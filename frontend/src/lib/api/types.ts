export type PracticeRole = "admin" | "coder" | "cdi" | "compliance" | "biller" | "viewer";
export type Role = "hq" | PracticeRole;

export type CheckKey = "em" | "icd" | "cdi" | "audit" | "mips";
export type Checks = Record<CheckKey, boolean>;

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
}

export interface QueueRow extends NoteSummary {
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
  offset?: number;
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

export interface DecisionRecord {
  key: string;
  choice: Choice;
  by: string | null;
  at: string;
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
  history: NoteHistory;
  requests: AddendumRequestView[];
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

export interface BillingList {
  items: BillingRow[];
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

export interface SecuritySettings {
  mfa_roles: PracticeRole[];
  idle_minutes: IdleMinutes;
  private_messages: boolean;
}

export interface PracticeSetup {
  sections: Record<SetupSectionKey | "providers", SetupSection>;
  complete: number;
  total: number;
  checks: Checks;
  missing_npi: number;
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
  actor_kind: "user" | "provider";
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
}

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

export interface DemoRequest {
  name: string;
  email: string;
  organization: string;
  message: string | null;
}
