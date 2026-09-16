# MediCore Health Network --- Phase 2: Source Understanding

This document delivers the Phase 2 output defined in `README.md`
(sections 4 and 18): source applications and responsibilities, entity
relationships, and a source-data contract per entity.

Phase 1 business-understanding content --- personas, business questions,
and data products --- lives in `phase1_business_understanding.md`.

> **Note on assumptions:** the base README defines the business scenario,
> the 7 entities, and the 5 operational application areas, but does not
> spell out per-entity contract details. Those are drafted here as a
> reasonable first pass grounded in the business scenario, and are
> flagged as **[ASSUMPTION]** where they go beyond what the README states
> directly. Please correct/override anything that doesn't match your
> intent before this is treated as final.

------------------------------------------------------------------------

# 1. Source Applications and Responsibilities

README section 2 names five operational application areas. Facilities and
providers are treated here as centrally-maintained reference/master data
rather than being owned by one of the five transactional apps
**[ASSUMPTION --- please confirm]**:

| Source application | Entities owned | Nature |
|---|---|---|
| Patient Management System | `patients` | Registration + demographic updates |
| Facility & Provider Directory **[ASSUMPTION]** | `facilities`, `providers` | Administrative reference/master data, low change frequency |
| Clinical / Encounter Management System | `encounters` | Visit lifecycle (admit → discharge / open → close) |
| Laboratory Information System (LIS) | `lab_results` | Orders and results tied to an encounter |
| Pharmacy / Prescription Management System | `prescriptions` | Medications tied to an encounter |
| Billing & Claims Management System | `claims` | Claim lifecycle tied to an encounter |

------------------------------------------------------------------------

# 2. Entity Relationships

```text
facilities ──1:N── providers        (a provider may serve multiple facilities → treat as N:M [ASSUMPTION])
facilities ──1:N── encounters
providers  ──1:N── encounters
patients   ──1:N── encounters

encounters ──1:N── lab_results
encounters ──1:N── prescriptions
encounters ──1:N── claims           (assume one facility/encounter can generate multiple claims/line items)
```

`encounters` is the fan-out point: nearly every downstream fact
(`lab_results`, `prescriptions`, `claims`) traces back to an encounter,
which is itself the join point for `patients` × `providers` × `facilities`.
This matches the Gold dimensional model already sketched in README
section 10.

------------------------------------------------------------------------

# 3. Source Data Contracts

## 3.1 `patients`

| Attribute | Detail |
|---|---|
| Business meaning | A person registered to receive care at any MediCore facility |
| Business key | `patient_id` (assigned at registration) |
| Relationships | 1:N to `encounters` |
| Update pattern | Mutable --- demographic changes (address, phone, email, insurance) over time |
| Append-only / event? | No --- master-like entity; SCD Type 2 candidate in Gold (`dim_patient`) |
| Source timestamps | `created_at`/registration date, `updated_at`/last-modified date |
| Ingestion characteristics | `patients.csv`, batch delivery per load |
| PII/PHI | Name, DOB, SSN/national ID, phone, email, address, insurance ID --- high sensitivity |
| Likely DQ issues | Missing patient identifiers, malformed emails, possible duplicate patient records across facilities (no cross-facility MPI implied by README), late-arriving demographic corrections (Load 4/5) |
| Schema evolution | Additional attributes possible in Load 3 (e.g. emergency contact, preferred language) |

**[ASSUMPTION / open question]:** the README doesn't say whether
`patient_id` is globally unique across the network or assigned
per-facility. If per-facility, true Patient 360 requires an
identity-resolution/MPI step not yet described --- worth deciding
explicitly before Gold design.

## 3.2 `providers`

| Attribute | Detail |
|---|---|
| Business meaning | Clinicians delivering care across one or more facilities |
| Business key | `provider_id` (real-world analogue: NPI) |
| Relationships | N:M to `facilities`; 1:N to `encounters` |
| Update pattern | Mutable but low-frequency --- specialty, credential, active/inactive status |
| Append-only / event? | No --- slowly changing reference data; SCD1 or SCD2 candidate |
| Source timestamps | `created_at`, `updated_at` |
| Ingestion characteristics | `providers.json`, batch, small volume |
| PII/PHI | Name and contact info --- sensitive but not PHI in the same sense as patient data |
| Likely DQ issues | Invalid provider references surfacing downstream in `encounters` (Load 4) |
| Schema evolution | Possible added sub-specialty/credential attributes |

## 3.3 `facilities`

| Attribute | Detail |
|---|---|
| Business meaning | Physical locations in the network (hospital, clinic, diagnostic center) |
| Business key | `facility_id` |
| Relationships | 1:N to `providers`, 1:N to `encounters` |
| Update pattern | Rarely changes --- near-static reference data |
| Append-only / event? | No --- static/slowly changing |
| Source timestamps | `created_at`, `updated_at` |
| Ingestion characteristics | `facilities.json`, batch, very small volume (4 known facilities) |
| PII/PHI | None --- facility name/address is not patient data |
| Likely DQ issues | Minimal, given small volume; possible naming inconsistencies |
| Schema evolution | Possible added attributes (bed count, department list) |

## 3.4 `encounters`

| Attribute | Detail |
|---|---|
| Business meaning | A clinical visit/interaction between a patient and a provider at a facility |
| Business key | `encounter_id` |
| Relationships | N:1 to `patients`, `providers`, `facilities`; 1:N to `lab_results`, `prescriptions`, `claims` |
| Update pattern | Primarily new records, but status can transition during the visit lifecycle (e.g. admitted → discharged) |
| Append-only / event? | Mostly event-like, but not strictly immutable --- status updates and late corrections occur (Load 5) |
| Source timestamps | `encounter_date`/admission timestamp, discharge timestamp, `updated_at` |
| Ingestion characteristics | `encounters.json`, higher volume, incremental per load |
| PII/PHI | Linked patient identifier + visit reason/diagnosis --- PHI once joined to `patients` |
| Likely DQ issues | Late-arriving encounters, duplicate late-arriving records (Load 5) |
| Schema evolution | Possible added visit-reason/diagnosis-coding fields (Load 3) |

## 3.5 `lab_results`

| Attribute | Detail |
|---|---|
| Business meaning | Laboratory test results ordered as part of an encounter |
| Business key | `lab_result_id` |
| Relationships | N:1 to `encounters` (transitively to patient/provider/facility) |
| Update pattern | Mostly append; occasional corrections to previously reported results |
| Append-only / event? | Primarily append-only/event, with rare corrections requiring versioning or latest-wins handling |
| Source timestamps | Collected/result date, reported timestamp |
| Ingestion characteristics | `lab_results.parquet` --- the one columnar source, likely a LIS batch extract |
| PII/PHI | High sensitivity --- actual clinical result values tied to a patient |
| Likely DQ issues | Corrected lab information (Load 3), late-arriving results, duplicate late-arriving records, corrected results (Load 5) |
| Schema evolution | Possible additional test-panel attributes |

## 3.6 `prescriptions`

| Attribute | Detail |
|---|---|
| Business meaning | Medications prescribed to a patient during an encounter |
| Business key | `prescription_id` |
| Relationships | N:1 to `encounters` (transitively to patient/provider) |
| Update pattern | Primarily append; status may change (filled/cancelled) **[ASSUMPTION]** |
| Append-only / event? | Largely event/append-only |
| Source timestamps | Prescribed date, filled date |
| Ingestion characteristics | `prescriptions.csv`, batch from Pharmacy system |
| PII/PHI | Medication data tied to a patient --- PHI |
| Likely DQ issues | Not named explicitly in README; general Load 4 patterns (duplicates, invalid categorical values) assumed to apply **[ASSUMPTION]** |
| Schema evolution | Possible added dosage/frequency fields |

## 3.7 `claims`

| Attribute | Detail |
|---|---|
| Business meaning | Insurance claims submitted for services rendered during an encounter |
| Business key | `claim_id` |
| Relationships | N:1 to `encounters` |
| Update pattern | Highly mutable --- status progresses (submitted → under review → approved/denied → paid) |
| Append-only / event? | No --- the clearest CDC/upsert candidate in the source set |
| Source timestamps | Submitted date, status-updated date |
| Ingestion characteristics | `claims.json`, incremental from Billing/Claims system |
| PII/PHI | Insurance ID, claim amounts, diagnosis/procedure codes tied to patient --- PHI + sensitive financial data |
| Likely DQ issues | Negative claim amounts, invalid claim statuses (Load 4); late-arriving updated claims (Load 5) |
| Schema evolution | Possible added claim line-item detail |

------------------------------------------------------------------------

# 4. Open Items Before Phase 3 (Architecture)

1. Confirm whether `patient_id` is network-global or per-facility (drives
   whether an MPI/identity-resolution step is needed before `dim_patient`).
2. Confirm the `facilities`/`providers` ownership assumption in section 4,
   or specify the actual owning system(s).
3. Confirm encounter → claim cardinality (1:1 vs 1:N) to finalize
   `fact_claim` grain.
4. Confirm whether any entity has a genuine multi-facility identity overlap
   scenario intended for Load 2+ (e.g. a patient seen at two facilities),
   since this directly exercises the Patient 360 outcome.
