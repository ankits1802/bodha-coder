# 0012 Gemini on Vertex AI for PHI

Context: every review sends a clinical note, which is protected health information, to Gemini.
Until now Bodha reached Gemini only through the Gemini Developer API with an API key. A practice
may send PHI to a vendor only under a business associate agreement. Google's HIPAA Business
Associate Addendum applies only to the Google Cloud services on its HIPAA covered-products list,
and it says it does not apply to any product that is not a Covered Service. Generative AI on Vertex
AI (now listed as Generative AI on Agent Platform) is on that list; the Developer API is a separate
service reached with an API key and is not a Google Cloud covered service.

## Choice

- `GEMINI_BACKEND` picks the endpoint: `developer` (the default, `GEMINI_API_KEY`) or `vertex`.
  With `vertex`, `adapters/gemini.py` builds `genai.Client(enterprise=True, project=..., location=...)`
  from `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION`; `enterprise` is the google-genai 3.x name
  of the flag whose legacy alias is `vertexai`. A missing project or location is a configuration
  error at start, never a fallback to the Developer API.
- Credentials come from Application Default Credentials: the service account attached to the
  workload on Google Cloud, workload identity federation elsewhere, or `GOOGLE_APPLICATION_CREDENTIALS`
  naming a key file kept outside the repository. No credential is a Bodha setting and none goes in
  `.env.example`. The account needs the Vertex AI User role (`roles/aiplatform.user`) on the project.
- Data residency: `GOOGLE_CLOUD_LOCATION` names a regional endpoint (for example `us-central1`), so
  prompts and notes are processed in that region. Use a regional location, not `global`, when the
  practice's agreement requires US processing.
- The Files API does not exist on Vertex. Vertex takes PDFs inline up to 50 MiB on every current
  endpoint (Gemini 2.5 endpoints that have not migrated; Gemini 3 and later accept 256 MB per
  attachment), which is above `MAX_UPLOAD_MB` (40). A PDF above `VERTEX_INLINE_PDF_LIMIT_BYTES`
  raises `ModelRequestRejected("PDF too large for Vertex inline; split it")`, which the worker
  records as a permanent failure with that reason. The Developer API keeps its 14 MiB inline limit
  and the Files API above it.
- No Cloud Storage upload. A `GEMINI_GCS_BUCKET` path would add a second store of PHI with its own
  credentials, retention and deletion, a new pinned dependency (`google-cloud-storage`) and a
  failure mode on every large note, for a size the upload limit already rules out.

## Follows

- A practice that sends real notes signs Google's BAA for the project, keeps the project to
  covered services, checks the current covered-products list, and reviews the Vertex AI data
  caching and abuse-monitoring settings for zero data retention.
- Raising `MAX_UPLOAD_MB` above 50 makes large PDFs fail on Vertex; revisit the Cloud Storage path
  then.
- The model name (`GEMINI_MODEL`) must be one Vertex serves in the chosen location.
