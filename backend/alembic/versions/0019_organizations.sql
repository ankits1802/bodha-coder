CREATE FUNCTION bodha_organization_closure() RETURNS trigger
LANGUAGE plpgsql AS $body$
BEGIN
  IF bodha_maintenance(TG_RELID) THEN
    RETURN NEW;
  END IF;
  IF TG_OP = 'INSERT' THEN
    IF NEW.closed_at IS NOT NULL OR NEW.purged_at IS NOT NULL THEN
      RAISE EXCEPTION 'bodha: an organization is added open' USING ERRCODE = 'insufficient_privilege';
    END IF;
    RETURN NEW;
  END IF;
  IF OLD.closed_at IS NOT NULL AND NEW.closed_at IS DISTINCT FROM OLD.closed_at THEN
    RAISE EXCEPTION 'bodha: closing an organization is final' USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF NEW.purged_at IS DISTINCT FROM OLD.purged_at OR (NEW.status = 'purged' AND OLD.status <> 'purged') THEN
    RAISE EXCEPTION 'bodha: only the purge marks an organization purged' USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF OLD.closed_at IS NULL AND NEW.closed_at IS NOT NULL THEN
    NEW.closed_at := clock_timestamp();
  END IF;
  RETURN NEW;
END
$body$
;
CREATE FUNCTION bodha_purge_organization(organization text, wait_days integer) RETURNS integer
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
  SELECT closed_at INTO closed FROM organizations WHERE id = organization AND status = 'closed' FOR UPDATE;
  IF closed IS NULL THEN
    RAISE EXCEPTION 'bodha: organization % is not closed', organization
      USING ERRCODE = 'object_not_in_prerequisite_state';
  END IF;
  IF closed > clock_timestamp() - make_interval(days => floor_days) THEN
    RAISE EXCEPTION 'bodha: organization % closed less than % days ago', organization, floor_days
      USING ERRCODE = 'object_not_in_prerequisite_state';
  END IF;
  only_here := ARRAY(
    SELECT member.user_id FROM organization_memberships AS member
    WHERE member.organization_id = organization AND NOT EXISTS (
      SELECT 1 FROM organization_memberships AS other
      WHERE other.user_id = member.user_id AND other.organization_id <> organization
    ) AND NOT EXISTS (
      SELECT 1 FROM practice_memberships AS place WHERE place.user_id = member.user_id
    )
  );
  PERFORM set_config('bodha.maintenance', 'on', true);
  FOREACH step IN ARRAY ARRAY[
    'DELETE FROM domain_join_requests WHERE claim_id IN (SELECT id FROM domain_claims WHERE organization_id = $1)',
    'DELETE FROM domain_claims WHERE organization_id = $1',
    'DELETE FROM subscriptions WHERE organization_id = $1',
    'DELETE FROM organization_memberships WHERE organization_id = $1',
    'DELETE FROM signature_adoptions WHERE user_id = ANY($2)',
    'DELETE FROM signatures WHERE user_id = ANY($2)',
    'DELETE FROM sessions WHERE user_id = ANY($2)',
    'DELETE FROM auth_events WHERE user_id = ANY($2)',
    'DELETE FROM user_tokens WHERE user_id = ANY($2)',
    'DELETE FROM recovery_codes WHERE user_id = ANY($2)',
    'DELETE FROM user_identities WHERE user_id = ANY($2)',
    'DELETE FROM users WHERE id = ANY($2)'
  ]::text[] LOOP
    EXECUTE step USING organization, only_here;
    GET DIAGNOSTICS counted = ROW_COUNT;
    removed := removed + counted;
  END LOOP;
  UPDATE organizations SET status = 'purged', purged_at = clock_timestamp() WHERE id = organization;
  PERFORM set_config('bodha.maintenance', previous, true);
  RETURN removed;
END
$body$
;
