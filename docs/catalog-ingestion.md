# Catalog imagery on Railway

The catalog importer indexes OpenNGC records and adds actual DSS2 red survey
cutouts from CDS HiPS2FITS. The pinned catalog revision is in `pipeline/catalog.py`.
It includes the addendum (including M45), excludes duplicate/nonexistent entries,
and preserves published coordinates and classifications. These are catalog
records, not newly detected sources or model predictions.

Catalog data: Mattia Verga and OpenNGC contributors, [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/),
[source](https://github.com/mattiaverga/OpenNGC). Adaptations normalize names,
coordinates, and types and combine records with survey cutout metadata. Derived
catalog data retains the same license. Imagery: Digitized Sky Survey 2 / STScI;
cutouts provided by CDS Strasbourg through [HiPS2FITS](https://alasky.cds.unistra.fr/hips-image-services/hips2fits).
DSS digitization was funded by grant NAG W-2166 and uses photographic plates
from the Palomar Oschin Schmidt and UK Schmidt telescopes. See the
[survey acknowledgments and plate copyrights](https://archive.stsci.edu/dss/acknowledging.html).
This is targeted imagery across both hemispheres, not complete all-sky pixel coverage.

## Storage and operation

API and importer use `CATALOG_S3_BUCKET`, `CATALOG_S3_ENDPOINT_URL`,
`CATALOG_S3_ACCESS_KEY`, `CATALOG_S3_SECRET_KEY`, `CATALOG_S3_REGION=auto`,
and `CATALOG_S3_URL_STYLE=virtual`. Set these as Railway variables, never commit
credentials. Existing JWST/MinIO storage is independent.

`python -m pipeline.catalog_import --metadata-only` indexes names without images.
`python -m pipeline.catalog_import --max-images 250 --max-seconds 1500 --max-total-bytes 20000000000`
adds one bounded batch. Set the worker's Railway start command to that command
and its cron schedule to `0 */2 * * *`. Configure no HTTP healthcheck, 1 vCPU and 2 GB
maximum memory. The process exits between runs; no always-on Celery worker is
needed for this importer. Do not configure restart-on-success.

Railway now rejects newly configured legacy config-file paths. The API and worker
use service settings: root `/`, Dockerfile builder and `Dockerfile` path. API
uses the Dockerfile's default start command, `/health`, a 300-second healthcheck
timeout, and ON_FAILURE with three retries. Worker uses the importer command
above and restart policy NEVER. The former root `railway.json` was removed so
its HTTP healthcheck cannot accidentally apply to the batch worker. Web retains
its existing independent `/web` configuration.

Deterministic IDs, Postgres conflict handling, and a database advisory lock make
repeated and overlapping runs safe. Completed images are skipped. Failed images
remain pending for a later batch; ten failures stop a batch. Upload keys are
deterministic, so interrupted uploads are overwritten on retry. Originals, PNG
previews, and a JPEG tile pyramid are stored for each object. FITS downloads
retain the survey WCS. The storage accounting cap includes committed assets;
an interrupted upload can leave one target's partial assets outside this count.

Limits: 512-pixel cutouts, 20 GB total committed imagery, at most 250 attempts or
25 minutes per batch (an in-flight request may finish afterward), one request at
a time, and one second between targets. The run budget excludes initial catalog
indexing. At full CPU/memory limits the scheduled runtime is approximately
$10.42/month plus $0.30 for 20 GB storage and service upload egress, below the
additional $25/month budget. Actual usage should be lower; this is an estimate,
not a Railway billing hard limit. API traffic and existing services are separate.
Prices: [Railway plans](https://docs.railway.com/pricing/plans) and
[bucket billing](https://docs.railway.com/storage-buckets/billing).

`GET /api/catalog/summary` reports searchable records, ready/queued imagery,
hemisphere counts, and committed bytes. Verify M31, M42, M45, and NGC 253 through
the live search, object page, viewer, and FITS export after deploying. A record
without an image is explicitly marked queued. Observation lists are paginated
with `limit` (default 100, maximum 500) and `offset`.
