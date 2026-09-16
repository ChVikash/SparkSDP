# MediCore Health Network --- Phase 3: Architecture

This document turns the medallion sketch (`README.md` §7), the Lakeflow
decision framework (§12), and the confirmed Phase 2 source-data contracts
(`phase2_source_understanding.md`) into a concrete architecture: what
Databricks services are used, how they relate to each other, how source
files are landed and simulated, and how each entity is treated at each
layer.

> **Note on assumptions:** environment constraints below are as you
> described them. Everything past the "Environment & Storage" section is
> a first-pass design grounded in those constraints and the confirmed
> Phase 2 decisions, flagged **[ASSUMPTION]** where it goes beyond what's
> been explicitly discussed. Please correct/override before this is
> treated as final.

------------------------------------------------------------------------

# 1. Environment & Storage Constraints

- **Platform**: Azure Databricks workspace only. No other Azure resources
  (Storage Accounts, ADLS Gen2, Key Vault, etc.) are assumed available,
  since there is no active Azure subscription backing this project beyond
  the Databricks workspace itself.
- **Consequence**: no external cloud storage, no Unity Catalog *external
  locations*, no storage credentials. All storage is
  **Databricks-managed**: managed Unity Catalog volumes and managed Delta
  tables, backed by the workspace/metastore's own storage rather than a
  customer-owned ADLS Gen2 container.
- **Source-file landing**: instead of operational applications writing to
  an external storage account, source files (`patients.csv`,
  `providers.json`, ... per README §6) are landed directly into a
  **Unity Catalog managed Volume**, which Auto Loader then reads
  incrementally --- Auto Loader supports Volume paths the same way it
  supports cloud storage paths, so this substitution doesn't change the
  ingestion pattern, only where the bytes physically live.
- **[ASSUMPTION]** In a real deployment this project would use an
  external ADLS Gen2 account + UC external location/storage credential
  instead of a managed volume. That's called out here as a deliberate,
  documented deviation for this learning environment, not an oversight.

------------------------------------------------------------------------

# 2. Databricks Service Map

Unity Catalog is the spine: every other service reads/writes through it,
and it's what makes lineage, access control, and auditing span the whole
stack (tying back to README §11 Governance).

```text
                         UNITY CATALOG
        (catalogs, schemas, volumes, tables, access control,
                    lineage, audit, masking)
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   Managed Volume        Managed Delta         Governed access
   (landing zone)          Tables            for every layer below
        │                     │
        ▼                     │
   AUTO LOADER  ──────────────┤  (incremental file → Bronze)
        │                     │
        ▼                     │
   BRONZE (Delta) ────────────┤
        │                     │
        ▼                     │
 LAKEFLOW DECLARATIVE         │  (Bronze→Silver→Gold transforms,
   PIPELINES  ────────────────┤   expectations, CDC/APPLY CHANGES,
        │                     │   dedup, MDM matching)
        ▼                     │
   SILVER (Delta) ────────────┤
        │                     │
        ▼                     │
   GOLD (Delta) ───────────────┘
        │
        ├──────────────┬──────────────┬───────────────┬──────────────┐
        ▼              ▼              ▼                ▼              ▼
  SQL WAREHOUSE   LAKEBASE       VECTOR SEARCH    MODEL SERVING   MLFLOW
  (BI / AI-BI /   (low-latency    (embeddings for   (LLM/ML        (experiment
   Genie NL       operational     agentic RAG,       endpoints for  tracking,
   queries)       serving for     e.g. Patient       agentic apps)  model
                  Databricks      360 assistant)                    registry)
                  Apps)
        │              │
        └──────┬───────┘
               ▼
       DATABRICKS APPS
   (Patient 360 / ops-assistant
         UI, internal tools)

LAKEFLOW JOBS orchestrate/schedule the whole vertical chain
(landing → Bronze → Silver → Gold), and simulate each Load's arrival.

DATABRICKS ASSET BUNDLES (DABs) deploy all of the above --- catalogs,
volumes, pipelines, jobs, permissions --- across Dev/Test/Prod
(README §14).
```

## 2.1 Service responsibilities

| Service | Role in this project |
|---|---|
| Unity Catalog | Governance spine: catalogs/schemas/volumes/tables, access control, column masking for PHI, lineage, audit logging |
| Managed Volume | Landing zone simulating source-file delivery (replaces ADLS Gen2 in this constrained environment) |
| Auto Loader | Incremental, schema-evolution-aware ingestion from the landing Volume into Bronze |
| Lakeflow Declarative Pipelines | Declarative Bronze→Silver→Gold transforms; expectations for data-quality; `APPLY CHANGES INTO` for CDC/upsert entities |
| Lakeflow Jobs | Orchestrates pipeline runs; simulates Load 1--5 arrival by triggering ingestion after each load's files are placed in the Volume |
| Delta Lake | Table format underlying every layer --- ACID, time travel, schema evolution, `MERGE`/`APPLY CHANGES` support |
| Databricks SQL Warehouse | Serves Gold tables to BI tools, AI/BI dashboards, and Genie natural-language queries (README §16 "Natural-language exploration") |
| MLflow | Experiment tracking and model registry --- future ML use cases (README §16) |
| Model Serving | Hosts ML models and/or LLM endpoints for the future agentic layer |
| Vector Search | Indexes governed Gold-layer text/embeddings for RAG --- future agentic use cases (patient summarization, ops assistant) |
| Lakebase | Postgres-compatible, low-latency operational store --- **[ASSUMPTION]** used later to serve a synced subset of Gold data (e.g. current patient snapshot) to a Databricks App with OLTP-style access patterns Delta/SQL Warehouse isn't built for |
| Databricks Apps | Hosts internal-facing applications (Patient 360 viewer, operations assistant UI) directly on governed data, without a separate app-hosting platform |

**[ASSUMPTION]** Lakebase, Vector Search, Model Serving, and Databricks
Apps are all named in README §16 as *future* phases (ML/Agentic Layer).
They're included here in the service map for completeness/relationships,
but Phase 3--4 work (Bronze/Silver/Gold + DAB deployment) does not depend
on them --- they become relevant starting Phase 6.

------------------------------------------------------------------------

# 3. Unity Catalog Structure

**[ASSUMPTION --- please confirm]** proposed structure: one catalog per
environment (matching the Dev/Test/Prod promotion model in README §14),
one schema per medallion layer within it.

```text
medicore_dev / medicore_test / medicore_prod      (catalog per environment)
│
├── landing        (schema)
│   └── source_files                              (managed Volume)
│       ├── patients/load_1/patients.csv ... load_5/...
│       ├── providers/load_1/providers.json ...
│       ├── facilities/load_1/facilities.json ...
│       ├── encounters/load_1/encounters.json ...
│       ├── lab_results/load_1/lab_results.parquet ...
│       ├── prescriptions/load_1/prescriptions.csv ...
│       └── claims/load_1/claims.json ...
│
├── bronze          (schema)
│   ├── patients, providers, facilities, encounters,
│   │   lab_results, prescriptions, claims
│   └── (raw + technical metadata columns per README §8)
│
├── silver          (schema)
│   ├── patients, providers, facilities, encounters,
│   │   lab_results, prescriptions, claims
│   └── patient_identity_xref     (MDM linkage table, see §5)
│
└── gold            (schema)
    ├── dim_patient, dim_provider, dim_facility, dim_date
    └── fact_encounter, fact_lab_result, fact_prescription, fact_claim
```

Rationale: catalog-per-environment keeps Dev/Test/Prod fully isolated
(separate permissions, separate data, no risk of a Dev pipeline touching
Prod data) while schema-per-layer keeps Bronze/Silver/Gold permissions
distinct within an environment --- e.g. only pipeline service principals
can write Bronze/Silver, while analysts get read access to Gold only.

The `source_files` Volume subfolder structure
(`<entity>/load_<n>/<file>`) is what simulates the "continuous source
system" from README §5: files are dropped into the next `load_n/` folder
to represent that load's delivery, and a Lakeflow Job run represents that
load being "processed."

------------------------------------------------------------------------

# 4. Load Simulation Mechanism

Since there's no real operational application generating events, Load
1--5 arrival (README §5) is simulated as:

1. Place that Load's files under `landing.source_files.<entity>/load_N/`
   in the managed Volume.
2. Trigger the Lakeflow Job for that load (manually for this learning
   project, rather than on a real schedule).
3. Auto Loader picks up the new files (it tracks already-processed files
   via its checkpoint, so only the newly-dropped Load N files are
   ingested --- this is what gives us incremental behavior without a real
   streaming source).
4. The Lakeflow Declarative Pipeline runs Bronze→Silver→Gold for the
   newly ingested Bronze rows.

This means "Load N" is a **file-drop + job-trigger event**, not a
continuously running stream --- appropriate for a learning project
simulating batch-oriented source systems (matches README §8's note that
"Auto Loader is the planned ingestion mechanism for file arrival").

------------------------------------------------------------------------

# 5. Per-Entity Layer Design

Built directly from the confirmed contracts in
`phase2_source_understanding.md` §3, applying the decision framework in
README §12.

| Entity | Bronze ingestion | Silver processing | Gold treatment |
|---|---|---|---|
| `patients` | Auto Loader, `patients.csv`, schema evolution on | `APPLY CHANGES INTO` (SCD2) on `patient_id` **plus** the identity-resolution/MDM step described below | `dim_patient`, SCD Type 2, keyed by the resolved network-wide patient identity |
| `providers` | Auto Loader, `providers.json` | `APPLY CHANGES INTO` (SCD1 or SCD2 --- **[ASSUMPTION]** SCD2, since specialty/credential history has analytical value for Provider Performance) | `dim_provider`, SCD Type 2 |
| `facilities` | Auto Loader, `facilities.json` | `MERGE`/upsert on `facility_id`; low volume, near-static | `dim_facility`, SCD Type 1 (current state only --- **[ASSUMPTION]**, since facility identity rarely needs historical tracking) |
| `encounters` | Auto Loader, `encounters.json` | `MERGE` on `encounter_id` handling status transitions; dedup on late-arriving/duplicate records (Load 5) using event time | `fact_encounter`, incremental append/merge, FKs to `dim_patient`/`dim_provider`/`dim_facility`/`dim_date` |
| `lab_results` | Auto Loader, `lab_results.parquet` | Append-only with correction handling: latest-value-wins via a sequencing column (result timestamp) when a corrected result arrives (Load 3/5) | `fact_lab_result`, append/merge, FK to `fact_encounter` (or directly to `dim_patient`/`dim_provider`/`dim_facility` via the encounter) |
| `prescriptions` | Auto Loader, `prescriptions.csv` | `MERGE` on `prescription_id` handling status changes (filled/cancelled, confirmed in Phase 2) | `fact_prescription`, incremental append/merge |
| `claims` | Auto Loader, `claims.json` | `APPLY CHANGES INTO` on `claim_id` --- the clearest CDC/upsert case (status lifecycle confirmed in Phase 2) | `fact_claim`, grain = one row per claim (1:N from `encounters`, confirmed in Phase 2) |

All Bronze tables carry the technical metadata columns from README §8
(`_source_file`, `_ingestion_timestamp`, `_load_id`, `_record_hash`,
etc.), and all Silver transforms apply Lakeflow **expectations** for the
data-quality rules anticipated in Phase 2 (missing identifiers, invalid
categorical values, negative claim amounts, malformed emails, invalid
provider/claim-status references), routing failures to quarantine rather
than silently dropping them (README §9).

## 5.1 Identity Resolution / MDM (patients)

Confirmed in Phase 2: `patient_id` is per-facility, not globally unique.
**[ASSUMPTION --- design not yet detailed]** proposed approach:

1. Silver `patients` retains the per-facility record as-is (source of
   truth per facility).
2. A separate Silver table, `patient_identity_xref`, holds the matching
   logic output: `(facility_id, patient_id) → network_patient_id`,
   produced by a deterministic/rules-based match (name + DOB + a
   normalized phone/email, or similar) for Load 2's clean-duplicate case,
   extendable to fuzzy matching for Load 4's mismatched-demographics
   case.
3. `dim_patient` in Gold is built from `patients` joined through
   `patient_identity_xref`, collapsing per-facility records into one
   SCD2 dimension row per `network_patient_id`.
4. Load 5's late correction to an already-resolved match is handled by
   re-running the matching step for affected records and updating the
   xref table --- this is why `patient_identity_xref` is a separate
   table rather than a one-time transform baked into `dim_patient`
   directly: it needs to be revisable.

This keeps the matching logic auditable and separate from the dimensional
model itself, and gives us a natural place to plug in a more
sophisticated MDM tool later without reshaping `dim_patient`.

------------------------------------------------------------------------

# 6. PHI/PII Protection

**[ASSUMPTION --- not yet discussed in detail]** mapped from README §11
onto Unity Catalog mechanisms:

| Technique | UC mechanism | Applied to |
|---|---|---|
| Masking | Column mask (SQL UDF via `ALTER TABLE ... SET MASK`) | Phone, partial SSN display for non-privileged roles |
| Hashing | Computed column at Silver | SSN/national ID, where original value isn't needed downstream |
| Tokenization | Computed column at Silver, deterministic token | `patient_id` exposed to lower-privilege consumers as `PAT_xxxxxx` (README §11 example) |
| Generalization | Computed column at Gold | DOB → birth year only, for roles that don't need exact DOB |
| Row/column-level access | Unity Catalog row filters + column masks, grants scoped by role | Restricting raw Bronze/Silver PHI to pipeline service principals and governance roles only; analysts get masked/tokenized Gold |

------------------------------------------------------------------------

# 7. Open Items Before Phase 4 (Implementation)

1. Confirm Unity Catalog structure in §3 (catalog-per-environment,
   schema-per-layer) --- or specify a different convention.
2. Confirm SCD choice for `dim_provider` (SCD2 proposed) and
   `dim_facility` (SCD1 proposed).
3. Confirm the MDM/identity-resolution matching approach in §5.1
   (deterministic rules vs. a specific fuzzy-matching technique) --- this
   is currently just a placeholder design.
4. Confirm the PHI/PII mechanism mapping in §6, and which roles/groups
   should exist in Unity Catalog for access control.
5. Confirm whether Lakeflow Jobs should be one job per entity, one job
   per load, or one job for the whole Bronze→Gold chain per load ---
   affects DAB job definitions in Phase 4.
