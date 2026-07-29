# NYC Subway J/Z Planned Service Calendar

A small Python 3.12 application that turns upcoming, material, planned J/Z subway changes from the
official MTA service-alert feed into an idempotently maintained Google Calendar.

The [reference-project audit](AUDIT.md) explains what was retained and replaced.

## How classification works

The application first requires a planned-work entity (`:planned_work:` in the MTA entity ID),
unless `INCLUDE_REALTIME_ALERTS=true`. It examines every `informed_entity` selector.

An alert is eligible when either:

1. a selector names `J` or `Z`; or
2. a selector names a verified J/Z station and rider-facing text explicitly names J or Z service.

The second rule is deliberately conjunctive. M-only work at Myrtle Av or another shared station
does not enter the calendar merely because the station is on the J/Z corridor.

Eligible alerts must then match a material structured MTA alert type: part/full suspension,
reroute, express/local change, stops skipped, reduced service, or special schedule. Text matching
is a secondary fallback for no-train/suspension language, reroutes, early termination, station
bypasses, shuttle buses, major frequency reductions, and suspended Z skip-stop service. Quantified
frequency alerts are treated as major only at headways of 12 minutes or longer; routine notices
such as “trains run every 10 minutes” are excluded.
Delay-only, elevator, boarding-only, station-notice, and general informational alerts are excluded
by default. Extra-service alerts are excluded unless they explicitly describe another train
running via the J line, which is treated as a reroute affecting J riders.

The checked-in [station map](jz_calendar/data/jz_stations.json) was generated on 2026-07-28 by
joining J/Z trips to stop times and parent stations in the official MTA static GTFS archive. Its
source URL and snapshot date are recorded in the file. Review/update it when MTA routing changes.

## Synchronization guarantees

Each active period becomes a separate event. Its stable key is SHA-256 over MTA alert ID plus the
period's start/end Unix timestamps. The key, alert ID, MTA update time, classifier category, and a
management marker are stored as private Google Calendar extended properties.

On each run the application:

- creates missing keys;
- updates changed events in place;
- removes duplicates and future managed events no longer desired;
- leaves ended historical events untouched.

Only this application's marked events are considered. The MTA client requires a valid, non-empty,
full-dataset response before Calendar access begins. Fetch, JSON, validation, or parse failures
abort synchronization, so an outage or empty response cannot erase the calendar.

Times are parsed as UTC instants and rendered with Python's `zoneinfo` for
`America/New_York`, including DST transitions. Correctness does not depend on an exact scheduler
start time.

## Google Calendar setup

1. In Google Calendar, create a dedicated calendar (for example, “NYC J/Z Planned Service”).
2. In Google Cloud, create a project, enable the **Google Calendar API**, and create a service
   account. No downloadable key is required for the default GitHub deployment.
3. In the calendar's **Settings and sharing**, share the calendar with the service account's
   `client_email` and grant **Make changes to events**.
   If Google Workspace policy disables write access for external identities, create an internal,
   invited-only group, add the service account as its only automation member, and grant that group
   **Make changes and see all event details** instead. Group membership and Calendar ACL changes
   can take several minutes to propagate.
4. Copy the value under **Integrate calendar → Calendar ID**.
5. To make it publicly subscribable, under **Access permissions for events** enable
   **Make available to public**. Public viewers can use the calendar's public iCal address or add
   the Calendar ID in Google Calendar. Confirm this visibility choice is acceptable; event content
   becomes public.
6. Store the Calendar ID as a GitHub secret and configure keyless Workload Identity Federation as
   described below.

The default deployment intentionally uses short-lived credentials and works when the
`iam.disableServiceAccountKeyCreation` organization policy is enforced.

If Workspace policy prevents an external service account from receiving write access, run the
manual **Bootstrap service-account-owned calendar** workflow with confirmation `CREATE`. It creates
a dedicated public calendar owned by the automation identity and prints its Calendar ID. Store that
ID in `GOOGLE_CALENDAR_ID` and in `site/config.js`. This avoids changing Workspace sharing policy;
the tradeoff is that Google does not allow ownership of a service-account-owned calendar to be
transferred later.

## Local development

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
# Export values from .env with your preferred environment loader.
ruff check .
ruff format --check .
pytest
jz-calendar --dry-run
```

`--dry-run` overrides `DRY_RUN` and still needs read access to the real calendar so it can calculate
the diff. It never calls create, update, or delete.

Configuration:

| Variable | Default | Meaning |
| --- | --- | --- |
| `GOOGLE_CALENDAR_ID` | required | Dedicated target calendar ID |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | optional | Local JSON-key fallback; omit when using ADC/WIF |
| `TARGET_ROUTES` | `J,Z` | Comma-separated target route IDs |
| `INCLUDE_REALTIME_ALERTS` | `false` | Allow otherwise-classifiable non-planned alerts |
| `DRY_RUN` | `false` | Log changes without mutation |
| `LOG_LEVEL` | `INFO` | Python log level |

Example dry-run JSON lines (values are illustrative):

```json
{"timestamp":"2026-07-28T15:00:01+00:00","level":"INFO","logger":"jz_calendar.sync","message":"calendar_create","event":"calendar_create","key":"16b21f…","title":"[J] No trains between Broadway Junction and Jamaica Center","dry_run":true}
{"timestamp":"2026-07-28T15:00:01+00:00","level":"INFO","logger":"jz_calendar.sync","message":"calendar_update","event":"calendar_update","key":"8b3d74…","title":"[Z] Skip-stop service suspended","dry_run":true}
{"timestamp":"2026-07-28T15:00:01+00:00","level":"INFO","logger":"jz_calendar.main","message":"sync_complete","event":"sync_complete","creates":1,"updates":1,"deletes":0,"unchanged":4,"dry_run":true}
```

## GitHub Actions deployment

Add repository secret:

- `GOOGLE_CALENDAR_ID`

The default workflow uses keyless **Workload Identity Federation** instead of a service-account
key. Add these repository variables:

- `GCP_WORKLOAD_IDENTITY_PROVIDER` — the provider's full resource name, beginning with
  `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/`
- `GCP_SERVICE_ACCOUNT` — `j-z-train-calendar@client-dashboard-461117.iam.gserviceaccount.com`

The workflow in `.github/workflows/sync.yml` runs at minute 17 every three hours, serializes runs,
installs dependencies, runs Ruff and pytest, then synchronizes. It is also manually dispatchable
with a dry-run option. GitHub documents that scheduled jobs can be delayed; the diff-based design
does not assume exact timing. Scheduled workflows run from the default branch, so keep the workflow
there and ensure repository Actions are enabled.

### Keyless GitHub authentication

Service-account key creation can remain disabled. After the GitHub repository exists:

1. In Google Cloud project `client-dashboard-461117`, enable the IAM, Security Token Service, and
   Service Account Credentials APIs.
2. Under **IAM & Admin → Workload Identity Federation**, create a pool and an OpenID Connect
   provider for GitHub. Use issuer `https://token.actions.githubusercontent.com`.
3. Map `google.subject` to `assertion.sub` and `attribute.repository` to
   `assertion.repository`.
4. Restrict the provider with the condition
   `assertion.repository == 'GITHUB_OWNER/GITHUB_REPOSITORY'`.
5. Grant that repository principal **Workload Identity User** on the
   `j-z-train-calendar` service account.
6. Copy the provider's full resource name and service-account email into the GitHub repository
   variables listed above.

The authentication action creates short-lived Application Default Credentials for each workflow
run. The Python application discovers those credentials automatically. For local development,
either run `gcloud auth application-default login` or set the optional
`GOOGLE_SERVICE_ACCOUNT_JSON` fallback when organizational policy permits it.

## Public landing page

The responsive static landing page in `site/` offers separate Google Calendar subscription buttons
for J/Z and L service and credits the original L-calendar creator, Reddit user
[`u/alexmerm`](https://www.reddit.com/r/Bushwick/comments/1dj2t3o/i_made_a_google_cal_which_lets_you_know_when_the/).
The L button uses the public calendar linked by the original project.

After creating the J/Z calendar, replace `REPLACE_WITH_PUBLIC_JZ_CALENDAR_ID` in
`site/config.js` with its Calendar ID. A Calendar ID is public subscription information, not a
credential. Until configured, the J/Z button remains visibly disabled.

The `pages.yml` workflow publishes `site/` whenever it changes on `main`. In the GitHub repository,
open **Settings → Pages** and set **Source** to **GitHub Actions**. Push the configured site or run
the workflow manually; its deployment summary provides the public URL. You can later attach a
custom domain in the same Pages settings.

Optional container use:

```bash
docker build -t jz-calendar .
docker run --rm --env-file .env jz-calendar --dry-run
```

## Known limitations

- MTA does not expose a permanent machine-readable taxonomy for every rider-facing phrase. New or
  renamed alert types may be conservatively excluded until rules and fixtures are updated.
- The station fallback recognizes explicit forms such as `[J]`, `[Z]`, “J trains,” “Z service,”
  and “J/Z.” Unusually worded copy can be missed by design to avoid false positives.
- A changed active-period boundary intentionally produces a new deterministic key; the old future
  key is deleted and the new one created.
- Open-ended periods are skipped because Google Calendar events require an end and guessing could
  create misleading public events.
- Public Calendar and iCal propagation are controlled by Google and may lag API writes.
- The static station map is a verified snapshot, not an automatically refreshed dependency.
