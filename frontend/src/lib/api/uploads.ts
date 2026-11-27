import { request } from "./client";
import type { BatchPage, FileDetail, FilePreview, Place, Provider, UploadResult } from "./types";

export function previewFiles(files: File[]): Promise<FilePreview[]> {
  const form = new FormData();
  for (const file of files) form.append("files", file, file.name);
  return request<FilePreview[]>("/api/uploads/preview", { method: "POST", form });
}

export function buildUploadForm(visitType: string, files: File[], details: FileDetail[]): FormData {
  const form = new FormData();
  form.set("visit_type", visitType);
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
