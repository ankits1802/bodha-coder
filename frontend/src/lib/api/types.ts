import type { components } from "./schema";

type Schemas = components["schemas"];

export type Checks = Schemas["Checks"];
export type CheckKey = keyof Checks;
export type PracticeSummary = Schemas["PracticeSummary"];
export type User = Schemas["User"];
export type Role = User["role"];
export type PracticeChoice = Schemas["PracticeChoice"];
export type OrganizationChoice = Schemas["OrganizationChoice"];
export type NewPracticeRequest = Schemas["NewPracticeBody"];
export type SignedIn = Schemas["SignedIn"];
export type MfaVerified = SignedIn;
export type MfaChallenge = Schemas["MfaChallenge"];
export type MfaStep = MfaChallenge["mfa"];
export type LoginResult = SignedIn | MfaChallenge;
export type MfaEnrolment = Schemas["MfaEnrolment"];
export type SignInProviders = Schemas["SignInProviders"];
export type IdentityProviderName = SignInProviders["providers"][number];
export type SignUpOptions = Schemas["SignUpOptions"];
export type PendingIdentity = Schemas["PendingIdentity"];
export type JoinOffer = Schemas["JoinOfferView"];
export type JoinMode = JoinOffer["mode"];
export type JoinPage = Schemas["JoinPage"];
export type JoinOutcome = Schemas["JoinOutcome"];
export type JoinResult = Schemas["JoinOutcome"]["outcome"];
export type JoinChoiceRequest = Schemas["JoinChoiceBody"];
export type IdentityJoinRequest = Schemas["IdentityJoinBody"];
export type SignupRequest = Schemas["SignupBody"];
export type IdentitySignupRequest = Schemas["IdentitySignupBody"];
export type SignedInDevice = Schemas["SignedInDevice"];
export type RecoveryCodeStatus = Schemas["RecoveryCodeStatus"];
export type RecoveryCodes = Schemas["RecoveryCodes"];
export type Preferences = Schemas["Preferences"];
export type TourRecord = Schemas["TourRecord"];
export type TourKey = TourRecord["tour"];
export type TourBody = Schemas["TourBody"];
export type TourOutcome = TourBody["outcome"];

export type Created = Schemas["Created"];
export type ErrorBody = Schemas["ErrorResponse"];
export type DocumentLink = Schemas["DocumentLink"];

export type NoteSummary = Schemas["NoteSummary"];
export type NoteStatus = NoteSummary["status"];
export type Lane = NonNullable<NoteSummary["lane"]>;
export type LaneReason = NonNullable<NoteSummary["lane_reason"]>;
export type LaneCount = Schemas["LaneCount"];
export type LaneCounts = Schemas["LaneCounts"];
export type QueueRow = Schemas["QueueRow"];
export type EmAction = NonNullable<QueueRow["em_action"]>;
export type BatchProgress = Schemas["BatchProgress"];
export type TodaySummary = Schemas["TodaySummary"];
export type QueuePage = Schemas["QueuePage"];
export type ProviderReasonCounts = Schemas["ProviderReasonCounts"];
export type ProviderReason = keyof ProviderReasonCounts;
export type QueueViewFilters = Schemas["QueueViewFilters"];
export type QueueSort = QueueViewFilters["sort"];
export type QueueViews = Schemas["QueueViews"];
export type BuiltinView = Schemas["BuiltinView"];
export type BuiltinViewKey = BuiltinView["key"];
export type SavedView = Schemas["SavedView"];
export type QueueViewBody = Schemas["QueueViewBody"];
export type InboxPage = Schemas["InboxPage"];
export type InboxEntry = Schemas["InboxEntry"];
export type InboxKind = InboxEntry["kind"];
export type InboxCount = Schemas["InboxCount"];
export type SearchResults = Schemas["SearchResults"];
export type CompliancePattern = Schemas["CompliancePattern"];
export type ComplianceRow = Schemas["ComplianceRow"];
export type ComplianceList = Schemas["ComplianceList"];

export type ProviderRef = Schemas["ProviderRef"];
export type Channel = ProviderRef["channel"];
export type NoteHeader = Schemas["NoteHeader"];
export type NoteText = Schemas["NoteText"];
export type TextSource = NoteText["source"];
export type AnalysisView = Schemas["AnalysisView"];
export type AnalysisStatus = AnalysisView["status"];
export type RequiredElement = Schemas["RequiredElement"];
export type CodingComplianceCheck = Schemas["CodingComplianceCheck"];
export type CmsCdiCompliance = Schemas["CmsCdiCompliance"];
export type CodeLinkingOpportunity = Schemas["CodeLinkingOpportunity"];
export type Finding = Schemas["Finding"];
export type FindingKind = Finding["kind"];
export type FindingAction = Finding["action"];
export type Choice = Finding["choice"];
export type CodeJson = Schemas["CodeJson"];
export type CodeType = CodeJson["type"];
export type AnalysisRevision = Schemas["AnalysisRevision"];
export type CodeSetRevision = Schemas["CodeSetRevision"];
export type PointerChoice = Schemas["PointerChoice"];
export type DecisionRecord = Schemas["DecisionRecord"];
export type NoteChangeRecord = Schemas["NoteChangeRecord"];
export type NoteChangeField = NoteChangeRecord["field"];
export type VoidInfo = Schemas["VoidInfo"];
export type NoteHistory = Schemas["NoteHistory"];
export type AddendumQuestion = Schemas["AddendumQuestion"];
export type AddendumAnswer = Schemas["AddendumAnswer"];
export type AddendumRequestView = Schemas["AddendumRequestView"];
export type RequestStatus = AddendumRequestView["status"];
export type NoteDetail = Schemas["NoteDetail"];
export type EstimateLine = Schemas["EstimateLine"];
export type ClaimEstimate = Schemas["ClaimEstimate"];
export type ClaimEstimates = Schemas["ClaimEstimates"];
export type RateSetting = ClaimEstimates["setting"];

export type NoteState = Schemas["NoteState"];
export type NoteLane = Schemas["NoteLane"];
export type ComplianceOutcome = Schemas["ComplianceOutcome"];
export type RequestCancelled = Schemas["RequestCancelled"];
export type NotePayer = Schemas["NotePayer"];
export type ApprovedNotes = Schemas["ApprovedNotes"];
export type AssignedNotes = Schemas["AssignedNotes"];
export type VoidedNotes = Schemas["VoidedNotes"];
export type QueuedNotes = Schemas["QueuedNotes"];
export type ReopenedNotes = Schemas["ReopenedNotes"];
export type RequestCreated = Schemas["RequestCreated"];
export type PointerLine = Schemas["PointerLine"];
export type ClaimDiagnosis = Schemas["ClaimDiagnosis"];
export type ClaimPointers = Schemas["ClaimPointers"];

export type ClaimChecks = Schemas["ClaimChecks"];
export type ClaimEdit = ClaimChecks["edits"][number];
export type PayerFlag = Schemas["PayerFlag"];
export type PayerFlagRule = PayerFlag["rule"];
export type PayerFlagSeverity = PayerFlag["severity"];

export type FilePreview = Schemas["FilePreview"];
export type MatchConfidence = Schemas["MatchConfidence"];
export type UploadResult = Schemas["UploadResult"];
export type UploadedBatch = Schemas["UploadedBatch"];
export type BatchPage = Schemas["BatchPage"];

export type ProviderDetails = Schemas["ProviderDetails"];
export type BillsUnder = NonNullable<ProviderDetails["bills_under"]>;
export type Provider = Schemas["Provider"];
export type Place = Schemas["Place"];
export type ImportedProviders = Schemas["ImportedProviders"];

export type BillingRow = Schemas["BillingRow"];
export type BillingSummary = Schemas["BillingSummary"];
export type BillingList = Schemas["BillingList"];
export type ClaimLinesFormat = NonNullable<Schemas["ClaimLinesBody"]["format"]>;
export type ClaimColumn = Schemas["ClaimColumn"];
export type ClaimStatus = ClaimColumn["status"];
export type ClaimReason = Schemas["ClaimReason"];
export type ClearinghouseSummary = Schemas["ClearinghouseSummary"];
export type ClaimSent = Schemas["ClaimSent"];
export type ClaimFileRecord = Schemas["ClaimFileRecord"];
export type ClaimFilePage = Schemas["ClaimFilePage"];
export type ClaimFileOutcome = ClaimFileRecord["outcome"];
export type AckUpload = Schemas["AckUpload"];
export type ClaimDetailsView = Schemas["ClaimDetailsView"];
export type ClaimDetailsRecord = Schemas["ClaimDetailsRecord"];
export type ClaimDetailsSuggestion = Schemas["ClaimDetailsSuggestion"];
export type ClaimDetailsInput = Schemas["ClaimDetailsBody"];
export type Relationship = ClaimDetailsInput["relationship"];
export type PatientSex = ClaimDetailsInput["patient_sex"];
export type ClearinghouseView = Schemas["ClearinghouseView"];
export type ClearinghouseConnection = Schemas["ClearinghouseConnectionView"];
export type ConnectionInput = Schemas["ConnectionBody"];
export type ClaimTransport = ClearinghouseConnection["transport"];
export type ClaimUsage = ClearinghouseConnection["usage"];
export type IdQualifier = ClearinghouseConnection["sender_qualifier"];
export type AuthKind = NonNullable<ClearinghouseConnection["auth_kind"]>;
export type HostKey = Schemas["HostKey"];
export type ConnectionCheck = Schemas["ConnectionCheck"];
export type Charge = Schemas["Charge"];
export type ChargeList = Schemas["ChargeList"];

export type Outcomes = Schemas["Outcomes"];
export type Insights = Schemas["Insights"];
export type UsageFigures = Schemas["UsageFigures"];
export type HqUsageFigures = Schemas["HqUsageFigures"];
export type UsageTaskFigures = Schemas["UsageTaskFigures"];
export type UsageStallFigures = Schemas["UsageStallFigures"];
export type UsageSpread = Schemas["UsageSpread"];
export type UsageTaskEvent = Schemas["UsageTaskBody"];
export type UsageStallEvent = Schemas["UsageStallBody"];
export type UsageEvent = UsageTaskEvent | UsageStallEvent;
export type UsageTask = UsageTaskEvent["task"];
export type UsageStep = UsageStallEvent["step"];
export type UsageOutcome = UsageTaskEvent["outcome"];
export type InsightEstimates = Schemas["InsightEstimates"];
export type PersonProductivity = Schemas["PersonProductivity"];

export type SetupSection = Schemas["SetupSection"];
export type SetupSectionKey = Exclude<keyof Schemas["SetupSections"], "providers">;
export type SecuritySettings = Schemas["SecuritySettings"];
export type PracticeRole = SecuritySettings["mfa_roles"][number];
export type IdleMinutes = SecuritySettings["idle_minutes"];
export type AccessLogYears = SecuritySettings["access_log_years"];
export type Payer = Schemas["Payer"];
export type PlanType = Payer["plan_type"];
export type ClaimFiling = NonNullable<Payer["claim_filing"]>;
export type PayerOption = Schemas["PayerOption"];
export type PracticeSetup = Schemas["PracticeSetup"];
export type FirstRun = Schemas["FirstRun"];
export type MipsMeasure = Schemas["MipsMeasure"];
export type MipsOverview = Schemas["MipsOverview"];
export type MipsChoice = Schemas["MipsChoice"];
export type PracticeMeasure = Schemas["PracticeMeasureView"];
export type PracticeMeasureInput = Schemas["PracticeMeasureBody"];
export type AccessLogEntry = Schemas["AccessLogEntry"];
export type AccessLogPage = Schemas["AccessLogPage"];
export type AccessLogPerson = Schemas["AccessLogPerson"];
export type AccessLogFilters = Schemas["AccessLogExportBody"];
export type IntakeView = Schemas["IntakeView"];
export type EmailIntake = Schemas["EmailIntakeView"];
export type IntakeSender = Schemas["IntakeSenderView"];
export type PreviousIntakeAddress = Schemas["PreviousIntakeAddress"];
export type IntakeTest = Schemas["IntakeTestView"];
export type IntakeMessagePage = Schemas["IntakeMessagePage"];
export type IntakeMessage = Schemas["IntakeMessageRow"];
export type IntakeMessageOutcome = IntakeMessage["outcome"];
export type IntakeRefusal = NonNullable<IntakeMessage["reason"]>;
export type IntakeFile = Schemas["IntakeMessageFile"];
export type EhrConnection = Schemas["EhrConnectionView"];
export type EhrStatus = EhrConnection["status"];
export type EhrRegistration = Schemas["EhrRegistrationView"];
export type EhrKeyAlgorithm = EhrRegistration["algorithm"];
export type EhrSettings = Schemas["EhrConnectionSettingsView"];
export type EhrSettingsInput = Schemas["EhrConnectionBody"];
export type EhrNoteType = EhrSettingsInput["note_types"][number];
export type EhrCheck = Schemas["EhrCheckView"];
export type EhrCheckStep = Schemas["EhrCheckStepView"];
export type EhrPullRun = Schemas["EhrPullRunView"];
export type EhrPullOutcome = EhrPullRun["outcome"];
export type EhrPullReason = NonNullable<EhrPullRun["reason"]>;
export type EhrPullRunPage = Schemas["EhrPullRunPage"];
export type EhrDocument = Schemas["EhrDocumentView"];
export type EhrDocumentReason = NonNullable<EhrDocument["reason"]>;
export type EhrDocumentPage = Schemas["EhrDocumentPage"];

export type TeamMember = Schemas["TeamMember"];
export type MemberStatus = TeamMember["status"];
export type TeamList = Schemas["TeamList"];

export type ProviderRequest = Schemas["ProviderRequest"];
export type RequestPurpose = ProviderRequest["purpose"];
export type LevelChangeView = Schemas["LevelChangeView"];
export type LevelChangeBody = Schemas["LevelChangeBody"];
export type LevelAnswer = LevelChangeBody["answer"];
export type LevelChangeResult = Schemas["LevelChangeResult"];
export type RespondResult = Schemas["RespondResult"];
export type RespondBody = Schemas["RespondBody"];
export type SignatureView = Schemas["SignatureView"];
export type SignatureSource = SignatureView["source"];
export type MySignature = Schemas["MySignature"];
export type SignatureDraftBody = Schemas["SignatureDraftBody"];
export type SigningChoice = Pick<RespondBody, "signature_id" | "remember_signature">;
export type SealVerification = Schemas["SealVerification"];
export type SigningEventType = SealVerification["event"];
export type VerificationProblem = SealVerification["problems"][number];
export type OtherRequest = Schemas["OtherRequest"];
export type CodeSent = Schemas["CodeSent"];
export type ProviderToken = Schemas["ProviderToken"];

export type HqOverview = Schemas["HqOverview"];
export type HqPractice = Schemas["HqPractice"];
export type PracticeStatus = HqPractice["status"];
export type Plan = HqPractice["plan"];
export type AdminLinkSent = Schemas["AdminLinkSent"];
export type AdminLink = AdminLinkSent["sent"];
export type AdminAppointment = Schemas["HqAdminBody"];
export type AdminAppointed = Schemas["AdminAppointed"];
export type Renewal = Schemas["Renewal"];
export type DemoRequestRow = Schemas["DemoRequestRow"];
export type HqPlace = Schemas["HqPlace"];
export type HqPracticePage = Schemas["HqPracticePage"];
export type HqPracticePlace = Schemas["HqPracticePlace"];
export type HqPerson = Schemas["HqPerson"];
export type HqSearchResults = Schemas["HqSearchResults"];
export type HqSearchPerson = Schemas["HqSearchPerson"];
export type HqPracticeHit = Schemas["HqPracticeHit"];
export type HqActivityEntry = Schemas["HqActivityEntry"];
export type HqActivityPage = Schemas["HqActivityPage"];
export type ActivityChange = Schemas["ActivityChange"];
export type AuditChain = Schemas["AuditChain"];
export type AuditVerification = Schemas["AuditVerification"];
export type PracticePurged = Schemas["PracticePurged"];
export type HqTeamMember = Schemas["HqTeamMember"];
export type HqExpenditure = Schemas["Expenditure"];
export type SpendFigures = Schemas["SpendFigures"];
export type PracticeSpend = Schemas["PracticeSpend"];
export type ProviderSpend = Schemas["ProviderSpend"];
export type HqInvite = Schemas["HqInviteBody"];
export type HqMemberUpdate = Schemas["HqMemberBody"];
export type HqOrganization = Schemas["HqOrganization"];
export type OrganizationStatus = HqOrganization["status"];
export type HqOrganizationPage = Schemas["HqOrganizationPage"];
export type HqOrganizationAdmin = Schemas["HqOrganizationAdmin"];
export type HqOrganizationHit = Schemas["HqOrganizationHit"];
export type NewOrganization = Schemas["OrganizationBody"];
export type OrganizationUpdate = Schemas["OrganizationUpdateBody"];
export type AttachPractice = Schemas["AttachPracticeBody"];
export type OrganizationAdminAppointment = Schemas["OrganizationAdminBody"];
export type OrganizationPurged = Schemas["OrganizationPurged"];

export type OrganizationOverview = Schemas["OrganizationOverview"];
export type OrganizationPracticeRow = Schemas["OrganizationPracticeRow"];
export type MyOrganizationPractice = Schemas["MyOrganizationPractice"];
export type OrganizationAdminRow = Schemas["OrganizationAdminRow"];
export type OrganizationPlan = Schemas["OrganizationPlan"];
export type PracticeUsage = Schemas["PracticeUsage"];
export type OrganizationInsights = Schemas["OrganizationInsights"];
export type PracticeInsight = Schemas["PracticeInsight"];
export type InsightFigures = Schemas["InsightFigures"];
export type LocationRequest = Schemas["LocationBody"];
export type AccessRequest = Schemas["AccessBody"];
export type OrganizationPersonRequest = Schemas["OrganizationPersonBody"];
export type Placement = Schemas["PlacementBody"];
export type CombinedBilling = Schemas["CombinedBillingBody"];

export type DomainClaim = Schemas["DomainClaimView"];
export type DomainJoinMode = DomainClaim["join_mode"];
export type DomainClaimRequest = Schemas["DomainBody"];
export type DomainEmailRequest = Schemas["DomainEmailBody"];
export type AdminMailbox = DomainEmailRequest["mailbox"];
export type DomainJoinRequest = Schemas["DomainJoinBody"];
export type VerifiedDomain = Schemas["VerifiedDomain"];
export type JoinRequestRow = Schemas["JoinRequestRow"];
export type JoinApproval = Schemas["JoinApprovalBody"];

export type PlanCatalog = Schemas["PlanCatalog"];
export type PlanTerms = Schemas["PlanTerms"];
export type PlanStatus = Schemas["PlanStatus"];
export type PlanStanding = PlanStatus["standing"];
export type PayerOrganization = Schemas["PayerOrganization"];
export type PlanSubscription = Schemas["PlanSubscription"];
export type BillingProvider = PlanSubscription["provider"];
export type BillingInterval = PlanSubscription["interval"];
export type BillingStatus = PlanSubscription["status"];
export type CheckoutRequest = Schemas["CheckoutBody"];
export type CheckoutPlan = CheckoutRequest["plan"];
export type RedirectLink = Schemas["RedirectLink"];

export type DayNote = Schemas["DayNote"];
export type DayDuplicate = Schemas["DayDuplicate"];
export type DayLevelCount = Schemas["DayLevelCount"];
export type ProviderDay = Schemas["ProviderDay"];
export type DayFlag = ProviderDay["flags"][number];
export type NoteDay = Schemas["NoteDay"];
export type FlaggedDays = Schemas["FlaggedDays"];

export type EmMixLevel = Schemas["EmMixLevel"];
export type EmMixDirection = NonNullable<EmMixLevel["direction"]>;
export type EmMixFamily = Schemas["EmMixFamily"];
export type EmMixLean = NonNullable<EmMixFamily["lean"]>;
export type EmMixProvider = Schemas["EmMixProvider"];
export type EmMix = Schemas["EmMix"];

export type RemittanceSummary = Schemas["RemittanceSummary"];
export type RemittanceCounts = RemittanceSummary["counts"];
export type RemittanceListItem = Schemas["RemittanceListItem"];
export type RemittancePage = Schemas["RemittancePage"];
export type RemittanceAdjustment = Schemas["RemittanceAdjustment"];
export type RemittanceLine = Schemas["RemittanceLine"];
export type RemittanceLineStatus = RemittanceLine["status"];
export type RemittanceDetail = Schemas["RemittanceDetail"];
export type RemittanceUpload = Schemas["RemittanceUpload"];
export type AppealDraft = Schemas["AppealDraft"];
export type AppealDays = Schemas["AppealDays"];

export type QueryMetrics = Schemas["QueryMetrics"];
export type ProviderQueryMetrics = Schemas["ProviderQueryMetrics"];
export type QueryMetricsReport = Schemas["QueryMetricsReport"];

export type Rate = Schemas["Rate"];
export type AgreementSummary = Schemas["AgreementSummary"];
export type AgreementSide = keyof Schemas["AgreementSides"];
export type ElementComparison = Schemas["ElementComparison"];
export type EmDirection = ElementComparison["em"]["direction"];
export type ClaimElements = Schemas["ClaimElements"];
export type SampleOverview = Schemas["SampleOverview"];
export type SampleScope = SampleOverview["scope"];
export type SamplePurpose = SampleOverview["purpose"];
export type SampleList = Schemas["SampleList"];
export type SampleItemRow = Schemas["SampleItemRow"];
export type ProviderAgreement = Schemas["ProviderAgreement"];
export type SampleResults = Schemas["SampleResults"];
export type QualityOptions = Schemas["QualityOptions"];
export type BlindText = Schemas["TextRevision"];
export type BlindItem = Schemas["BlindItem"];
export type BlindStep = Schemas["BlindStep"];
export type BlindAnswer = ClaimElements;
export type BlindSubmitted = Schemas["BlindSubmitted"];
export type AutonomyEligibility = Schemas["AutonomyEligibility"];
export type EligibilityReason = AutonomyEligibility["reason"];
export type ProviderAutonomy = Schemas["ProviderAutonomy"];
export type ProviderAutonomyList = Schemas["ProviderAutonomyList"];
export type LevelMixWindow = Schemas["LevelMixWindow"];
export type LevelMix = Schemas["LevelMix"];
export type LevelMixStatus = LevelMix["status"];
export type EvalSummary = Schemas["EvalSummary"];
export type EvalRunChange = Schemas["EvalRunChange"];
export type EvalMetric = EvalRunChange["dropped"][number];
export type EvalRunView = Schemas["EvalRunView"];
export type EvalRunStatus = EvalRunView["status"];
export type EvalRuns = Schemas["EvalRuns"];
export type EvalCaseRow = Schemas["EvalCaseRow"];
export type EvalCaseList = Schemas["EvalCaseList"];
export type EvalCandidate = Schemas["EvalCandidate"];
export type EvalCandidateList = Schemas["EvalCandidateList"];
export type EvalCaseAdded = Schemas["EvalCaseAdded"];
export type AssignedSample = Schemas["AssignedSample"];
export type TrainingOverview = Schemas["TrainingOverview"];
export type TrainingSuggestion = Schemas["TrainingSuggestion"];
export type TrainingFeedback = Schemas["TrainingFeedback"];

export type ComplianceDecision = Schemas["ComplianceBody"]["decision"];
export type OverrideChoice = Schemas["OverrideBody"];
export type OverrideReason = OverrideChoice["reason"];
export type OverrideView = Schemas["OverrideView"];
export type ReturnReasonChoice = Schemas["ReturnReasonBody"];
export type ReturnReason = ReturnReasonChoice["reason"];
export type ReturnView = Schemas["ReturnView"];
export type ReturnRecord = Schemas["ReturnRecord"];
export type SnapshotRecord = Schemas["SnapshotRecord"];
export type ExportRecord = Schemas["ExportRecord"];
export type ExportFormat = ExportRecord["format"];
export type NoteExportRecord = Schemas["NoteExportRecord"];
export type ExportPage = Schemas["ExportPage"];
export type AttestationRecord = Schemas["AttestationRecord"];
export type AttestationAnswer = AttestationRecord["answer"];
export type NoteComment = Schemas["NoteComment"];
export type NoteComments = Schemas["NoteComments"];
export type CommentPerson = Schemas["CommentPerson"];
export type CommentInput = Schemas["CommentBody"];
export type ReviewSettings = Schemas["ReviewSettings"];
export type QuestionEdit = Schemas["QuestionBody"];
export type AskBody = Schemas["AskBody"];
export type DemoRequest = Schemas["DemoBody"];
export type SampleInput = Schemas["SampleBody"];
export type TrainingInput = Schemas["TrainingBody"];
export type PayerInput = Omit<Payer, "id">;
export type ProviderInput = Omit<Provider, "id" | "channel"> & { channel: Channel | null };

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

export interface QueueQuery {
  lane?: Lane;
  reason?: LaneReason;
  search?: string;
  provider_id?: string;
  batch_id?: string;
  assigned?: string;
  overdue?: boolean;
  sort?: QueueSort;
  offset?: number;
}

export interface FilePlacement {
  provider_id: string;
  service_date: string;
  place_code: string;
}

export interface FileDetail extends FilePlacement {
  billed: string | null;
  visit_type: string | null;
}

export interface UploadPlan extends FilePlacement {
  visit_type: string;
}

export type BillingShow = "ready" | "exported" | "today" | "all";
export type InsightDays = 7 | 14 | 30 | 90;
export type RemittanceFilter = "all" | "downcoded" | "denied" | "unmatched";

export interface InviteBody {
  name: string;
  email: string;
  role: PracticeRole;
}

export interface MemberUpdate {
  role?: PracticeRole;
  blocked?: boolean;
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

export interface HqActivityQuery {
  practice_id: string | null;
  action: string | null;
  offset: number;
}

export interface SpendRange {
  from: string;
  to: string;
}
