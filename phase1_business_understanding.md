# MediCore Health Network --- Phase 1: Business Understanding

This document completes the **Phase 1 --- Business Understanding** items
from the roadmap in `README.md` (section 18): business personas, business
questions, and data products. The business scenario and outcomes
themselves are already defined in `README.md` (sections 2--3); this doc
builds directly on those without repeating them.

Source-side Phase 2 content (source applications, entity relationships,
per-entity source-data contracts) lives in `phase2_source_understanding.md`.

> **Note on assumptions:** the base `README.md` defines the business
> scenario and outcomes, but does not spell out personas or specific
> questions. Those are drafted here as a reasonable first pass grounded in
> the business scenario, and are flagged as **[ASSUMPTION]** where they go
> beyond what `README.md` states directly. Please correct/override
> anything that doesn't match your intent before this is treated as final.

------------------------------------------------------------------------

# 1. Business Personas

| Persona | Role | Primary interest |
|---|---|---|
| Facility Administrator | Runs day-to-day operations at a hospital/clinic | Facility utilization, patient volumes |
| Clinical Operations Lead / CMO | Oversees clinical quality and staffing across the network | Provider workload, specialty performance, encounter trends |
| Care Coordinator / Clinician | Delivers direct patient care | Patient 360 view: history across facilities, encounters, labs, meds |
| Laboratory Operations Manager | Runs lab services | Lab volumes, turnaround time, abnormal-result trends |
| Pharmacy Manager | Runs prescription/medication services | Prescription volumes and patterns |
| Revenue Cycle / Billing Manager | Owns claims and reimbursement performance | Claim volumes, denial rates, processing time, denial reasons |
| Data Governance / Compliance Officer | Owns PHI/PII risk and regulatory compliance | Access control, masking, auditability, lineage |
| Platform/Analytics Consumer **[ASSUMPTION]** | Future ML/agentic applications and BI tooling | Governed Gold-layer data products, not raw PHI |

------------------------------------------------------------------------

# 2. Business Questions

Directly derived from the outcomes in `README.md` section 3.

**Patient 360**
- What is a given patient's full history of encounters, providers,
  facilities, diagnoses, labs, prescriptions and claims?
- Has the same patient been seen at more than one MediCore facility?

**Clinical & Operational Intelligence**
- Which facilities have increasing/decreasing patient volumes?
- How is provider workload distributed across facilities and specialties?
- Which specialties see the highest demand, and how is that trending?
- Are there abnormal laboratory-result trends by facility or test type?
- What are prescription patterns by specialty, facility, or medication?

**Claims & Revenue Intelligence**
- What is the claim approval/denial rate, overall and by facility?
- What are the most common denial reasons?
- What is the average/outlier claim processing time?
- What is total and trending claim value by facility?

**Trusted & Governed Data**
- Which datasets/columns carry PHI and require masking or restricted access?
- Can every Gold-layer figure be traced back to its Bronze source record?

------------------------------------------------------------------------

# 3. Data Products

Restated from `README.md` section 10 for traceability --- each maps to one
or more business questions above:

| Data product | Answers |
|---|---|
| Patient 360 | Patient history questions |
| Facility Performance | Facility volume/utilization questions |
| Provider Performance | Provider workload questions |
| Clinical Activity | Encounter/specialty trend questions |
| Laboratory Analytics | Lab volume/abnormal-trend questions |
| Claims Analytics | Denial rate, processing time, claim value questions |

------------------------------------------------------------------------

# 4. Next: Phase 2 --- Source Understanding

With personas, questions, and data products established, the remaining
Phase 1 "next milestone" items --- source applications, source-system
responsibilities, source entity contracts, and entity relationships --- are
Phase 2 scope and are covered in `phase2_source_understanding.md`.
