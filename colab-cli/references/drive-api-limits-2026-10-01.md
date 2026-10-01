# Google Drive API Quotas and Cost Notes — verified 2026-10-01

Use this reference when a Colab workflow mounts Google Drive, transfers large
datasets/checkpoints, hits Drive rate limits, or asks whether Drive API usage is
billable.

Primary source:
https://developers.google.com/workspace/drive/api/guides/limits

Google changed Drive API quotas on 2026-05-01. Projects that used Drive API
between 2025-11 and 2026-04 can remain on previously assigned quotas, so do not
assume the standardized values below for a grandfathered project. Inspect the
project's Google Cloud Quotas & System Limits page when exact enforcement
matters.

## Standard Drive API limits

For projects subject to the standardized model:

| Limit | Standard value |
| --- | ---: |
| Per minute per project | 1,000,000 quota units |
| Per minute per user per project | 325,000 quota units |
| Per day per project egress | 1 TB / 24 h |
| Daily no-additional-charge threshold | 400,000,000 quota units / 24 h |

Representative REST method costs documented by Google:

| Action | Quota units |
| --- | ---: |
| Read item, e.g. files.get | 5 |
| List items, e.g. files.list | 100 |
| Download item, e.g. files.download | 200 |
| Edit item, e.g. files.update | 50 |
| Other actions, e.g. files.generateIds | 5 |

If Drive returns HTTP 403 User rate limit exceeded or HTTP 429 Rate limit
exceeded, retry with exponential backoff. Do not hammer the same request in a
tight loop.

## Data-transfer direction

For ordinary Drive API semantics:

- Drive -> Colab/local/client is egress from Drive/Google and is the direction
  relevant to the 1 TB/day project egress limit.
- Colab/local/client -> Drive is upload/ingress and does not consume that 1 TB
  egress budget.
- Google Workspace users have a separate 750 GB/day upload+copy constraint
  across My Drive and shared drives.
- Maximum upload file size is 5 TB.
- Maximum copy size is 750 GB.

Important DriveFS caveat: Google's Drive API quota page defines project egress
and REST-method quota units, but does not explicitly document that every byte
read through Colab DriveFS is accounted one-for-one against that Drive API
project egress metric. Treat Drive -> runtime as the relevant egress direction,
but do not claim exact DriveFS quota accounting without checking the project's
actual Cloud quota/usage telemetry.

## Pricing

Google states that standard Drive API use has no additional cost. Usage under
the 400,000,000 quota-unit daily threshold is not additionally billed.

Google also states that later in 2026, after at least 90 days' notice, usage
above standard daily thresholds is planned to generate Google Cloud charges and
quota increases will require billing. Do not quote a future price per unit until
Google publishes it.

Drive API billing is separate from Colab compute/Compute Units. A Drive mount
does not by itself mean a separate Colab GPU charge beyond normal Colab compute
usage.

## Operational guidance for large Colab jobs

- Avoid repeatedly rereading multi-hundred-GB datasets from Drive when a local
  runtime cache or staged copy is sufficient.
- For long jobs, record approximate bytes read from Drive and bytes written to
  Drive separately.
- For pipelines near 750 GB upload/day or 1 TB project egress/day, inspect the
  actual Google Cloud project quota/usage dashboard before starting another
  large transfer.
- Keep retry behavior bounded and exponential on Drive 403/429 responses.
