# 0003 Every result and decision is a stored revision

Context: the owner requires reasoning, suggestions and revisions to be stored properly, with
Postgres and S3/R2 in mind.

Choice: note texts, analyses, code sets and decisions are append-only; suggestions belong to one
analysis; the claim is always derived from billed codes plus the latest decisions. Validated
reports and suggestions live in Postgres (JSONB); raw model replies and PDFs live in the object
store under id-only keys. One adapter serves S3 and R2 (endpoint URL, region `auto`, optional
server-side encryption header).

Follows: editing billed codes creates a new analysis revision that re-derives suggestions from the
same report without a model call.
