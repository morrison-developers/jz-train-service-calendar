# Audit of LTrainClosureCalendar

Reference inspected: [alexmerm/LTrainClosureCalendar](https://github.com/alexmerm/LTrainClosureCalendar)
(two commits, `master` branch), plus the live MTA JSON alert feed on 2026-07-28.

## Worth retaining

- The official MTA subway-alert endpoint and the core idea of periodically reconciling planned
  alerts into a public Google Calendar.
- Conversion of Unix timestamps to `America/New_York`.
- The policy of deleting feed-removed events only while they are still relevant and preserving
  ended events.
- A container image as an optional runtime.

These are design ideas rather than reusable code. The original application is a single Lambda
function tightly coupled to AWS, pandas, GCSA, OAuth token files, and S3.

## Replaced

- The first-entity route filter is replaced by parsing every `informed_entity`.
- One accepted alert type is replaced by structured category classification with a conservative
  text fallback.
- S3/Parquet state is replaced by Google Calendar private extended properties.
- Consumer OAuth token files are replaced by service-account credentials.
- Delete-and-recreate updates are replaced with in-place Calendar API updates.
- AWS Lambda/CloudWatch is replaced by GitHub Actions, while a generic Dockerfile remains.
- Ad-hoc printing is replaced by JSON structured logs.
- The monolith is split into typed fetch, parse, classify, event, Calendar, sync, configuration,
  logging, and CLI modules.

## Bugs and brittle assumptions found

- `informed_entity[0]["route_id"]` both misses routes later in the array and raises when the first
  selector is station-only.
- It accepts only `Planned - Part Suspended`, missing full suspensions, reroutes, skipped stops,
  reduced service, shuttle buses, special schedules, and other material patterns.
- `id.split(":")` assumes exactly three fields.
- It assumes both `en` and `en-html` translations always exist and indexes the first match.
- It does not set a request timeout, check HTTP status, or validate full-dataset semantics.
- An empty/malformed feed can fail after partial processing; state safety depends on where it fails.
- Updating by delete/recreate changes Google event IDs and can briefly remove events.
- Calendar identity lives only in an external Parquet snapshot, so it cannot be reconstructed from
  the calendar and is vulnerable to state/calendar drift.
- The update test considers only MTA `updated_at`; changed periods/content with a bad or unchanged
  upstream timestamp can be missed.
- Duplicate rows in the Parquet state and partially failed Calendar writes are not reconciled.
- S3 downloads of credentials, OAuth token pickle, and state add failure modes and AWS coupling.
- OAuth token pickle storage is inappropriate for a headless service-account-friendly workflow.
- Exceptions in notification handling can obscure the original failure.
- Dependencies are unbounded and there are no automated tests or lint checks.
- The Dockerfile comment and packaging are Lambda-specific, and the requirements file appears to
  concatenate `boto3` directly with the next Dockerfile line in the raw audit output.

## Live-feed observations

The feed is a GTFS-Realtime 2.0 JSON representation with `FULL_DATASET` incrementality. MTA-specific
metadata is under `alert["transit_realtime.mercury_alert"]`. On inspection, the feed contained
planned categories including `Planned - Part Suspended`, `Planned - Suspended`,
`Planned - Reroute`, `Planned - Stops Skipped`, `Planned - Express to Local`,
`Reduced Service`, `Special Schedule`, `Boarding Change`, and `Extra Service`. Entities commonly
mix route and stop selectors, confirming that all selectors must be examined.
