# 0013 The job queue stays in Postgres; no SQS

Context: the owner asked whether Amazon SQS should carry the analysis jobs.

Choice: no. Each queued `analyses` row is the job, claimed with `SELECT … FOR UPDATE SKIP LOCKED`.
At the target of about 3,000 notes a day (bursts of tens of PDFs per upload, seconds to tens of seconds
per read) this queue has ample headroom, workers on any number of machines share it safely, retries
and stale-job recovery already work, and the job and its record cannot disagree because they are the
same row.

SQS would add a second store that must be kept consistent with Postgres (publishing after commit and
a reconciler for lost messages), another AWS service to provision and monitor, and new failure modes,
for capacity the product does not need.

Follows: the worker reports the number of queued and running analyses as a CloudWatch metric, and the
worker service scales on it. Revisit if volume grows by orders of magnitude or other systems need to
consume the same jobs.
