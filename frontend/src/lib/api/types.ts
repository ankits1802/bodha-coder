export type PracticeRole = "admin" | "coder" | "cdi" | "compliance" | "biller" | "viewer";
export type Role = "hq" | PracticeRole;

export type CheckKey = "em" | "icd" | "cdi" | "audit" | "mips" | "hcc";
export type Checks = Record<Exclude<CheckKey, "hcc">, boolean> & Partial<Record<"hcc", boolean>>;

export interface PracticeSummary {
  id: string;
  name: string;
  checks: Checks;
  idle_minutes: number;
  time_zone: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  practice: PracticeSummary | null;
}

export interface SignedIn {
  access_token: string;
  user: User;
}

export type MfaStep = "setup" | "verify";

export interface MfaChallenge {
  mfa: MfaStep;
  mfa_token: string;
}

export type LoginResult = SignedIn | MfaChallenge;

export interface MfaEnrolment {
  secret: string;
  uri: string;
  qr_image: string;
}

export interface MfaVerified extends SignedIn {
  recovery_codes?: string[];
}

export interface SignInProviders {
  google: boolean;
}

export interface SignedInDevice {
  id: string;
  created_at: string;
  last_used_at: string;
  ip: string | null;
  user_agent: string | null;
  current: boolean;
}

export interface RecoveryCodeStatus {
  enabled: boolean;
  remaining: number;
}

export interface RecoveryCodes {
  codes: string[];
}

export interface Preferences {
  notify_digest: boolean;
}

export type Lane = "approve" | "coder" | "provider" | "compliance";
export type NoteStatus = "queued" | "reading" | "ready" | "failed" | "approved" | "exported";
export type LaneReason =
  | "flagged"
  | "levels_too_high"
  | "audit_risk"
  | "waiting_on_provider"
  | "code_changes"
  | "questions"
  | "matches";

export interface LaneCount {
  total: number;
  due_soon: number;
}

export type LaneCounts = Record<Lane, LaneCount>;

export type EmAction = "keep" | "lower" | "raise" | "replace" | "add" | "not_applicable";

export interface NoteSummary {
  id: string;
  patient_name: string | null;
  provider_name: string;
  service_date: string;
  status: NoteStatus;
  lane: Lane | null;
  lane_reason: LaneReason | null;
  headline: string | null;
  place_code: string;
  visit_type: string;
  flag_reason: string | null;
  flagged_by: string | null;
  due_at: string;
  file_name: string;
  assigned_to: string | null;
}

export interface QueueRow extends NoteSummary {
  assignee_name: string | null;
  billed: string[];
  suggested: string[];
  em_action: EmAction | null;
}

export interface BatchProgress {
  id: string;
  provider_name: string;
  service_date: string;
  place_code: string;
  counts: Partial<Record<NoteStatus, number>>;
}

export interface TodaySummary {
  waiting: number;
  due_soon: number;
  lanes: LaneCounts;
  next_up: QueueRow[];
  batches: BatchProgress[];
}

export interface QueuePage {
  items: QueueRow[];
  lanes: LaneCounts;
  total: number;
  all_total: number;
  failed: number;
  page_size: number;
}

export interface QueueQuery {
  lane?: Lane;
  search?: string;
  provider_id?: string;
  batch_id?: string;
  assigned?: string;
  offset?: number;
}

export interface SearchResults {
  items: NoteSummary[];
  limit: number;
}

export interface CompliancePattern {
  provider_name: string;
  count: number;
}

export interface ComplianceRow extends QueueRow {
  flagged_by_name: string | null;
}

export interface ComplianceList {
  items: ComplianceRow[];
  patterns: CompliancePattern[];
}

export type Channel = "email" | "sms";

export interface ProviderRef {
  id: string;
  name: string;
  credential: string;
  specialty: string | null;
  channel: Channel;
}

export interface NoteHeader extends NoteSummary {
  assignee_name: string | null;
  payer: string | null;
  patient_age: number | null;
  patient_sex: string | null;
  provider: ProviderRef;
}

export type TextSource = "document" | "addendum";

export interface NoteText {
  revision: number;
  source: TextSource;
  text: string;
  created_at: string;
}

export type AnalysisStatus = "queued" | "running" | "succeeded" | "failed" | "superseded";

export interface RequiredElement {
  element: string;
  present: boolean;
  location: string | null;
  deficiency: string | null;
}

export interface CodingComplianceCheck {
  check: string;
  status: "Pass" | "Fail" | "Warning";
  finding: string;
}

export interface CmsCdiCompliance {
  standard: string;
  compliant: boolean;
  note: string;
}

export interface CodeLinkingOpportunity {
  diagnosis: string;
  relatedFindings: string;
  suggestion: string;
}

export interface AnalysisView {
  id: string;
  revision: number;
  status: AnalysisStatus;
  model: string | null;
  prompt_version: string | null;
  finished_at: string | null;
  failed_sections: string[];
  cdi: {
    overallCDIScore: number | null;
    summaryGuidance: string | null;
    codeLinkingOpportunities: CodeLinkingOpportunity[] | null;
  };
  audit: {
    overallComplianceScore: number | null;
    auditSummary: string | null;
    requiredElements: RequiredElement[] | null;
    codingCompliance: CodingComplianceCheck[] | null;
    cmsCDICompliance: CmsCdiCompliance[] | null;
  };
  mips_scope: unknown;
}

export type FindingKind =
  | "em"
  | "diagnosis"
  | "modifier"
  | "code_review"
  | "cdi_gap"
  | "cdi_query"
  | "audit_risk"
  | "audit_finding"
  | "mips";

export type FindingAction =
  | "keep"
  | "lower"
  | "raise"
  | "replace"
  | "add"
  | "remove"
  | "review"
  | "ask"
  | "info"
  | "not_applicable";

export type Choice = "accept" | "keep" | "ask" | "add" | "skip";

export interface Finding {
  kind: FindingKind;
  key: string;
  action: FindingAction;
  title: string;
  reasoning: string;
  code_before: string | null;
  code_after: string | null;
  evidence: string[];
  severity: string | null;
  detail: Record<string, unknown>;
  default_choice: Choice;
  choice: Choice;
  allowed: Choice[];
}

export type MdmLevel = "Straightforward" | "Low" | "Moderate" | "High";

export interface MdmElement {
  level: MdmLevel;
  reason: string;
}

export interface MdmElements {
  problems: MdmElement;
  data: MdmElement;
  risk: MdmElement;
}

export type CodeType = "CPT" | "ICD-10";

export interface CodeJson {
  code: string;
  type: CodeType;
  modifiers: string[];
  units?: number;
}

export interface AnalysisRevision {
  revision: number;
  reason: string;
  status: AnalysisStatus;
  model: string | null;
  finished_at: string | null;
  error: string | null;
}

export interface CodeSetRevision {
  kind: "billed" | "final";
  revision: number;
  codes: CodeJson[];
  reason: string;
  by: string | null;
  at: string;
}

export interface PointerChoice {
  code: string;
  diagnoses: string[];
}

export interface DecisionRecord {
  key: string;
  choice: Choice;
  by: string | null;
  at: string;
  pointers: PointerChoice | null;
}

export interface NoteHistory {
  analyses: AnalysisRevision[];
  code_sets: CodeSetRevision[];
  decisions: DecisionRecord[];
}

export interface AddendumQuestion {
  key: string;
  text: string;
  context: string[];
  options: string[];
}

export interface AddendumAnswer {
  key: string;
  choice: string;
  comment: string | null;
}

export type RequestStatus = "sent" | "answered" | "expired" | "cancelled";

export interface AddendumRequestView {
  id: string;
  status: RequestStatus;
  channel: Channel;
  questions: AddendumQuestion[];
  answers: AddendumAnswer[] | null;
  addendum_text: string | null;
  hold_claim: boolean;
  sent_at: string;
  answered_at: string | null;
}

export interface NoteDetail {
  note: NoteHeader;
  texts: NoteText[];
  failure: string | null;
  analysis: AnalysisView | null;
  findings: Finding[];
  claim: string[];
  estimate: ClaimEstimates | null;
  history: NoteHistory;
  requests: AddendumRequestView[];
}

export type RateSetting = "facility" | "non_facility";

export interface EstimateLine {
  code: string;
  amount: number | null;
}

export interface ClaimEstimate {
  total: number;
  lines: EstimateLine[];
  unpriced: string[];
}

export interface ClaimEstimates {
  release: string;
  setting: RateSetting;
  billed: ClaimEstimate;
  claim: ClaimEstimate;
  difference: number;
}

export interface PointerLine {
  code: string;
  label: string;
  pointers: string[];
  stored: boolean;
}

export interface ClaimDiagnosis {
  code: string;
  letter: string | null;
}

export interface ClaimPointers {
  diagnoses: ClaimDiagnosis[];
  lines: PointerLine[];
}

export type ComplianceDecision = "confirm" | "return" | "keep";

export interface QuestionEdit {
  key: string;
  text: string;
}

export interface AskBody {
  questions: QuestionEdit[];
  channel: Channel;
  hold: boolean;
}

export interface FilePreview {
  file_name: string;
  service_date: string | null;
  patient_name: string | null;
  cpt: string | null;
}

export interface FileDetail {
  billed: string | null;
  visit_type: string | null;
}

export interface UploadPlan {
  provider_id: string;
  service_date: string;
  place_code: string;
  visit_type: string;
}

export interface UploadResult {
  batch_id: string;
  accepted: string[];
  duplicates: string[];
}

export interface Page<T> {
  items: T[];
  total: number;
  offset: number;
  page_size: number;
}

export interface UploadedBatch {
  id: string;
  provider_name: string;
  service_date: string;
  place_code: string;
  visit_type: string;
  uploaded_by: string;
  created_at: string;
  counts: Partial<Record<NoteStatus, number>>;
}

export type BillsUnder = "individual" | "group";

export interface ProviderDetails {
  taxonomy_code: string | null;
  license_number: string | null;
  license_state: string | null;
  dea_number: string | null;
  bills_under: BillsUnder | null;
  group_npi: string | null;
  supervising_physician: string | null;
  signature_on_file: boolean;
}

export interface Provider {
  id: string;
  name: string;
  credential: string;
  specialty: string | null;
  npi: string | null;
  place_code: string | null;
  email: string | null;
  phone: string | null;
  channel: Channel;
  active: boolean;
  details: ProviderDetails;
}

export interface ProviderInput {
  name: string;
  credential: string;
  specialty: string | null;
  npi: string | null;
  place_code: string | null;
  email: string | null;
  phone: string | null;
  channel: Channel | null;
  active: boolean;
  details: ProviderDetails;
}

export interface Place {
  code: string;
  name: string;
}

export type BillingShow = "ready" | "exported" | "all";

export interface BillingRow {
  id: string;
  patient_name: string | null;
  service_date: string;
  provider_name: string;
  npi: string | null;
  place_code: string;
  codes: string[];
  changed: number;
  estimate: number | null;
  approved_by: string;
  approved_at: string | null;
  exported_at: string | null;
  cpt: string[];
  icd10: string[];
}

export interface BillingSummary {
  ready: number;
  exported_today: number;
  held_for_provider: number;
}

export interface BillingList extends Page<BillingRow> {
  summary: BillingSummary;
  limit: number;
}

export type InsightDays = 7 | 14 | 30 | 90;

export interface Outcomes {
  matched: number;
  billed_too_low: number;
  billed_too_high: number;
  diagnosis_changes: number;
}

export interface Insights {
  days: InsightDays;
  per_day: { date: string; notes: number }[];
  approved: number;
  approved_on_time: number;
  outcomes: Outcomes;
  providers: { provider_name: string; notes: number; matched: number }[];
  estimates: InsightEstimates;
  people: PersonProductivity[];
}

export interface InsightEstimates {
  notes: number;
  difference: number;
  providers: { provider_name: string; notes: number; difference: number }[];
}

export interface PersonProductivity {
  id: string;
  name: string;
  approved: number;
  median_minutes: number | null;
  changed: number;
}

export type SetupSectionKey =
  | "practice_details"
  | "payers"
  | "payments"
  | "coding_rules"
  | "charge_capture"
  | "documentation_rules"
  | "compliance"
  | "reports"
  | "contacts"
  | "patient_registration"
  | "software";

export interface SetupSection {
  fields: string[];
  values: Record<string, string>;
  complete: boolean;
}

export type IdleMinutes = 5 | 10 | 15 | 30;

export type AccessLogYears = 6 | 7 | 8 | 9 | 10;

export interface SecuritySettings {
  mfa_roles: PracticeRole[];
  idle_minutes: IdleMinutes;
  access_log_years: AccessLogYears;
}

export type PlanType = "commercial" | "medicare" | "medicare_advantage" | "medicaid" | "other";

export interface PayerInput {
  name: string;
  payer_id: string | null;
  plan_type: PlanType;
  active: boolean;
}

export interface Payer extends PayerInput {
  id: string;
}

export interface PracticeSetup {
  sections: Record<SetupSectionKey | "providers", SetupSection>;
  complete: number;
  total: number;
  checks: Checks;
  missing_npi: number;
  payers: Payer[];
  security: SecuritySettings | null;
}

export interface MipsMeasure {
  id: string;
  title: string;
}

export interface MipsOverview {
  standard: MipsMeasure[];
  addable: MipsMeasure[];
  measure_ids: string[];
  uses_standard: boolean;
}

export interface AccessLogEntry {
  at: string;
  actor: string;
  actor_kind: "user" | "provider" | "system";
  action: string;
  note_id: string | null;
  detail: string | null;
  ip: string | null;
  user_agent: string | null;
}

export type MemberStatus = "invited" | "active" | "blocked";

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: Role;
  status: MemberStatus;
  mfa_enabled: boolean;
  last_active_at: string | null;
}

export interface TeamList {
  seats: number;
  members: TeamMember[];
}

export interface InviteBody {
  name: string;
  email: string;
  role: PracticeRole;
}

export interface MemberUpdate {
  role?: PracticeRole;
  blocked?: boolean;
}

export interface ProviderRequest {
  practice_name: string;
  provider_name: string;
  status: RequestStatus;
  patient: { name: string | null; age: number | null; sex: string | null };
  service_date: string;
  visit_type: string;
  place_code: string;
  place_name: string | null;
  requested_by: string | null;
  requested_at: string;
  answered_at: string | null;
  expires_at: string;
  questions: AddendumQuestion[];
  texts: { revision: number; source: TextSource; text: string }[];
  addendum_text: string | null;
}

export interface RespondResult {
  status: RequestStatus;
  addendum_text: string;
}

export interface OtherRequest {
  id: string;
  patient_name: string | null;
  service_date: string;
  sent_at: string;
  questions: number;
}

export interface HqOverview {
  practices: number;
  people: number;
  read_last_24h: number;
  tokens_last_24h: number;
  failed_last_24h: number;
  waiting: number;
  running: number;
}

export type PracticeStatus = "trial" | "active" | "ended" | "blocked";
export type Plan = "trial" | "basic" | "professional" | "enterprise";

export interface HqPractice {
  id: string;
  name: string;
  status: PracticeStatus;
  plan: Plan;
  seats: number;
  users: number;
  providers: number;
  waiting: number;
  renews_on: string | null;
  time_zone: string;
  failed_24h: number;
  last_failure: string | null;
  admin_name: string | null;
  admin_email: string | null;
  admin_status: MemberStatus | null;
}

export type AdminLink = "invite" | "reset";

export interface NewPractice {
  name: string;
  admin_name: string;
  admin_email: string;
  plan: Plan;
  seats: number;
  time_zone: string;
}

export interface PracticeUpdate {
  name?: string;
  status?: PracticeStatus;
  plan?: Plan;
  seats?: number;
  renews_on?: string | null;
  time_zone?: string;
}

export interface DemoRequestRow {
  id: string;
  name: string;
  email: string;
  organization: string;
  message: string | null;
  received_at: string;
}

export interface HqPlace {
  code: string;
  name: string;
  active: boolean;
}

export interface HqActivityEntry {
  at: string;
  actor: string;
  action: string;
  practice_id: string | null;
  detail: string | null;
}

export interface HqActivityPage extends Page<HqActivityEntry> {
  actions: string[];
}

export interface HqActivityQuery {
  practice_id: string | null;
  action: string | null;
  offset: number;
}

export interface DemoRequest {
  name: string;
  email: string;
  organization: string;
  message: string | null;
}

export type DayFlag = "time_over_day" | "cloned_text" | "high_level_share";

export interface DayNote {
  id: string;
  patient_name: string | null;
  status: NoteStatus;
  lane: Lane | null;
  em_code: string | null;
  minutes: number | null;
}

export interface DayDuplicate {
  first: string;
  second: string;
  similarity: number;
}

export interface DayLevelCount {
  code: string;
  count: number;
}

export interface ProviderDay {
  provider: { id: string; name: string };
  service_date: string;
  notes: DayNote[];
  total_minutes: number;
  timed_notes: number;
  visits: number;
  levels: DayLevelCount[];
  high_level_visits: number;
  high_level_share: number | null;
  compared: number;
  duplicates: DayDuplicate[];
  flags: DayFlag[];
}

export interface NoteDay extends ProviderDay {
  note_id: string;
}

export interface FlaggedDays {
  from: string;
  to: string;
  days: ProviderDay[];
}

export type EmMixDirection = "above" | "below";
export type EmMixLean = "higher" | "lower";

export interface EmMixLevel {
  code: string;
  count: number;
  share: number;
  benchmark: number | null;
  points: number | null;
  direction: EmMixDirection | null;
}

export interface EmMixFamily {
  family: string;
  label: string;
  visits: number;
  has_benchmark: boolean;
  levels: EmMixLevel[];
  chi_square: number | null;
  degrees_of_freedom: number | null;
  p_value: number | null;
  outlier: boolean;
  reasons: ("points" | "chi_square")[];
  lean: EmMixLean | null;
}

export interface EmMixProvider {
  id: string;
  name: string;
  specialty: string | null;
  cms_specialty: string | null;
  visits: number;
  families: EmMixFamily[];
}

export interface EmMix {
  start: string;
  end: string;
  benchmark: { dataset: string; year: string; source_url: string };
  providers: EmMixProvider[];
}

export type RemittanceLineStatus = "paid_as_billed" | "downcoded" | "denied" | "matched" | "unmatched";
export type RemittanceFilter = "all" | "downcoded" | "denied" | "unmatched";
export type RemittanceCounts = Partial<Record<RemittanceLineStatus, number>>;

export interface RemittanceSummary {
  id: string;
  file_name: string;
  payer: string | null;
  paid_on: string | null;
  uploaded_by: string;
  uploaded_at: string;
  counts: RemittanceCounts;
}

export interface RemittanceListItem extends RemittanceSummary {
  next_appeal_by: string | null;
}

export interface RemittanceAdjustment {
  group: string;
  reason: string;
  cents: number;
}

export interface RemittanceLine {
  id: string;
  note_id: string | null;
  claim_ref: string | null;
  patient_name: string | null;
  service_date: string | null;
  billed_code: string | null;
  paid_code: string | null;
  billed_amount: number | null;
  paid_amount: number | null;
  adjustments: RemittanceAdjustment[];
  status: RemittanceLineStatus;
  appeal_by: string | null;
}

export interface RemittanceDetail {
  remittance: RemittanceSummary;
  lines: RemittanceLine[];
}

export interface RemittanceUpload {
  ids: string[];
  counts: RemittanceCounts;
}

export interface AppealDraft {
  line_id: string;
  note_id: string | null;
  appeal_by: string;
  text: string;
  file_name: string;
  defense_packet: string | null;
}

export type AppealDays = Record<PlanType, number>;

export interface IntakeSettings {
  enabled: boolean;
  prefix: string;
  provider_by_folder: Record<string, string>;
  place_code: string | null;
  visit_type: string;
}

export interface IntakeView extends IntakeSettings {
  watched_prefix: string;
}

export interface QueryMetrics {
  notes: number;
  queries: number;
  per_100_notes: number | null;
  response_rate: number | null;
  median_hours: number | null;
  agree_rate: number | null;
  repeat_rate: number | null;
}

export interface ProviderQueryMetrics extends QueryMetrics {
  provider_id: string;
  provider_name: string;
}

export interface QueryMetricsReport {
  days: number;
  total: QueryMetrics;
  providers: ProviderQueryMetrics[];
}

export interface Rate {
  successes: number;
  trials: number;
  value: number | null;
  low: number | null;
  high: number | null;
}

export interface AgreementSummary {
  notes: number;
  em: Rate;
  em_higher: Rate;
  em_lower: Rate;
  em_other: number;
  icd_precision: Rate;
  icd_recall: Rate;
  icd_f1: number | null;
  icd_exact: Rate;
  modifiers: Rate;
}

export type EmDirection = "match" | "higher" | "lower" | "family" | "absent";

export interface ElementComparison {
  em: { reference: string | null; compared: string | null; match: boolean; direction: EmDirection };
  icd: { matched: number; compared: number; reference: number; missing: string[]; extra: string[]; match: boolean };
  modifiers: { reference: string[]; compared: string[]; match: boolean };
}

export interface ClaimElements {
  em: string | null;
  icd: string[];
  modifiers: string[];
}

export type AgreementSide = "bodha" | "claim";
export type SampleScope = "practice" | "provider" | "specialty";
export type SamplePurpose = "audit" | "training";

export interface SampleOverview {
  id: string;
  purpose: SamplePurpose;
  scope: SampleScope;
  provider_name: string | null;
  specialty: string | null;
  start: string;
  end: string;
  requested: number;
  notes: number;
  done: number;
  status: "open" | "done";
  reviewers: string[];
  started_by: string | null;
  started_at: string;
  completed_at: string | null;
  em: Rate;
  em_claim: Rate;
}

export interface SampleItemRow {
  id: string;
  position: number;
  provider_name: string;
  service_date: string;
  reviewer_name: string;
  status: "open" | "done";
  answer: ClaimElements | null;
  bodha: ClaimElements | null;
  claim: ClaimElements | null;
  agreement: Record<AgreementSide, ElementComparison> | null;
}

export interface ProviderAgreement extends Record<AgreementSide, AgreementSummary> {
  provider_id: string;
  provider_name: string;
}

export interface SampleResults {
  sample: SampleOverview;
  summary: Record<AgreementSide, AgreementSummary>;
  providers: ProviderAgreement[];
  items: SampleItemRow[];
}

export interface QualityOptions {
  providers: { id: string; name: string; specialty: string | null }[];
  reviewers: { id: string; name: string; role: Role }[];
  specialties: string[];
  default_size: number;
  specialty_size: number;
}

export interface SampleInput {
  scope: SampleScope;
  start: string;
  end: string;
  reviewer_ids: string[];
  size: number | null;
  provider_id: string | null;
  specialty: string | null;
}

export interface BlindText {
  revision: number;
  source: "document" | "addendum";
  text: string;
}

export interface BlindItem {
  id: string;
  position: number;
  texts: BlindText[];
}

export interface BlindStep {
  sample: { id: string; purpose: SamplePurpose; total: number; done: number };
  item: BlindItem | null;
}

export interface BlindAnswer {
  em: string | null;
  icd: string[];
  modifiers: string[];
}

export interface BlindSubmitted {
  id: string;
  status: "open" | "done";
  purpose: SamplePurpose;
}

export type EligibilityReason = "eligible" | "no_audit" | "too_few_notes" | "agreement_low" | "too_many_higher";

export interface AutonomyEligibility {
  eligible: boolean;
  reason: EligibilityReason;
  sample_id: string | null;
  notes: number;
  em_low: number | null;
  higher_share: number | null;
}

export interface ProviderAutonomy {
  id: string;
  name: string;
  credential: string;
  specialty: string | null;
  auto_approve: boolean;
  eligibility: AutonomyEligibility;
}

export type LevelMixStatus = "steady" | "shifted" | "not_enough";

export interface LevelMixWindow {
  start: string;
  end: string;
  notes: number;
}

export interface LevelMix {
  recent: LevelMixWindow;
  prior: LevelMixWindow;
  levels: { level: string; recent: number; prior: number }[];
  test: { statistic: number; degrees_of_freedom: number; p_value: number } | null;
  status: LevelMixStatus;
}

export type EvalMetric = "em" | "icd_f1" | "modifiers";
export type EvalRunStatus = "queued" | "running" | "done" | "failed";

export interface EvalSummary {
  cases: number;
  scored: number;
  failed: number;
  em: Rate;
  em_higher: Rate;
  em_lower: Rate;
  icd_precision: Rate;
  icd_recall: Rate;
  icd_f1: number | null;
  modifiers: Rate;
  consistency: Record<"em" | "icd" | "modifiers" | "all", Rate>;
  error?: string;
}

export interface EvalRunChange {
  deltas: Partial<Record<EvalMetric, number>>;
  dropped: EvalMetric[];
  status: "dropped" | "holding";
}

export interface EvalRunView {
  id: string;
  status: EvalRunStatus;
  model: string;
  prompt_version: string;
  requested_at: string | null;
  finished_at: string | null;
  summary: Partial<EvalSummary>;
  change: EvalRunChange | null;
}

export interface EvalRuns {
  cases: number;
  runs: EvalRunView[];
}

export interface EvalCaseRow {
  note_id: string;
  provider_name: string;
  service_date: string;
  em: string | null;
  level: string | null;
  icd: string[];
  modifiers: string[];
  added_at: string;
}

export interface EvalCandidate {
  note_id: string;
  provider_name: string;
  service_date: string;
  codes: string[];
}

export interface AssignedSample {
  id: string;
  purpose: SamplePurpose;
  total: number;
  done: number;
  started_at: string;
}

export interface TrainingOverview {
  sets: AssignedSample[];
  scores: Record<AgreementSide, AgreementSummary>;
}

export interface TrainingSuggestion {
  key: string;
  kind: string;
  action: string;
  title: string;
  reasoning: string;
  code_before: string | null;
  code_after: string | null;
  evidence: string[];
}

export interface TrainingFeedback {
  item_id: string;
  sample_id: string;
  answer: ClaimElements;
  bodha: ClaimElements;
  claim: ClaimElements;
  agreement: Record<AgreementSide, ElementComparison>;
  suggestions: TrainingSuggestion[];
}

export interface TrainingInput {
  trainee_id: string;
  start: string;
  end: string;
  size: number;
  provider_id: string | null;
}

export type ClaimEdit =
  | { kind: "ptp"; column1: string; column2: string; modifier_allowed: boolean; bypassed_by: string | null }
  | { kind: "mue"; code: string; units: number; limit: number; mai: number }
  | { kind: "aoc"; code: string; primaries: string[] };

export type PayerFlagRule =
  | "telehealth_place"
  | "audio_only_place"
  | "home_telehealth_ended"
  | "complexity_with_25"
  | "g2211_replaced"
  | "level_downcode_risk"
  | "audio_only_risk_adjustment"
  | "nursing_incident_to"
  | "initial_visit_repeated";

export type PayerFlagSeverity = "denial" | "risk" | "reminder";

export interface PayerFlag {
  rule: PayerFlagRule;
  severity: PayerFlagSeverity;
  codes: string[];
  earlier?: string;
}

export interface ClaimChecks {
  ncci: { quarter: string; covers: boolean };
  edits: ClaimEdit[];
  payer: { name: string; plan_type: string | null } | null;
  payer_flags: PayerFlag[];
}
