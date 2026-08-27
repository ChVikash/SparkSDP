# MediCore Health Network --- Healthcare Lakehouse

## 1. Project Overview

MediCore Health Network is a multi-facility healthcare organization
operating hospitals, specialty clinics, and diagnostic facilities.

The organization has multiple operational applications that continuously
generate healthcare data across patient management, clinical encounters,
laboratory services, prescriptions, and claims.

This project simulates that environment and builds an end-to-end
healthcare data platform on Databricks.

The project is intentionally designed from a **business-first
perspective**:

``` text
Business Outcomes
        ↓
Business Questions
        ↓
Data Products
        ↓
Source Systems
        ↓
Source Data Characteristics
        ↓
Architecture
        ↓
Databricks Implementation
        ↓
Analytics / ML / Agentic Applications
```

Databricks is the selected implementation platform because of its
unified data engineering, analytics, ML and AI capabilities, together
with open/interoperable technologies such as Apache Spark, Delta Lake
and open data formats.

The objective is **not** to demonstrate every Databricks feature.
Instead, the project should demonstrate engineering judgment: choosing
the appropriate modern Databricks/Lakeflow capability based on the
business and data characteristics.

------------------------------------------------------------------------

# 2. Business Scenario

MediCore Health Network operates multiple healthcare facilities:

-   City Care Hospital --- Delhi
-   Metro Health Hospital --- Noida
-   MediCore Diagnostics --- Ghaziabad
-   MediCore Specialty Clinic --- Gurgaon

Operational applications are continuously used by patients, providers,
clinical staff, laboratory teams, administrative teams, pharmacy teams
and billing/claims teams.

These applications generate data such as:

-   Patient registrations and demographic changes
-   Provider and facility information
-   Patient encounters
-   Laboratory results
-   Prescriptions
-   Insurance claims

In the real world, these applications would continuously generate events
and/or source-system changes.

For this learning project, we simulate those changes through successive
file deliveries:

``` text
Load 1 → Load 2 → Load 3 → Load 4 → Load 5
```

The terms Day1, Day2, etc. therefore represent **successive loads**, not
calendar dates.

------------------------------------------------------------------------

# 3. Business Outcomes

The platform is intended to support the following business outcomes.

## 3.1 Patient 360

Provide a trusted, governed view of a patient's healthcare activity
across the healthcare network.

A patient view should eventually bring together:

-   Demographics
-   Facilities visited
-   Encounters
-   Providers
-   Diagnoses
-   Laboratory results
-   Prescriptions
-   Claims

## 3.2 Clinical and Operational Intelligence

Enable healthcare management and operational teams to understand:

-   Patient volumes
-   Facility utilization
-   Provider workload
-   Specialty performance
-   Encounter trends
-   Laboratory activity
-   Abnormal laboratory-result trends
-   Prescription patterns

## 3.3 Claims and Revenue Intelligence

Enable analysis of:

-   Claim volumes
-   Approval and denial rates
-   Claim values
-   Claim processing times
-   Denial reasons
-   Facility-level claims performance

## 3.4 Trusted and Governed Healthcare Data

Establish a data platform with:

-   Data-quality controls
-   Data lineage
-   PII/PHI protection
-   Access controls
-   Auditability
-   Reproducible processing
-   Reliable incremental processing

## 3.5 Foundation for ML and Agentic Applications

The governed lakehouse should eventually support:

-   Machine-learning use cases
-   Healthcare analytics
-   Patient 360 experiences
-   Internal healthcare operations assistants
-   Agentic applications operating over governed healthcare data

The AI/agentic layer is a later phase. The lakehouse is the data
foundation that makes those capabilities possible.

------------------------------------------------------------------------

# 4. Project Phases

## Phase 1 --- Business Understanding

Start with the organization and its business objectives rather than the
technology.

### Activities

-   Define business outcomes
-   Identify business users/personas
-   Define important business questions
-   Identify required data products
-   Identify analytical and operational use cases
-   Define future ML/AI/agentic opportunities

### Output

A set of business requirements and data-product requirements that can
drive the rest of the architecture.

------------------------------------------------------------------------

## Phase 2 --- Source Understanding

Understand how the operational world actually generates data.

### Operational applications

The simulated source environment includes applications for:

-   Patient management
-   Clinical/encounter management
-   Laboratory services
-   Prescription management
-   Billing and claims

### Initial source entities

The project currently proposes seven core source entities:

``` text
patients
providers
facilities
encounters
lab_results
prescriptions
claims
```

### Activities

For each source:

-   Understand the business meaning
-   Identify business keys
-   Identify relationships
-   Identify update patterns
-   Identify append-only/event characteristics
-   Identify source-system timestamps
-   Identify ingestion characteristics
-   Identify PII/PHI
-   Identify potential data-quality problems
-   Identify schema-evolution possibilities

### Output

A documented source-data contract for each entity.

------------------------------------------------------------------------

# 5. Simulated Source Loads

The source system is conceptually continuous.

The project simulates that continuous operation through five successive
loads.

## Load 1 --- Baseline

Initial population of the healthcare network.

Expected behavior:

-   Initial patients
-   Initial providers
-   Initial facilities
-   Initial encounters
-   Initial lab results
-   Initial prescriptions
-   Initial claims

The baseline should be relatively clean.

------------------------------------------------------------------------

## Load 2 --- Normal Incremental Activity

The operational systems continue changing.

Examples:

-   New patients
-   New encounters
-   New lab results
-   New prescriptions
-   New claims
-   Patient demographic updates
-   Provider changes
-   Claim-status changes

This load introduces the first meaningful decisions around:

-   Append
-   Upsert
-   CDC
-   SCD

------------------------------------------------------------------------

## Load 3 --- Source and Business Evolution

The source systems evolve.

Examples:

-   New source column
-   Additional patient attributes
-   Business-level updates
-   Corrected laboratory information
-   Additional facility/provider activity

This load allows the project to demonstrate the distinction between:

``` text
Schema evolution
        vs.
Data evolution
```

------------------------------------------------------------------------

## Load 4 --- Data Quality Degradation

The source begins producing imperfect data.

Examples:

-   Duplicate records
-   Missing patient identifiers
-   Invalid categorical values
-   Negative claim amounts
-   Malformed email addresses
-   Invalid provider references
-   Invalid claim statuses

This load is used to demonstrate appropriate data-quality handling,
including expectations and quarantine/rejection strategies where
justified.

------------------------------------------------------------------------

## Load 5 --- Production-Like Messiness

The source now contains more realistic operational complications.

Examples:

-   Late-arriving encounters
-   Late-arriving laboratory results
-   Duplicate late-arriving records
-   Corrected lab results
-   Updated claims
-   Patient demographic corrections

A key scenario is:

``` text
Arrival / Load Date
        ≠
Business / Event Date
```

This allows us to reason about:

-   Event time
-   Ingestion time
-   Late-arriving data
-   Idempotency
-   Deduplication
-   Business keys
-   Corrections
-   Incremental processing

------------------------------------------------------------------------

# 6. Source Data Formats

The project will intentionally use multiple source formats:

``` text
patients.csv
providers.json
facilities.json
encounters.json
lab_results.parquet
prescriptions.csv
claims.json
```

Format diversity is included to simulate heterogeneous operational
sources and exercise ingestion/schema-handling capabilities.

It is not intended as feature usage for its own sake.

------------------------------------------------------------------------

# 7. Target Lakehouse Architecture

The target architecture follows the medallion pattern.

``` text
                 OPERATIONAL APPLICATIONS
                          │
                          ▼
                  SOURCE FILE DELIVERY
                  Load 1 → Load 5
                          │
                          ▼
                 ┌──────────────────┐
                 │      BRONZE      │
                 │ Raw / auditable  │
                 │ source data      │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │      SILVER      │
                 │ Cleaned          │
                 │ Standardized     │
                 │ Validated        │
                 │ Deduplicated     │
                 │ Protected        │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │       GOLD       │
                 │ Dimensional      │
                 │ model            │
                 │ Facts            │
                 │ Dimensions       │
                 │ Data products    │
                 └────────┬─────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
        BI / Analytics          ML / Agentic AI
```

------------------------------------------------------------------------

# 8. Bronze Layer

Bronze represents the raw, auditable representation of source data.

The objective is to preserve source information and ingestion context
rather than performing significant business transformations.

Expected technical metadata will include concepts such as:

``` text
_source_file
_source_file_path
_source_file_name
_source_system
_ingestion_timestamp
_load_id
_record_hash
```

These fields will help us reason about:

-   Lineage
-   Replayability
-   Duplicate detection
-   Late-arriving data
-   Source provenance
-   Load-level debugging

Auto Loader is the planned ingestion mechanism for file arrival.

------------------------------------------------------------------------

# 9. Silver Layer

Silver represents trusted, standardized and usable operational data.

Typical responsibilities:

-   Schema normalization
-   Data-type conversion
-   Standardization
-   Data-quality validation
-   Deduplication
-   Referential-integrity checks
-   Business-rule validation
-   Incremental processing
-   Change handling
-   PHI/PII protection
-   Enrichment where justified

The exact Lakeflow capability used for each dataset will be determined
from its source characteristics.

The project should explicitly avoid forcing every dataset through the
same processing pattern.

------------------------------------------------------------------------

# 10. Gold Layer

Gold will contain business-oriented analytical data products.

The project will use dimensional modeling where appropriate.

Initial dimensional model:

``` text
dim_patient
dim_provider
dim_facility
dim_date

fact_encounter
fact_lab_result
fact_prescription
fact_claim
```

Potential analytical data products include:

``` text
Patient 360
Facility Performance
Provider Performance
Clinical Activity
Laboratory Analytics
Claims Analytics
```

The Gold layer will demonstrate:

-   Business keys vs surrogate keys
-   Fact vs dimension design
-   SCD Type 1/Type 2 where justified
-   Historical state
-   Conformed dimensions
-   Analytical aggregates where useful

------------------------------------------------------------------------

# 11. Privacy, Security and Governance

Healthcare data contains sensitive PII/PHI.

Privacy and governance are therefore cross-cutting architectural
requirements.

Potential sensitive attributes include:

-   Patient name
-   Date of birth
-   Phone
-   Email
-   Address
-   Insurance identifiers
-   Patient identifiers
-   Clinical information
-   Laboratory results
-   Claims information

The project will consider appropriate techniques such as:

### Masking

Example:

``` text
9876543210
      ↓
******3210
```

### Hashing

Used where the original value does not need to be recovered.

### Tokenization / Pseudonymization

Example:

``` text
P10001
  ↓
PAT_7F91A2
```

This allows consistent joins while reducing exposure of the original
identifier.

### Generalization

For example, using year of birth rather than the full date where the
business use case permits.

### Encryption

Encryption requirements will be considered for data at rest/in transit
and for secrets/credentials, with implementation choices based on the
actual platform and deployment architecture.

### Governance

Unity Catalog will be used as the governance foundation for:

-   Access control
-   Data discovery
-   Permissions
-   Lineage
-   Auditing
-   Governed consumption

Sensitive data should not simply be exposed because it exists in Bronze.

------------------------------------------------------------------------

# 12. Modern Lakeflow Strategy

The project will use modern Lakeflow capabilities based on **why a
capability is appropriate for a particular data problem**.

We will not attempt to use every available feature.

Examples of the decision framework:

``` text
Append-only/event data
        ↓
Append-oriented incremental processing

Changing source records
        ↓
Appropriate CDC/upsert capability

Historical dimension requirements
        ↓
SCD Type 2 capability

Data-quality requirements
        ↓
Expectations

Incremental file arrival
        ↓
Auto Loader

Declarative transformation requirements
        ↓
Lakeflow Declarative Pipelines
```

The exact mapping will be finalized after the source-data contract is
defined.

The goal is to demonstrate:

> **Knowing when to use what, rather than knowing how to use
> everything.**

------------------------------------------------------------------------

# 13. Data Modeling Strategy

Gold will be designed from business questions rather than from the
Silver schema.

For example:

``` text
Business Question:
Which facilities have increasing outpatient demand?

Required data:
Encounter + Patient + Facility + Date

          ↓

Gold model:
fact_encounter
dim_patient
dim_facility
dim_date
```

Similarly:

``` text
Business Question:
What is the claim denial rate by facility?

Required data:
Claim + Facility + Date

          ↓

Gold model:
fact_claim
dim_facility
dim_date
```

This keeps the data model aligned with actual business outcomes.

------------------------------------------------------------------------

# 14. DevOps and Deployment

Databricks Asset Bundles (DABs) will be the DevOps/deployment mechanism.

The project will be source-controlled and designed around environment
promotion.

Conceptually:

``` text
Git
 │
 ▼
DAB
 │
 ├── Dev
 ├── Test
 └── Prod
       │
       ▼
Databricks Resources
       │
       ├── Lakeflow Pipelines
       ├── Jobs
       ├── Notebooks / Source
       ├── Configuration
       └── Permissions
```

The goal is to treat the Databricks implementation as a software project
rather than a collection of manually configured notebooks.

------------------------------------------------------------------------

# 15. Engineering Excellence

The project will eventually cover:

-   Git-based source control
-   DAB-based deployment
-   Environment separation
-   Automated validation
-   Data-quality testing
-   Pipeline monitoring
-   Operational observability
-   Error handling
-   Lineage
-   Governance
-   Reproducibility
-   Idempotent processing

These capabilities will be introduced where they solve actual
engineering problems.

------------------------------------------------------------------------

# 16. Future ML and Agentic Layer

The lakehouse is intentionally designed to support future intelligent
applications.

The eventual architecture could evolve toward:

``` text
                 Healthcare Lakehouse
                         │
                         ▼
                Governed Gold Layer
                         │
                  Semantic / Serving
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
          Analytics              AI / ML
                                     │
                                     ▼
                               Agentic Layer
```

Potential future agentic use cases:

-   Patient activity summarization
-   Healthcare operations assistant
-   Facility performance analysis
-   Claims investigation assistant
-   Provider performance assistant
-   Natural-language exploration of governed healthcare data

The agent should operate against appropriately governed data products
rather than unrestricted raw PHI.

------------------------------------------------------------------------

# 17. Architecture Decision Principle

The central principle of this project is:

``` text
Business Requirement
        ↓
Data Requirement
        ↓
Source Characteristic
        ↓
Architecture Decision
        ↓
Databricks Capability
```

Not:

``` text
Databricks Feature
        ↓
Find a reason to use it
```

This principle will guide all subsequent design decisions.

------------------------------------------------------------------------

# 18. Project Roadmap

``` text
Phase 1 — Business Understanding
    ↓
Phase 2 — Source Understanding
    ↓
Phase 3 — Architecture
    ↓
Phase 4 — Implementation
    ↓
Phase 5 — Engineering Excellence
    ↓
Phase 6 — Analytics / AI
```

### Current status

**Phase 1 --- Business Understanding**

Business scenario and high-level outcomes are established.

### Next milestone

Define:

1.  Business personas
2.  Business questions
3.  Data products
4.  Source applications
5.  Source-system responsibilities
6.  Source entity contracts
7.  Relationships between entities

Only after those are established will the exact source files for Load
1--5 be generated.

------------------------------------------------------------------------

# 19. Project Philosophy

This project is intended to demonstrate **end-to-end data engineering
judgment**, not simply Databricks syntax.

The desired outcome is that every major implementation decision can be
explained in business and architectural terms:

> Why is this data in Bronze?

> Why is this transformation in Silver?

> Why is this table modeled this way in Gold?

> Why is this dataset append-only?

> Why does this one require CDC?

> Why is this dimension SCD2?

> Why should this data be masked rather than hashed?

> Why does this data require restricted access?

> Why are we using this Lakeflow capability here?

> Why is this deployed through DABs?

If those questions can be answered clearly, the project will demonstrate
much more than the ability to build a Spark pipeline.

It will demonstrate the ability to **design and operate a modern
healthcare data platform**.
