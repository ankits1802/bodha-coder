import { request } from "./client";
import type { BatchPage, FileDetail, FilePreview, Place, Provider, UploadPlan, UploadResult } from "./types";

export function previewFiles(fileNames: string[]): Promise<FilePreview[]> {
  return request<FilePreview[]>("/api/uploads/preview", { body: { file_names: fileNames } });
}

export function buildUploadForm(plan: UploadPlan, files: File[], details: FileDetail[]): FormData {
  const form = new FormData();
  form.set("provider_id", plan.provider_id);
  form.set("service_date", plan.service_date);
  form.set("place_code", plan.place_code);
  form.set("visit_type", plan.visit_type);
  form.set("details", JSON.stringify(details));
  for (const file of files) form.append("files", file, file.name);
  return form;
}

export function uploadNotes(form: FormData): Promise<UploadResult> {
  return request<UploadResult>("/api/uploads", { method: "POST", form });
}

export function getUploadHistory(offset: number): Promise<BatchPage> {
  return request<BatchPage>("/api/batches", { query: { offset } });
}

export function getProviders(): Promise<Provider[]> {
  return request<Provider[]>("/api/providers");
}

export function getPlaces(): Promise<Place[]> {
  return request<Place[]>("/api/places");
}
