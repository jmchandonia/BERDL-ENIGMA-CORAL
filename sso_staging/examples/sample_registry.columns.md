# Example brick-like structure: `enigma.sso_staging.sample_registry`

One row per **physical sample** (the assay manifest, `Assay Metadata` sheet:
Timepoint × Date × Well × Assay → Sample ID). **Refresh-from-source** (upsert /
replace by `sdt_sample_name`). This table is the **provenance backbone**: it is
the staged form of CORAL's `sdt_sample` static object, so every ID must be
CORAL-legal now (see `NAMING.md`). When assay *results* arrive, they attach
here by `sdt_sample_name`.

Unlike the other two tables it has **no COMO measurement columns** — it is a
registry of attributes (like a CORAL static-object import), so there are no
`ddt_brick` measurement rows. It carries FK columns in the coral/cm style so it
joins cleanly to `picarro_gas`, `field_metadata`, and `enigma.coral`.

Upsert key: `sdt_sample_name`.

## Columns

| Source (manifest) | Column | type | role / comment |
|---|---|---|---|
| `Sample ID` (normalized) | `sdt_sample_name` | STRING | **PK + FK** → enigma.coral.sdt_sample.sdt_sample_name; normalized CORAL ID `YYYYMMDD-WELL-ZONE-ASSAY`, validated `^[A-Z0-9-]+$` |
| `Sample ID` (raw) | `source_sample_id` | STRING | verbatim manifest ID, for traceability |
| `Timepoint` | `timepoint` | INT | campaign timepoint 1–36 |
| `Date` | `sample_date` | STRING | `YYYYMMDD` |
| `Well` | `sdt_location_name` | STRING | FK → enigma.coral.sdt_location; `SSO-<well>`; EFPW verbatim |
| `Well` | `location` | STRING | port string `U1-SZ1` |
| `Well` | `zone` | STRING | `SZ1`/`SZ2`; empty for EFPW |
| `Assay` | `assay` | STRING | raw manifest assay label (e.g. `Anions`, `NitrateIso`) |
| `Assay` (uppercased) | `assay_token` | STRING | token used in the ID (`ANIONS`, `NITRATEISO`) |
| `Storage Condition` | `storage_condition` | STRING | e.g. `4C, acidified`, `-80C` |
| `Volume` | `sample_volume` | STRING | as recorded (`30 mL`, `5 L`) — registry attribute, not a measurement |
| `Container` | `container` | STRING | e.g. `30 mL VOA vial`, `Restek Bags`, `15 mL falcon` |
| `Responsible Person` | `responsible_person` | STRING | e.g. `L. Zeng` |
| `PI` | `pi` | STRING | e.g. `Chakraborty` |
| `Ship Date` | `ship_date` | STRING | `YYYYMMDD` or empty |
| `Tracking #` | `tracking_number` | STRING | shipment tracking, or empty |
| `Notes` | `notes` | STRING | free text (in-field pH appears here for pH rows) |
| — | `provenance` / `source_file` / `ingest_run_id` / `ingested_at` | | bookkeeping |

## ID normalization (enforced on ingest; see NAMING.md)

- Manifest IDs are already date-first (`20261006-U1-SZ1-Anions`); only the
  **assay token is uppercased** → `20261006-U1-SZ1-ANIONS` (decision A: faithful
  uppercase).
- Validate every `sdt_sample_name` against `^[A-Z0-9-]+$` after uppercasing;
  **hold + report** any ID with an illegal char (underscore, space, period, …),
  never silently rewrite. Check uniqueness within the batch.
- `source_sample_id` keeps the raw manifest string for audit.

## Notes

- `sample_volume` and `container` are registry attributes (planned per-assay
  volume / container), not measured quantities → plain STRING, matching CORAL's
  free-text handling of container (there is no `container` COMO microtype).
- No assay **results** are modeled yet (none exist). A result file lands as its
  own table (or tables) keyed by `sdt_sample_name`.
- Open: confirm `EFPW02`/`EFPW03` exist as `sdt_location` in live coral, else
  stage additions (shared with field_metadata/picarro_gas).
