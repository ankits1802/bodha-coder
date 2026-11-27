import { request, requestNothing } from "./client";
import type {
  BlindAnswer,
  BlindStep,
  BlindSubmitted,
  EvalCandidate,
  EvalCaseRow,
  EvalRunView,
  EvalRuns,
  LevelMix,
  ProviderAutonomy,
  QualityOptions,
  SampleInput,
  SampleOverview,
  SampleResults,
  TrainingFeedback,
  TrainingInput,
  TrainingOverview,
} from "./types";

const segment = encodeURIComponent;

export function getQualityOptions(): Promise<QualityOptions> {
  return request<QualityOptions>("/api/quality/options");
}

export async function getSamples(): Promise<SampleOverview[]> {
  return (await request<{ items: SampleOverview[] }>("/api/quality/samples")).items;
}

export function startSample(input: SampleInput): Promise<{ id: string }> {
  return request<{ id: string }>("/api/quality/samples", { body: input });
}

export function getSampleResults(sampleId: string): Promise<SampleResults> {
  return request<SampleResults>(`/api/quality/samples/${segment(sampleId)}`);
}

export async function getProviderAutonomy(): Promise<ProviderAutonomy[]> {
  return (await request<{ items: ProviderAutonomy[] }>("/api/quality/providers")).items;
}

export function setAutoApprove(providerId: string, on: boolean): Promise<ProviderAutonomy> {
  return request<ProviderAutonomy>(`/api/quality/providers/${segment(providerId)}/auto-approve`, {
    method: "PUT",
    body: { on },
  });
}

export function getLevelMix(): Promise<LevelMix> {
  return request<LevelMix>("/api/quality/level-mix");
}

export function getEvaluations(): Promise<EvalRuns> {
  return request<EvalRuns>("/api/quality/evaluations");
}

export function queueEvaluation(): Promise<EvalRunView> {
  return request<EvalRunView>("/api/quality/evaluations", { method: "POST" });
}

export async function getEvalCases(): Promise<EvalCaseRow[]> {
  return (await request<{ items: EvalCaseRow[] }>("/api/quality/eval-cases")).items;
}

export async function getEvalCandidates(): Promise<EvalCandidate[]> {
  return (await request<{ items: EvalCandidate[] }>("/api/quality/eval-cases/candidates")).items;
}

export function addEvalCase(noteId: string): Promise<{ id: string; note_id: string }> {
  return request<{ id: string; note_id: string }>("/api/quality/eval-cases", { body: { note_id: noteId } });
}

export function removeEvalCase(noteId: string): Promise<void> {
  return requestNothing(`/api/quality/eval-cases/${segment(noteId)}`, { method: "DELETE" });
}

export function getBlindStep(sampleId: string): Promise<BlindStep> {
  return request<BlindStep>(`/api/blind-review/${segment(sampleId)}/next`);
}

export function getBlindDocument(itemId: string): Promise<{ url: string }> {
  return request<{ url: string }>(`/api/blind-review/items/${segment(itemId)}/document`);
}

export function submitBlindAnswer(itemId: string, answer: BlindAnswer): Promise<BlindSubmitted> {
  return request<BlindSubmitted>(`/api/blind-review/items/${segment(itemId)}/answer`, { body: answer });
}

export function getTrainingFeedback(itemId: string): Promise<TrainingFeedback> {
  return request<TrainingFeedback>(`/api/blind-review/items/${segment(itemId)}/feedback`);
}

export function getTraining(): Promise<TrainingOverview> {
  return request<TrainingOverview>("/api/training");
}

export async function getTrainingSets(): Promise<SampleOverview[]> {
  return (await request<{ items: SampleOverview[] }>("/api/training/sets")).items;
}

export function assignTraining(input: TrainingInput): Promise<{ id: string }> {
  return request<{ id: string }>("/api/training/sets", { body: input });
}
