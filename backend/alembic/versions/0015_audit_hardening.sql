CREATE FUNCTION bodha_maintenance(rel oid) RETURNS boolean
LANGUAGE sql VOLATILE AS $body$
SELECT coalesce(current_setting('bodha.maintenance', true), '') = 'on'
   AND pg_has_role(current_user, (SELECT relowner FROM pg_class WHERE oid = rel), 'MEMBER')
$body$
;
CREATE FUNCTION bodha_reject_change() RETURNS trigger
LANGUAGE plpgsql AS $body$
BEGIN
  IF bodha_maintenance(TG_RELID) THEN
    IF TG_OP = 'DELETE' THEN
      RETURN OLD;
    END IF;
    RETURN NEW;
  END IF;
  RAISE EXCEPTION 'bodha: % refused on %; retained rows are never deleted and append-only rows never change', TG_OP, TG_TABLE_NAME
    USING ERRCODE = 'insufficient_privilege';
END
$body$
;
CREATE FUNCTION bodha_write_once() RETURNS trigger
LANGUAGE plpgsql AS $body$
DECLARE
  old_row jsonb := to_jsonb(OLD);
  new_row jsonb := to_jsonb(NEW);
  guarded text;
BEGIN
  IF bodha_maintenance(TG_RELID) THEN
    RETURN NEW;
  END IF;
  FOREACH guarded IN ARRAY TG_ARGV LOOP
    IF NOT old_row ? guarded THEN
      RAISE EXCEPTION 'bodha: % has no column %', TG_TABLE_NAME, guarded;
    END IF;
    IF old_row -> guarded <> 'null'::jsonb AND old_row -> guarded IS DISTINCT FROM new_row -> guarded THEN
      RAISE EXCEPTION 'bodha: %.% is written once', TG_TABLE_NAME, guarded USING ERRCODE = 'insufficient_privilege';
    END IF;
  END LOOP;
  RETURN NEW;
END
$body$
;
CREATE FUNCTION bodha_stamp() RETURNS trigger
LANGUAGE plpgsql AS $body$
BEGIN
  IF bodha_maintenance(TG_RELID) THEN
    RETURN NEW;
  END IF;
  RETURN jsonb_populate_record(NEW, jsonb_build_object(TG_ARGV[0], clock_timestamp()));
END
$body$
;
CREATE FUNCTION bodha_link_hash(prev text, content text) RETURNS text
LANGUAGE sql IMMUTABLE AS $body$
SELECT encode(sha256(convert_to(prev || content, 'UTF8')), 'hex')
$body$
;
CREATE FUNCTION bodha_utc_text(moment timestamptz) RETURNS text
LANGUAGE sql IMMUTABLE AS $body$
SELECT to_char(moment AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
$body$
;
CREATE FUNCTION bodha_access_log_content(entry access_log) RETURNS text
LANGUAGE sql STABLE AS $body$
SELECT jsonb_build_array(
  entry.id, entry.practice_id, entry.chain_seq, bodha_utc_text(entry.created_at), entry.actor_kind,
  entry.actor_id, entry.actor_name, entry.action, entry.note_id, entry.detail, entry.ip, entry.user_agent
)::text
$body$
;
CREATE FUNCTION bodha_activity_content(entry activity) RETURNS text
LANGUAGE sql STABLE AS $body$
SELECT jsonb_build_array(
  entry.id, entry.chain_seq, bodha_utc_text(entry.created_at), entry.actor_id, entry.actor_name,
  entry.action, entry.practice_id, entry.detail, entry.changes
)::text
$body$
;
CREATE FUNCTION bodha_chain_start(chain_name text, OUT seq bigint, OUT hash text)
LANGUAGE sql STABLE AS $body$
SELECT coalesce(max(through_seq), 0),
       coalesce((array_agg(through_hash ORDER BY through_seq DESC))[1], repeat('0', 64))
FROM audit_chain_anchors WHERE chain = chain_name
$body$
;
CREATE FUNCTION bodha_link_access_log() RETURNS trigger
LANGUAGE plpgsql AS $body$
DECLARE
  chain_name text := 'access_log:' || NEW.practice_id;
  tail_seq bigint;
  tail_hash text;
BEGIN
  PERFORM pg_advisory_xact_lock(hashtextextended(chain_name, 0));
  SELECT chain_seq, row_hash INTO tail_seq, tail_hash FROM access_log
  WHERE practice_id = NEW.practice_id ORDER BY chain_seq DESC LIMIT 1;
  IF tail_seq IS NULL THEN
    SELECT origin.seq, origin.hash INTO tail_seq, tail_hash FROM bodha_chain_start(chain_name) AS origin;
  END IF;
  IF NOT bodha_maintenance(TG_RELID) THEN
    NEW.created_at := clock_timestamp();
  END IF;
  NEW.chain_seq := tail_seq + 1;
  NEW.prev_hash := tail_hash;
  NEW.row_hash := bodha_link_hash(tail_hash, bodha_access_log_content(NEW));
  RETURN NEW;
END
$body$
;
CREATE FUNCTION bodha_link_activity() RETURNS trigger
LANGUAGE plpgsql AS $body$
DECLARE
  tail_seq bigint;
  tail_hash text;
BEGIN
  PERFORM pg_advisory_xact_lock(hashtextextended('activity', 0));
  SELECT chain_seq, row_hash INTO tail_seq, tail_hash FROM activity ORDER BY chain_seq DESC LIMIT 1;
  IF tail_seq IS NULL THEN
    SELECT origin.seq, origin.hash INTO tail_seq, tail_hash FROM bodha_chain_start('activity') AS origin;
  END IF;
  IF NOT bodha_maintenance(TG_RELID) THEN
    NEW.created_at := clock_timestamp();
  END IF;
  NEW.chain_seq := tail_seq + 1;
  NEW.prev_hash := tail_hash;
  NEW.row_hash := bodha_link_hash(tail_hash, bodha_activity_content(NEW));
  RETURN NEW;
END
$body$
;
CREATE FUNCTION bodha_link_problem(
  expected_seq bigint, expected_prev text, seq bigint, prev text, stored text, content text
) RETURNS text
LANGUAGE sql IMMUTABLE AS $body$
SELECT CASE
  WHEN seq <> expected_seq THEN 'missing rows'
  WHEN prev <> expected_prev THEN 'broken link'
  WHEN stored <> bodha_link_hash(prev, content) THEN 'changed row'
END
$body$
;
CREATE FUNCTION bodha_verify_chain(chain_name text)
RETURNS TABLE(checked bigint, head_seq bigint, head_hash text, broken_seq bigint, broken_id text, problem text)
LANGUAGE plpgsql STABLE AS $body$
DECLARE
  log_entry access_log;
  activity_entry activity;
BEGIN
  SELECT origin.seq, origin.hash INTO head_seq, head_hash FROM bodha_chain_start(chain_name) AS origin;
  checked := 0;
  IF chain_name = 'activity' THEN
    FOR activity_entry IN SELECT * FROM activity ORDER BY chain_seq LOOP
      problem := bodha_link_problem(
        head_seq + 1, head_hash, activity_entry.chain_seq, activity_entry.prev_hash, activity_entry.row_hash,
        bodha_activity_content(activity_entry)
      );
      IF problem IS NOT NULL THEN
        broken_seq := activity_entry.chain_seq;
        broken_id := activity_entry.id;
        RETURN NEXT;
        RETURN;
      END IF;
      checked := checked + 1;
      head_seq := activity_entry.chain_seq;
      head_hash := activity_entry.row_hash;
    END LOOP;
  ELSIF chain_name LIKE 'access_log:%' THEN
    FOR log_entry IN
      SELECT * FROM access_log WHERE practice_id = substr(chain_name, 12) ORDER BY chain_seq
    LOOP
      problem := bodha_link_problem(
        head_seq + 1, head_hash, log_entry.chain_seq, log_entry.prev_hash, log_entry.row_hash,
        bodha_access_log_content(log_entry)
      );
      IF problem IS NOT NULL THEN
        broken_seq := log_entry.chain_seq;
        broken_id := log_entry.id;
        RETURN NEXT;
        RETURN;
      END IF;
      checked := checked + 1;
      head_seq := log_entry.chain_seq;
      head_hash := log_entry.row_hash;
    END LOOP;
  ELSE
    RAISE EXCEPTION 'bodha: % is not an audit chain', chain_name;
  END IF;
  RETURN NEXT;
END
$body$
;
CREATE FUNCTION bodha_verify_audit_log()
RETURNS TABLE(chain_name text, checked bigint, head_seq bigint, head_hash text, broken_seq bigint, broken_id text,
              problem text)
LANGUAGE sql STABLE AS $body$
SELECT chains.label, result.*
FROM (
  SELECT 'activity' AS label
  UNION SELECT 'access_log:' || practice_id FROM access_log
  UNION SELECT chain FROM audit_chain_anchors
) AS chains
CROSS JOIN LATERAL bodha_verify_chain(chains.label) AS result
ORDER BY chains.label
$body$
;
CREATE FUNCTION bodha_purge_access_log(practice text, cutoff timestamptz) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $body$
DECLARE
  chain_name text := 'access_log:' || practice;
  previous text := coalesce(current_setting('bodha.maintenance', true), '');
  first_kept bigint;
  through bigint;
  through_hash text;
  removed integer;
BEGIN
  IF cutoff IS NULL OR cutoff > clock_timestamp() - make_interval(days => 2557) THEN
    RAISE EXCEPTION 'bodha: access log rows younger than 2557 days are kept' USING ERRCODE = 'insufficient_privilege';
  END IF;
  PERFORM pg_advisory_xact_lock(hashtextextended(chain_name, 0));
  SELECT min(chain_seq) INTO first_kept FROM access_log WHERE practice_id = practice AND created_at >= cutoff;
  SELECT chain_seq, row_hash INTO through, through_hash FROM access_log
  WHERE practice_id = practice AND (first_kept IS NULL OR chain_seq < first_kept)
  ORDER BY chain_seq DESC LIMIT 1;
  IF through IS NULL THEN
    RETURN 0;
  END IF;
  INSERT INTO audit_chain_anchors (id, chain, through_seq, through_hash, rows_removed)
  SELECT gen_random_uuid()::text, chain_name, through, through_hash, count(*)
  FROM access_log WHERE practice_id = practice AND chain_seq <= through;
  PERFORM set_config('bodha.maintenance', 'on', true);
  DELETE FROM access_log WHERE practice_id = practice AND chain_seq <= through;
  GET DIAGNOSTICS removed = ROW_COUNT;
  PERFORM set_config('bodha.maintenance', previous, true);
  RETURN removed;
END
$body$
;
CREATE FUNCTION bodha_purge_practice(practice text, wait_days integer) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $body$
DECLARE
  previous text := coalesce(current_setting('bodha.maintenance', true), '');
  floor_days integer := greatest(coalesce(wait_days, 2557), 2557);
  closed timestamptz;
  only_here text[];
  step text;
  counted integer;
  removed integer := 0;
BEGIN
  SELECT closed_at INTO closed FROM practices WHERE id = practice AND status = 'closed' FOR UPDATE;
  IF closed IS NULL THEN
    RAISE EXCEPTION 'bodha: practice % is not closed', practice USING ERRCODE = 'object_not_in_prerequisite_state';
  END IF;
  IF closed > clock_timestamp() - make_interval(days => floor_days) THEN
    RAISE EXCEPTION 'bodha: practice % closed less than % days ago', practice, floor_days
      USING ERRCODE = 'object_not_in_prerequisite_state';
  END IF;
  only_here := ARRAY(
    SELECT member.user_id FROM practice_memberships AS member
    WHERE member.practice_id = practice AND NOT EXISTS (
      SELECT 1 FROM practice_memberships AS other
      WHERE other.user_id = member.user_id AND other.practice_id <> practice
    )
  );
  PERFORM set_config('bodha.maintenance', 'on', true);
  FOREACH step IN ARRAY ARRAY[
    'DELETE FROM remittance_lines WHERE note_id IN (SELECT id FROM notes WHERE practice_id = $1)
       OR remittance_id IN (SELECT id FROM remittances WHERE practice_id = $1)',
    'DELETE FROM remittances WHERE practice_id = $1',
    'DELETE FROM audit_samples WHERE practice_id = $1',
    'DELETE FROM audit_runs WHERE practice_id = $1',
    'DELETE FROM eval_cases WHERE practice_id = $1',
    'DELETE FROM eval_runs WHERE practice_id = $1',
    'DELETE FROM review_comment_removals WHERE practice_id = $1',
    'DELETE FROM review_comments WHERE practice_id = $1',
    'DELETE FROM provider_attestations WHERE practice_id = $1',
    'DELETE FROM audit_packages WHERE practice_id = $1',
    'DELETE FROM claim_export_items WHERE practice_id = $1',
    'DELETE FROM claim_exports WHERE practice_id = $1',
    'DELETE FROM note_changes WHERE note_id IN (SELECT id FROM notes WHERE practice_id = $1)',
    'DELETE FROM decisions WHERE note_id IN (SELECT id FROM notes WHERE practice_id = $1)',
    'DELETE FROM suggestions WHERE note_id IN (SELECT id FROM notes WHERE practice_id = $1)',
    'DELETE FROM note_texts WHERE note_id IN (SELECT id FROM notes WHERE practice_id = $1)',
    'DELETE FROM addendum_requests WHERE practice_id = $1',
    'DELETE FROM approved_claims WHERE practice_id = $1',
    'DELETE FROM analysis_failures WHERE analysis_id IN
       (SELECT analyses.id FROM analyses JOIN notes ON notes.id = analyses.note_id WHERE notes.practice_id = $1)',
    'DELETE FROM analyses WHERE note_id IN (SELECT id FROM notes WHERE practice_id = $1)',
    'DELETE FROM code_sets WHERE note_id IN (SELECT id FROM notes WHERE practice_id = $1)',
    'DELETE FROM notes WHERE practice_id = $1',
    'DELETE FROM batches WHERE practice_id = $1',
    'DELETE FROM providers WHERE practice_id = $1',
    'DELETE FROM mips_lists WHERE practice_id = $1',
    'DELETE FROM access_log WHERE practice_id = $1',
    'DELETE FROM audit_chain_anchors WHERE chain = ''access_log:'' || $1',
    'DELETE FROM subscriptions WHERE practice_id = $1',
    'DELETE FROM sessions WHERE practice_id = $1 OR user_id = ANY($2)',
    'DELETE FROM auth_events WHERE practice_id = $1 OR user_id = ANY($2)',
    'DELETE FROM practice_memberships WHERE practice_id = $1',
    'DELETE FROM user_tokens WHERE user_id = ANY($2)',
    'DELETE FROM recovery_codes WHERE user_id = ANY($2)',
    'DELETE FROM user_identities WHERE user_id = ANY($2)',
    'UPDATE users SET last_practice_id = NULL WHERE last_practice_id = $1',
    'UPDATE users SET practice_id = NULL WHERE practice_id = $1 AND NOT id = ANY($2)',
    'DELETE FROM users WHERE id = ANY($2)'
  ]::text[] LOOP
    EXECUTE step USING practice, only_here;
    GET DIAGNOSTICS counted = ROW_COUNT;
    removed := removed + counted;
  END LOOP;
  UPDATE practices SET status = 'purged', purged_at = clock_timestamp() WHERE id = practice;
  PERFORM set_config('bodha.maintenance', previous, true);
  RETURN removed;
END
$body$
;
CREATE FUNCTION bodha_purge_auth_events(practice text, cutoff timestamptz) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $body$
DECLARE
  previous text := coalesce(current_setting('bodha.maintenance', true), '');
  removed integer;
BEGIN
  IF cutoff IS NULL OR cutoff > clock_timestamp() - make_interval(days => 2557) THEN
    RAISE EXCEPTION 'bodha: sign-in events younger than 2557 days are kept' USING ERRCODE = 'insufficient_privilege';
  END IF;
  PERFORM set_config('bodha.maintenance', 'on', true);
  DELETE FROM auth_events
  WHERE created_at < cutoff AND (practice_id = practice OR (practice IS NULL AND practice_id IS NULL));
  GET DIAGNOSTICS removed = ROW_COUNT;
  PERFORM set_config('bodha.maintenance', previous, true);
  RETURN removed;
END
$body$
;
CREATE FUNCTION bodha_practice_closure() RETURNS trigger
LANGUAGE plpgsql AS $body$
BEGIN
  IF bodha_maintenance(TG_RELID) THEN
    RETURN NEW;
  END IF;
  IF TG_OP = 'INSERT' THEN
    IF NEW.closed_at IS NOT NULL OR NEW.purged_at IS NOT NULL THEN
      RAISE EXCEPTION 'bodha: a practice is added open' USING ERRCODE = 'insufficient_privilege';
    END IF;
    RETURN NEW;
  END IF;
  IF OLD.closed_at IS NOT NULL AND NEW.closed_at IS DISTINCT FROM OLD.closed_at THEN
    RAISE EXCEPTION 'bodha: closing a practice is final' USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF NEW.purged_at IS DISTINCT FROM OLD.purged_at OR (NEW.status = 'purged' AND OLD.status <> 'purged') THEN
    RAISE EXCEPTION 'bodha: only the purge marks a practice purged' USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF OLD.closed_at IS NULL AND NEW.closed_at IS NOT NULL THEN
    NEW.closed_at := clock_timestamp();
  END IF;
  RETURN NEW;
END
$body$
;
CREATE FUNCTION bodha_backfill_chains() RETURNS void
LANGUAGE plpgsql AS $body$
DECLARE
  practice text;
  log_entry access_log;
  activity_entry activity;
  seq bigint;
  prev text;
BEGIN
  FOR practice IN SELECT DISTINCT practice_id FROM access_log LOOP
    seq := 1;
    prev := repeat('0', 64);
    FOR log_entry IN SELECT * FROM access_log WHERE practice_id = practice ORDER BY created_at, id LOOP
      log_entry.chain_seq := seq;
      log_entry.prev_hash := prev;
      log_entry.row_hash := bodha_link_hash(prev, bodha_access_log_content(log_entry));
      UPDATE access_log SET chain_seq = seq, prev_hash = prev, row_hash = log_entry.row_hash WHERE id = log_entry.id;
      prev := log_entry.row_hash;
      seq := seq + 1;
    END LOOP;
  END LOOP;
  seq := 1;
  prev := repeat('0', 64);
  FOR activity_entry IN SELECT * FROM activity ORDER BY created_at, id LOOP
    activity_entry.chain_seq := seq;
    activity_entry.prev_hash := prev;
    activity_entry.row_hash := bodha_link_hash(prev, bodha_activity_content(activity_entry));
    UPDATE activity SET chain_seq = seq, prev_hash = prev, row_hash = activity_entry.row_hash
    WHERE id = activity_entry.id;
    prev := activity_entry.row_hash;
    seq := seq + 1;
  END LOOP;
END
$body$
;
CREATE TRIGGER bodha_write_once BEFORE UPDATE ON analyses FOR EACH ROW EXECUTE FUNCTION bodha_write_once(
  'id', 'note_id', 'revision', 'reason', 'created_at', 'report', 'response_key', 'prompt_key',
  'prompt_sha256', 'document_key', 'app_version', 'generation', 'model', 'prompt_version', 'input_tokens',
  'output_tokens', 'finished_at', 'cost_microusd', 'price_snapshot'
)
;
CREATE TRIGGER bodha_write_once BEFORE UPDATE ON remittances FOR EACH ROW EXECUTE FUNCTION bodha_write_once(
  'id', 'created_at', 'practice_id', 'file_key', 'file_name', 'payer', 'paid_on', 'uploaded_by',
  'file_sha256'
)
;
CREATE TRIGGER bodha_write_once BEFORE UPDATE ON addendum_requests FOR EACH ROW EXECUTE FUNCTION bodha_write_once(
  'id', 'created_at', 'practice_id', 'note_id', 'analysis_id', 'provider_id', 'questions', 'sent_by',
  'answers', 'addendum_text', 'answered_at', 'purpose', 'approved_claim_id'
)
;
