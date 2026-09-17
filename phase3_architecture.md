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
- **Files stand in for connectors**: the operational sources are
  databases, so a real deployment would replicate them through a managed
  CDC connector rather than receiving files at all. The file drop is a
  simulation device that keeps the five load behaviours reproducible in
  one repository; see §4.1 for what that substitutes for and what it
  leaves unchanged.
- **[NOTED, agreed]** In a real deployment this project would use an
  external ADLS Gen2 account + UC external location/storage credential
  instead of a managed volume. Called out as a deliberate, documented
  deviation for this learning environment, not an oversight.

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

LAKEFLOW JOBS: one main Job triggers the one main Pipeline per Load
(landing → Bronze → Silver → Gold), simulating that Load's arrival ---
see §5.2.

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
| Lakebase | Postgres-compatible, low-latency operational store --- **[NOTED, agreed]** used later to serve a synced subset of Gold data (e.g. current patient snapshot) to a Databricks App with OLTP-style access patterns Delta/SQL Warehouse isn't built for |
| Databricks Apps | Hosts internal-facing applications (Patient 360 viewer, operations assistant UI) directly on governed data, without a separate app-hosting platform |

**[NOTED, agreed]** Lakebase, Vector Search, Model Serving, and Databricks
Apps are all named in README §16 as *future* phases (ML/Agentic Layer).
They're included here in the service map for completeness/relationships,
but Phase 3--4 work (Bronze/Silver/Gold + DAB deployment) does not depend
on them --- they become relevant starting Phase 6.

------------------------------------------------------------------------

# 3. Unity Catalog Structure

**[CONFIRMED]** one catalog per environment (matching the Dev/Test/Prod
promotion model in README §14), one schema per medallion layer within it.

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
continuously running stream.

## 4.1 What is simulated, and what is not

The files are produced by `tools/generate_source_data.py`, which writes
them with pandas from the driver. That generator is a stand-in for the
operational applications; it is not an ingestion component and nothing in
the pipeline depends on it.

In a real deployment MediCore's sources are operational databases, and
ingestion would follow the source type rather than the file drop (see
README §8):

| Source | Real mechanism |
|---|---|
| Patient management, encounters, laboratory, pharmacy, claims | Lakeflow Connect database connector with its ingestion gateway, replicating changes continuously via CDC |
| An ERP-style source such as SAP, were one in scope | A connector that understands the source, or an external service such as Azure Data Factory landing changes |
| A genuine file feed, e.g. a partner lab or payer remittance | Auto Loader, exactly as used here |

The substitution is deliberate and contained. A CDC feed and a file drop
deliver the same *shape* of change -- inserts, updates, late arrivals,
corrections -- so the Silver and Gold designs in sections 5 and 6 are
unaffected by which one is upstream. What would change is only the
Bronze entry point: a CDC connector supplies change metadata
(operation type, commit sequence) that the file simulation has to convey
through the record's own timestamps instead.

Bronze therefore treats `_source_file` as provenance only. Anything
keyed on file arrival would have to be reworked when a real connector
replaced the simulation; anything keyed on business timestamps and keys
would not.

------------------------------------------------------------------------

# 5. Per-Entity Layer Design

Built directly from the confirmed contracts in
`phase2_source_understanding.md` §3, applying the decision framework in
README §12.

| Entity | Bronze ingestion | Silver processing | Gold treatment |
|---|---|---|---|
| `patients` | Auto Loader, `patients.csv`, schema evolution on | `APPLY CHANGES INTO` (SCD2) on `patient_id` **plus** the identity-resolution/MDM step described below | `dim_patient`, SCD Type 2, keyed by the resolved network-wide patient identity |
| `providers` | Auto Loader, `providers.json` | `APPLY CHANGES INTO` (SCD2 --- **[CONFIRMED]**, specialty/credential history has analytical value for Provider Performance) | `dim_provider`, SCD Type 2 |
| `facilities` | Auto Loader, `facilities.json` | `MERGE`/upsert on `facility_id`; low volume, near-static | `dim_facility`, SCD Type 1 (current state only --- **[CONFIRMED]**, facility identity rarely needs historical tracking) |
| `encounters` | Auto Loader, `encounters.json` | `MERGE` on `encounter_id` handling status transitions; dedup on late-arriving/duplicate records (Load 5) using event time | `fact_encounter`, incremental append/merge, FKs to `dim_patient`/`dim_provider`/`dim_facility`/`dim_date` |
| `lab_results` | Auto Loader, `lab_results.parquet` | Append + **[CONFIRMED]** SCD Type 2 versioning on correction: a corrected result inserts a new row (`effective_from`/`effective_to` or `is_current` flag) rather than overwriting, so the original and the correction are both preserved for audit | `fact_lab_result`, SCD2, FK to `fact_encounter` (or directly to `dim_patient`/`dim_provider`/`dim_facility` via the encounter); consumers filter to `is_current = true` unless doing a point-in-time/audit query |
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
**[CONFIRMED --- fuzzy matching]** staged, three-outcome matching design:

1. Silver `patients` retains the per-facility record as-is (source of
   truth per facility).
2. A separate Silver table, `patient_identity_xref`
   (`facility_id, patient_id → network_patient_id, match_method,
   match_score, matched_at`), holds the matching logic output rather than
   baking identity resolution into `dim_patient` directly.
3. **Matching logic**, staged by difficulty:
   - **Exact/deterministic** (covers Load 2's clean duplicate): normalized
     name + DOB + phone/email match exactly → auto-match.
   - **Blocked fuzzy match** (covers Load 4's mismatched-demographics
     case): candidate pairs are first narrowed via blocking (same DOB +
     soundex/metaphone of last name, to avoid all-pairs comparison), then
     scored with a weighted similarity function --- Jaro-Winkler on name,
     exact/normalized compare on DOB, phone, email. A threshold splits
     results into three outcomes rather than forcing a binary call:
     **auto-match**, **auto-reject**, and **needs manual review**
     (borderline scores land in a `patient_identity_review_queue` table
     rather than being silently merged or silently kept separate).
   - **[CONFIRMED --- future enhancement]** Matching is hand-rolled for
     now (exact-match + blocked fuzzy scoring above). Adopting
     [Zingg](https://github.com/zinggAI/zingg) --- an open-source
     entity-resolution library that runs natively on Spark, purpose-built
     for this kind of matching --- is a planned future upgrade once the
     hand-rolled approach's limits are better understood; it would
     replace the scoring step in `patient_identity_xref` generation
     without changing the surrounding architecture. Mentioned in
     `README.md` section 9.
4. `dim_patient` in Gold is built from `patients` joined through
   `patient_identity_xref` (auto-matched + manually-confirmed rows only),
   collapsing per-facility records into one SCD2 dimension row per
   `network_patient_id`.
5. Load 5's late correction to an already-resolved match is handled by
   re-running the matching step for affected records and updating the
   xref table --- this is why `patient_identity_xref` is a separate,
   revisable table rather than a one-time transform.

This keeps the matching logic auditable and separate from the dimensional
model itself. Exact matching thresholds/weights are a Phase 4
implementation detail, not an architecture decision.

## 5.2 Pipeline and Job Design --- **[CONFIRMED]**

- **One Lakeflow Declarative Pipeline** contains the full DAG: all 7
  entities' Bronze→Silver flows, `patient_identity_xref`, and all
  Silver→Gold flows (dims + facts). Pipelines are designed to be
  multi-table DAGs with automatic dependency resolution and shared
  compute --- splitting per-entity would fragment lineage and add
  operational overhead without benefit at this project's scale.
- **One Lakeflow Job** triggers that Pipeline per Load, structured as:
  1. *(optional pre-check task)* verify the expected Load N files exist
     under `landing.source_files.<entity>/load_N/` before triggering.
  2. Run/update the main Pipeline.
  3. *(optional post task)* e.g. refresh an AI/BI dashboard or send a
     completion notification --- not required for Phase 3--4, but the Job
     structure leaves room for it.
- Future ML/agentic-layer work (README §16) gets its **own** job(s) later
  --- this one Job's scope stays limited to the Bronze→Gold data pipeline.

------------------------------------------------------------------------

# 6. PHI/PII Protection

**[CONFIRMED --- control-table-driven]** rather than hardcoding masking
rules per column, a single control table drives policy for every PHI/PII
column across the project.

## 6.1 Control table

`<catalog>.governance.pii_column_policy` (one per environment catalog,
same catalog-per-env pattern as everything else):

| Column | Purpose |
|---|---|
| `entity`, `schema_name`, `table_name`, `column_name` | Identifies the exact column being governed |
| `classification` | `PHI` \| `PII` \| `SENSITIVE` \| `NONE` |
| `technique` | `MASK` \| `HASH` \| `TOKENIZE` \| `ENCRYPT` \| `GENERALIZE` \| `NONE` |
| `visible_to_groups` | `array<string>` --- UC groups allowed to see the *unprotected* value |
| `reversible` | `boolean` --- true only for `ENCRYPT`; false for hash/tokenize (one-way) |
| `key_scope` | Databricks secret scope name holding the encryption key, when `reversible = true` |
| `notes` | Free text --- rationale, e.g. "needed for claims appeal process" |

This table is the single source of truth for "what happens to this
column and who can see it unprotected" --- new columns get a policy row
before they're exposed past Bronze, rather than protection logic being
scattered across transform code.

## 6.2 How it's enforced

- At deployment (via DAB), the control table is read and used to
  generate/attach Unity Catalog **column masks** to each governed Silver
  and Gold column. A mask function checks the caller's group membership
  (`is_account_group_member()`) against `visible_to_groups` for that
  column and returns either the real value or the protected form.
- **Masking / Generalization**: mask function returns a redacted/reduced
  form (e.g. `******3210`, birth year only) for anyone not in
  `visible_to_groups`.
- **Hashing / Tokenization**: one-way; the protected form is the only
  form stored past Silver, so there's nothing to reverse regardless of
  group membership --- used when downstream processing only needs a
  stable join key (README §11's `P10001 → PAT_7F91A2` example), not the
  original value.
- **Encryption (reversible)**: value is stored via `aes_encrypt()` using
  a key held in a **Databricks-native secret scope** (not Azure Key
  Vault-backed, consistent with §1's no-external-Azure-resources
  constraint). The mask function calls `aes_decrypt()` only for callers
  in `visible_to_groups`; everyone else gets the ciphertext or a masked
  placeholder.

## 6.3 Groups (UC account-level groups, one per persona cluster from
`phase1_business_understanding.md` §1) --- **[CONFIRMED]**:

| Group | Roughly corresponds to persona(s) |
|---|---|
| `grp_clinical_care` | Care Coordinator/Clinician, Clinical Operations Lead |
| `grp_lab_ops` | Laboratory Operations Manager |
| `grp_pharmacy_ops` | Pharmacy Manager |
| `grp_billing_finance` | Revenue Cycle/Billing Manager |
| `grp_facility_admin` | Facility Administrator |
| `grp_compliance_governance` | Data Governance/Compliance Officer --- typically the only group with broad `visible_to_groups` access across entities |
| `grp_data_engineering` | Pipeline/platform builders --- Bronze/Silver access as needed for transforms, not a blanket PHI exemption |
| `grp_platform_ml` | Platform/Analytics Consumer --- Gold-layer access only, per README §16's "governed data products, not raw PHI" |

------------------------------------------------------------------------

# 7. Open Items Before Phase 4 (Implementation)

**[DEFERRED, by design]** The `pii_column_policy` control table's actual
contents (real column-by-column classification across all 7 entities) are
intentionally *not* filled in here. They'll be identified once Load 1's
raw files are landed and handled, against the real column names, rather
than guessed at the architecture stage. This is Phase 4 work, done right
after Bronze ingestion of Load 1.

All other architecture-level items are resolved --- see below.

**Resolved:**
- Unity Catalog structure --- catalog-per-environment, schema-per-layer
  (§3).
- SCD choices --- `dim_provider` SCD2, `dim_facility` SCD1 (§5).
- `lab_results` correction handling --- SCD Type 2 versioning; a
  correction inserts a new row rather than overwriting, preserving the
  original for audit (§5).
- MDM matching approach --- staged exact-match then blocked fuzzy
  matching (Jaro-Winkler + blocking), three-way outcome
  (auto-match/auto-reject/manual-review), hand-rolled for now; Zingg
  confirmed as a planned future upgrade, mentioned in `README.md`
  section 9 (§5.1).
- PHI/PII mechanism --- control-table-driven (`pii_column_policy`)
  rather than hardcoded per-column logic, covering mask/hash/
  tokenize/encrypt/generalize with group-gated, DAB-generated UC column
  masks; reversible encryption uses Databricks-native secret scopes, not
  Azure Key Vault (§6).
- UC groups --- `grp_clinical_care`, `grp_lab_ops`, `grp_pharmacy_ops`,
  `grp_billing_finance`, `grp_facility_admin`,
  `grp_compliance_governance`, `grp_data_engineering`,
  `grp_platform_ml` (§6.3).
- Lakeflow Job granularity --- one Pipeline (full DAG, all entities),
  one Job triggering it per Load (§5.2).
