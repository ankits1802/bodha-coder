CREATE TABLE activity (
	actor_id VARCHAR(36), 
	actor_name VARCHAR(120) NOT NULL, 
	action VARCHAR(40) NOT NULL, 
	practice_id VARCHAR(36), 
	detail VARCHAR(300), 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_activity PRIMARY KEY (id)
);

CREATE INDEX ix_activity_practice_id ON activity (practice_id);

CREATE TABLE demo_requests (
	name VARCHAR(120) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	organization VARCHAR(200) NOT NULL, 
	message TEXT, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_demo_requests PRIMARY KEY (id)
);

CREATE TABLE places_of_service (
	code VARCHAR(2) NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	active BOOLEAN NOT NULL, 
	CONSTRAINT pk_places_of_service PRIMARY KEY (code)
);

CREATE TABLE practices (
	name VARCHAR(200) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	plan VARCHAR(16) NOT NULL, 
	seats INTEGER NOT NULL, 
	renews_on DATE, 
	setup JSONB NOT NULL, 
	checks JSONB NOT NULL, 
	mfa_roles JSONB NOT NULL, 
	idle_minutes INTEGER NOT NULL, 
	private_messages BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_practices PRIMARY KEY (id), 
	CONSTRAINT ck_practices_status_allowed CHECK (status IN ('trial', 'active', 'ended', 'blocked'))
);

CREATE TABLE access_log (
	practice_id VARCHAR(36) NOT NULL, 
	actor_kind VARCHAR(8) NOT NULL, 
	actor_id VARCHAR(36) NOT NULL, 
	actor_name VARCHAR(120) NOT NULL, 
	action VARCHAR(40) NOT NULL, 
	note_id VARCHAR(36), 
	detail VARCHAR(300), 
	ip VARCHAR(64), 
	user_agent VARCHAR(300), 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_access_log PRIMARY KEY (id), 
	CONSTRAINT ck_access_log_actor_kind_allowed CHECK (actor_kind IN ('user', 'provider')), 
	CONSTRAINT fk_access_log_practice_id_practices FOREIGN KEY(practice_id) REFERENCES practices (id)
);

CREATE INDEX ix_access_log_practice_time ON access_log (practice_id, created_at);

CREATE TABLE providers (
	practice_id VARCHAR(36) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	credential VARCHAR(16) NOT NULL, 
	specialty VARCHAR(80), 
	npi VARCHAR(10), 
	place_code VARCHAR(2), 
	email VARCHAR(254), 
	phone VARCHAR(32), 
	channel VARCHAR(8) NOT NULL, 
	active BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_providers PRIMARY KEY (id), 
	CONSTRAINT ck_providers_channel_allowed CHECK (channel IN ('email', 'sms')), 
	CONSTRAINT fk_providers_practice_id_practices FOREIGN KEY(practice_id) REFERENCES practices (id), 
	CONSTRAINT fk_providers_place_code_places_of_service FOREIGN KEY(place_code) REFERENCES places_of_service (code)
);

CREATE INDEX ix_providers_practice_id ON providers (practice_id);

CREATE TABLE users (
	practice_id VARCHAR(36), 
	email VARCHAR(254) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	role VARCHAR(16) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	password_hash VARCHAR(100), 
	mfa_secret VARCHAR(64), 
	mfa_enabled BOOLEAN NOT NULL, 
	token_version INTEGER NOT NULL, 
	last_active_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_users PRIMARY KEY (id), 
	CONSTRAINT ck_users_role_allowed CHECK (role IN ('hq', 'admin', 'coder', 'cdi', 'compliance', 'biller', 'viewer')), 
	CONSTRAINT ck_users_status_allowed CHECK (status IN ('invited', 'active', 'blocked')), 
	CONSTRAINT fk_users_practice_id_practices FOREIGN KEY(practice_id) REFERENCES practices (id), 
	CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE INDEX ix_users_practice_id ON users (practice_id);

CREATE TABLE batches (
	practice_id VARCHAR(36) NOT NULL, 
	provider_id VARCHAR(36) NOT NULL, 
	service_date DATE NOT NULL, 
	place_code VARCHAR(2) NOT NULL, 
	visit_type VARCHAR(40) NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_batches PRIMARY KEY (id), 
	CONSTRAINT fk_batches_practice_id_practices FOREIGN KEY(practice_id) REFERENCES practices (id), 
	CONSTRAINT fk_batches_provider_id_providers FOREIGN KEY(provider_id) REFERENCES providers (id), 
	CONSTRAINT fk_batches_place_code_places_of_service FOREIGN KEY(place_code) REFERENCES places_of_service (code), 
	CONSTRAINT fk_batches_created_by_users FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE INDEX ix_batches_practice_id ON batches (practice_id);

CREATE TABLE mips_lists (
	practice_id VARCHAR(36) NOT NULL, 
	measure_ids JSONB NOT NULL, 
	updated_by VARCHAR(36) NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_mips_lists PRIMARY KEY (id), 
	CONSTRAINT uq_mips_lists_practice_id UNIQUE (practice_id), 
	CONSTRAINT fk_mips_lists_practice_id_practices FOREIGN KEY(practice_id) REFERENCES practices (id), 
	CONSTRAINT fk_mips_lists_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id)
);

CREATE TABLE sessions (
	user_id VARCHAR(36) NOT NULL, 
	refresh_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_used_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	user_agent VARCHAR(300), 
	ip VARCHAR(64), 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_sessions PRIMARY KEY (id), 
	CONSTRAINT fk_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), 
	CONSTRAINT uq_sessions_refresh_hash UNIQUE (refresh_hash)
);

CREATE INDEX ix_sessions_user_id ON sessions (user_id);

CREATE TABLE user_tokens (
	user_id VARCHAR(36) NOT NULL, 
	purpose VARCHAR(16) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	used_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_user_tokens PRIMARY KEY (id), 
	CONSTRAINT ck_user_tokens_purpose_allowed CHECK (purpose IN ('invite', 'reset')), 
	CONSTRAINT fk_user_tokens_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), 
	CONSTRAINT uq_user_tokens_token_hash UNIQUE (token_hash)
);

CREATE INDEX ix_user_tokens_user_id ON user_tokens (user_id);

CREATE TABLE notes (
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	practice_id VARCHAR(36) NOT NULL, 
	batch_id VARCHAR(36) NOT NULL, 
	provider_id VARCHAR(36) NOT NULL, 
	file_key VARCHAR(300) NOT NULL, 
	file_name VARCHAR(255) NOT NULL, 
	file_sha256 VARCHAR(64) NOT NULL, 
	file_bytes INTEGER NOT NULL, 
	patient_name VARCHAR(200), 
	patient_age INTEGER, 
	patient_sex VARCHAR(16), 
	service_date DATE NOT NULL, 
	visit_type VARCHAR(40) NOT NULL, 
	place_code VARCHAR(2) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	lane VARCHAR(16), 
	headline VARCHAR(120), 
	flag_reason TEXT, 
	flagged_by VARCHAR(36), 
	compliance_cleared_by VARCHAR(36), 
	current_analysis_id VARCHAR(36), 
	approved_by VARCHAR(36), 
	approved_at TIMESTAMP WITH TIME ZONE, 
	exported_at TIMESTAMP WITH TIME ZONE, 
	due_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_notes PRIMARY KEY (id), 
	CONSTRAINT uq_notes_practice_id UNIQUE (practice_id, file_sha256), 
	CONSTRAINT ck_notes_status_allowed CHECK (status IN ('queued', 'reading', 'ready', 'failed', 'approved', 'exported')), 
	CONSTRAINT ck_notes_lane_allowed CHECK (lane IS NULL OR lane IN ('approve', 'coder', 'provider', 'compliance')), 
	CONSTRAINT fk_notes_practice_id_practices FOREIGN KEY(practice_id) REFERENCES practices (id), 
	CONSTRAINT fk_notes_batch_id_batches FOREIGN KEY(batch_id) REFERENCES batches (id), 
	CONSTRAINT fk_notes_provider_id_providers FOREIGN KEY(provider_id) REFERENCES providers (id), 
	CONSTRAINT fk_notes_flagged_by_users FOREIGN KEY(flagged_by) REFERENCES users (id), 
	CONSTRAINT fk_notes_compliance_cleared_by_users FOREIGN KEY(compliance_cleared_by) REFERENCES users (id), 
	CONSTRAINT fk_notes_approved_by_users FOREIGN KEY(approved_by) REFERENCES users (id)
);

CREATE INDEX ix_notes_batch_id ON notes (batch_id);

CREATE INDEX ix_notes_provider_id ON notes (provider_id);

CREATE INDEX ix_notes_work ON notes (practice_id, status, lane, due_at);

CREATE TABLE analyses (
	note_id VARCHAR(36) NOT NULL, 
	revision INTEGER NOT NULL, 
	reason VARCHAR(24) NOT NULL, 
	status VARCHAR(12) NOT NULL, 
	text_revision INTEGER, 
	context JSONB NOT NULL, 
	model VARCHAR(60), 
	prompt_version VARCHAR(20), 
	attempts INTEGER NOT NULL, 
	requested_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	input_tokens INTEGER, 
	output_tokens INTEGER, 
	response_key VARCHAR(300), 
	report JSONB, 
	error VARCHAR(300), 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_analyses PRIMARY KEY (id), 
	CONSTRAINT uq_analyses_note_id UNIQUE (note_id, revision), 
	CONSTRAINT ck_analyses_status_allowed CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'superseded')), 
	CONSTRAINT fk_analyses_note_id_notes FOREIGN KEY(note_id) REFERENCES notes (id)
);

CREATE INDEX ix_analyses_queue ON analyses (status, requested_at);

CREATE TABLE code_sets (
	note_id VARCHAR(36) NOT NULL, 
	kind VARCHAR(8) NOT NULL, 
	revision INTEGER NOT NULL, 
	codes JSONB NOT NULL, 
	reason VARCHAR(40) NOT NULL, 
	actor_id VARCHAR(36), 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_code_sets PRIMARY KEY (id), 
	CONSTRAINT uq_code_sets_note_id UNIQUE (note_id, kind, revision), 
	CONSTRAINT ck_code_sets_kind_allowed CHECK (kind IN ('billed', 'final')), 
	CONSTRAINT fk_code_sets_note_id_notes FOREIGN KEY(note_id) REFERENCES notes (id), 
	CONSTRAINT fk_code_sets_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)
);

CREATE TABLE addendum_requests (
	practice_id VARCHAR(36) NOT NULL, 
	note_id VARCHAR(36) NOT NULL, 
	analysis_id VARCHAR(36) NOT NULL, 
	provider_id VARCHAR(36) NOT NULL, 
	questions JSONB NOT NULL, 
	answers JSONB, 
	addendum_text TEXT, 
	channel VARCHAR(8) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	code_hash VARCHAR(64), 
	code_expires_at TIMESTAMP WITH TIME ZONE, 
	code_attempts INTEGER NOT NULL, 
	hold_claim BOOLEAN NOT NULL, 
	remind_at TIMESTAMP WITH TIME ZONE, 
	status VARCHAR(12) NOT NULL, 
	sent_by VARCHAR(36) NOT NULL, 
	answered_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_addendum_requests PRIMARY KEY (id), 
	CONSTRAINT ck_addendum_requests_status_allowed CHECK (status IN ('sent', 'answered', 'expired', 'cancelled')), 
	CONSTRAINT ck_addendum_requests_channel_allowed CHECK (channel IN ('email', 'sms')), 
	CONSTRAINT fk_addendum_requests_practice_id_practices FOREIGN KEY(practice_id) REFERENCES practices (id), 
	CONSTRAINT fk_addendum_requests_note_id_notes FOREIGN KEY(note_id) REFERENCES notes (id), 
	CONSTRAINT fk_addendum_requests_analysis_id_analyses FOREIGN KEY(analysis_id) REFERENCES analyses (id), 
	CONSTRAINT fk_addendum_requests_provider_id_providers FOREIGN KEY(provider_id) REFERENCES providers (id), 
	CONSTRAINT uq_addendum_requests_token_hash UNIQUE (token_hash), 
	CONSTRAINT fk_addendum_requests_sent_by_users FOREIGN KEY(sent_by) REFERENCES users (id)
);

CREATE INDEX ix_addendum_requests_note_id ON addendum_requests (note_id);

CREATE INDEX ix_addendum_requests_practice_id ON addendum_requests (practice_id);

CREATE INDEX ix_addendum_requests_provider_id ON addendum_requests (provider_id);

CREATE TABLE decisions (
	note_id VARCHAR(36) NOT NULL, 
	analysis_id VARCHAR(36) NOT NULL, 
	suggestion_key VARCHAR(80) NOT NULL, 
	choice VARCHAR(8) NOT NULL, 
	actor_id VARCHAR(36) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_decisions PRIMARY KEY (id), 
	CONSTRAINT ck_decisions_choice_allowed CHECK (choice IN ('accept', 'keep', 'ask', 'add', 'skip')), 
	CONSTRAINT fk_decisions_note_id_notes FOREIGN KEY(note_id) REFERENCES notes (id), 
	CONSTRAINT fk_decisions_analysis_id_analyses FOREIGN KEY(analysis_id) REFERENCES analyses (id), 
	CONSTRAINT fk_decisions_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)
);

CREATE INDEX ix_decisions_note_key ON decisions (note_id, suggestion_key, created_at);

CREATE TABLE suggestions (
	analysis_id VARCHAR(36) NOT NULL, 
	note_id VARCHAR(36) NOT NULL, 
	kind VARCHAR(16) NOT NULL, 
	key VARCHAR(80) NOT NULL, 
	code_before VARCHAR(12), 
	code_after VARCHAR(12), 
	action VARCHAR(20) NOT NULL, 
	title VARCHAR(300) NOT NULL, 
	reasoning TEXT NOT NULL, 
	evidence JSONB NOT NULL, 
	severity VARCHAR(12), 
	detail JSONB NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_suggestions PRIMARY KEY (id), 
	CONSTRAINT uq_suggestions_analysis_id UNIQUE (analysis_id, key), 
	CONSTRAINT ck_suggestions_kind_allowed CHECK (kind IN ('em', 'diagnosis', 'modifier', 'code_review', 'cdi_gap', 'cdi_query', 'audit_risk', 'audit_finding', 'mips')), 
	CONSTRAINT fk_suggestions_analysis_id_analyses FOREIGN KEY(analysis_id) REFERENCES analyses (id), 
	CONSTRAINT fk_suggestions_note_id_notes FOREIGN KEY(note_id) REFERENCES notes (id)
);

CREATE INDEX ix_suggestions_note_id ON suggestions (note_id);

CREATE TABLE note_texts (
	note_id VARCHAR(36) NOT NULL, 
	revision INTEGER NOT NULL, 
	source VARCHAR(12) NOT NULL, 
	text TEXT NOT NULL, 
	addendum_request_id VARCHAR(36), 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_note_texts PRIMARY KEY (id), 
	CONSTRAINT uq_note_texts_note_id UNIQUE (note_id, revision), 
	CONSTRAINT ck_note_texts_source_allowed CHECK (source IN ('document', 'addendum')), 
	CONSTRAINT fk_note_texts_note_id_notes FOREIGN KEY(note_id) REFERENCES notes (id), 
	CONSTRAINT fk_note_texts_addendum_request_id_addendum_requests FOREIGN KEY(addendum_request_id) REFERENCES addendum_requests (id)
);
