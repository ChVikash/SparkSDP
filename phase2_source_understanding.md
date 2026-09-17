# MediCore Health Network --- Phase 2: Source Understanding

This document delivers the Phase 2 output defined in `README.md`
(sections 4 and 18): source applications and responsibilities, entity
relationships, and a source-data contract per entity.

Phase 1 business-understanding content --- personas, business questions,
and data products --- lives in `phase1_business_understanding.md`.

------------------------------------------------------------------------

# 1. Source Applications and Responsibilities

README section 2 names five operational application areas. Facilities and
providers are owned by their own independent Facility & Provider Directory
system, rather than being folded into one of the five transactional apps
--- **[CONFIRMED]** keeping them independent avoids tightly coupling
reference/master data (low change frequency) to a transactional app's
lifecycle (high change frequency), which would otherwise create an
unnecessary dependency between unrelated domains:

| Source application | Entities owned | Nature |
|---|---|---|
| Patient Management System | `patients` | Registration + demographic updates |
| Facility & Provider Directory | `facilities`, `providers` | Administrative reference/master data, low change frequency, independent of transactional apps |
| Clinical / Encounter Management System | `encounters` | Visit lifecycle (admit → discharge / open → close) |
| Laboratory Information System (LIS) | `lab_results` | Orders and results tied to an encounter |
| Pharmacy / Prescription Management System | `prescriptions` | Medications tied to an encounter |
| Billing & Claims Management System | `claims` | Claim lifecycle tied to an encounter |

------------------------------------------------------------------------

# 2. Entity Relationships

```text
facilities ──N:M── providers        (a provider can work across multiple facilities in the same network,
                                      depending on whether the relevant infrastructure/specialty exists
                                      at each facility --- [CONFIRMED])
facilities ──1:N── encounters
providers  ──1:N── encounters
patients   ──1:N── encounters

encounters ──1:N── lab_results
encounters ──1:N── prescriptions
encounters ──1:N── claims           (one encounter can generate multiple claims/line items --- [CONFIRMED])
```

`encounters` is the fan-out point: nearly every downstream fact
(`lab_results`, `prescriptions`, `claims`) traces back to an encounter,
which is itself the join point for `patients` × `providers` × `facilities`.
This matches the Gold dimensional model already sketched in README
section 10.

------------------------------------------------------------------------

# 3. Source Data Contracts

The **ingestion characteristics** row in each contract below describes how
the entity is delivered *in this project*, where all seven arrive as files
(README §6). That is a simulation device. These are operational databases,
so a real deployment would replicate them through a managed CDC connector
instead --- see README §8 for the mechanism per source type, and
`phase3_architecture.md` §4.1 for what that substitution does and does not
change. Every other row --- business key, update pattern, PHI, and so on ---
is a property of the source itself and holds either way.

## 3.1 `patients`

| Attribute | Detail |
|---|---|
| Business meaning | A person registered to receive care at any MediCore facility |
| Business key | `patient_id`, assigned at registration --- **not** globally unique across the network (per-facility) |
| Relationships | 1:N to `encounters` |
| Update pattern | Mutable --- demographic changes (address, phone, email, insurance) over time |
| Append-only / event? | No --- master-like entity; SCD Type 2 candidate in Gold (`dim_patient`) |
| Source timestamps | `created_at`/registration date, `updated_at`/last-modified date |
| Ingestion characteristics | `patients.csv`, batch delivery per load |
| PII/PHI | Name, DOB, SSN/national ID, phone, email, address, insurance ID --- high sensitivity |
| Likely DQ issues | Missing patient identifiers, malformed emails, duplicate/overlapping patient records across facilities (expected, not incidental --- see below), late-arriving demographic corrections (Load 4/5) |
| Schema evolution | Additional attributes possible in Load 3 (e.g. emergency contact, preferred language) |

**[CONFIRMED]** `patient_id` is per-facility, not globally unique. The
network is assumed to have grown in part through acquisition of existing
facility groups, each bringing its own legacy patient identifiers, so the
same real-world patient can legitimately appear as separate records under
different facilities. True Patient 360 therefore requires an explicit
identity resolution / Master Data Management (MDM) step in Silver to
reconcile per-facility patient records into a single network-wide
identity before `dim_patient` is built. This is now reflected in
`README.md` sections 2, 3.1, and 9.

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
| Update pattern | Primarily append; status may change (filled/cancelled) --- **[CONFIRMED]** |
| Append-only / event? | Largely event/append-only, with status transitions handled like `encounters` (append + in-place status update) |
| Source timestamps | Prescribed date, filled date |
| Ingestion characteristics | `prescriptions.csv`, batch from Pharmacy system |
| PII/PHI | Medication data tied to a patient --- PHI |
| Likely DQ issues | General Load 4 patterns (duplicates, invalid categorical values) apply here too --- **[CONFIRMED]** |
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

All items are now resolved.

**Resolved:**
- Multi-facility identity overlap scenarios --- confirmed, staged across
  three loads with increasing difficulty:
  - **Load 2**: clean cross-facility duplicate (same patient registers at
    a second facility under a new `patient_id`, demographics match
    exactly) --- first case exercising identity resolution / MDM.
  - **Load 4**: messier cross-facility duplicate with mismatched
    demographics (name/contact discrepancies) --- harder matching case,
    consistent with Load 4's data-quality-degradation theme.
  - **Load 5**: a correction to one side of an already-resolved
    cross-facility match arrives late, requiring re-evaluation of the MDM
    linkage --- consistent with Load 5's late-arriving/correction theme.
  Reflected in `README.md` Load 2, Load 4, and Load 5 sections.
- `facilities`/`providers` ownership --- independent Facility & Provider
  Directory system, kept separate from the 5 transactional apps to avoid
  coupling reference data to transactional lifecycles.
- `facilities`↔`providers` cardinality --- N:M, since a provider can work
  across multiple facilities in the same network depending on
  infrastructure/specialty availability at each site.
- `encounter`→`claims` cardinality --- 1:N, one encounter can generate
  multiple claims/line items.
- `patient_id` scope --- per-facility, not globally unique, due to the
  network having grown through acquisition of existing facility groups.
  Requires a Silver-layer identity resolution / MDM step; now reflected in
  `README.md` sections 2, 3.1, and 9.
- `prescriptions` update pattern --- status can change post-creation
  (filled/cancelled), same as `encounters`.
- `prescriptions` DQ issues --- general Load 4 patterns (duplicates,
  invalid categorical values) apply here too.
