"""Per-entity record generation for the MediCore simulated source systems.

Timestamp fields are emitted as datetime/date objects; the writers serialise
them per output format.
"""

import random
from datetime import date, datetime, timedelta

from . import reference_data as ref

WINDOW_START = datetime(2025, 1, 1)
WINDOW_END = datetime(2026, 6, 30, 23, 59)
REGISTRATION_START = datetime(2022, 1, 1)


def weighted_choice(rng: random.Random, pairs: list[tuple]):
    values = [pair[0] for pair in pairs]
    weights = [pair[1] for pair in pairs]
    return rng.choices(values, weights=weights, k=1)[0]


def random_datetime(rng: random.Random, start: datetime, end: datetime) -> datetime:
    span = int((end - start).total_seconds())
    return start + timedelta(seconds=rng.randint(0, max(span, 1)))


def _phone(rng: random.Random) -> str:
    return f"{rng.choice('6789')}{rng.randint(0, 999999999):09d}"


def _email(rng: random.Random, first: str, last: str) -> str:
    style = rng.randint(0, 3)
    local = {
        0: f"{first}.{last}",
        1: f"{first}{last}",
        2: f"{first}{rng.randint(1, 99)}",
        3: f"{first[0]}{last}{rng.randint(1, 999)}",
    }[style].lower()
    return f"{local}@{rng.choice(ref.EMAIL_DOMAINS)}"


def _person_name(rng: random.Random, gender: str) -> tuple[str, str]:
    if gender == "F":
        first = rng.choice(ref.FIRST_NAMES_FEMALE)
    elif gender == "M":
        first = rng.choice(ref.FIRST_NAMES_MALE)
    else:
        first = rng.choice(ref.FIRST_NAMES_MALE + ref.FIRST_NAMES_FEMALE)
    return first, rng.choice(ref.LAST_NAMES)


def generate_facilities() -> list[dict]:
    rows = []
    for facility in ref.FACILITIES:
        opened = date.fromisoformat(facility["opened_date"])
        rows.append(
            {
                "facility_id": facility["facility_id"],
                "facility_name": facility["facility_name"],
                "facility_type": facility["facility_type"],
                "address_line1": facility["address_line1"],
                "city": facility["city"],
                "state": facility["state"],
                "postal_code": facility["postal_code"],
                "phone": facility["phone"],
                "opened_date": opened,
                "created_at": datetime.combine(opened, datetime.min.time()),
                "updated_at": datetime.combine(opened, datetime.min.time()),
            }
        )
    return rows


def generate_providers(rng: random.Random, count: int) -> list[dict]:
    facility_ids = [facility["facility_id"] for facility in ref.FACILITIES]
    rows = []
    for index in range(count):
        gender = weighted_choice(rng, ref.GENDERS)
        first, last = _person_name(rng, gender)
        affiliation_count = weighted_choice(rng, [(1, 0.62), (2, 0.28), (3, 0.10)])
        affiliations = sorted(rng.sample(facility_ids, affiliation_count))
        created = random_datetime(rng, datetime(2015, 1, 1), datetime(2025, 12, 31))
        rows.append(
            {
                "provider_id": f"PR{1001 + index}",
                "npi": f"{rng.randint(1000000000, 1999999999)}",
                "first_name": first,
                "last_name": last,
                "specialty": weighted_choice(rng, ref.SPECIALTIES),
                "credential": rng.choice(ref.CREDENTIALS),
                "email": _email(rng, first, last),
                "phone": _phone(rng),
                "facility_ids": affiliations,
                "is_active": rng.random() > 0.05,
                "created_at": created,
                "updated_at": created + timedelta(days=rng.randint(0, 400)),
            }
        )
    return rows


def generate_patients(rng: random.Random, count: int) -> list[dict]:
    """Patient IDs restart at P10001 for every facility.

    This is deliberate: each facility's registration system assigns its own
    identifiers, so the same id string means different people at different
    facilities and the business key is (facility_id, patient_id). See
    phase2_source_understanding.md section 3.1.
    """
    rows = []
    for facility in ref.FACILITIES:
        facility_count = round(count * facility["patient_share"])
        opened = datetime.combine(
            date.fromisoformat(facility["opened_date"]), datetime.min.time()
        )
        registration_floor = max(REGISTRATION_START, opened)
        for index in range(facility_count):
            gender = weighted_choice(rng, ref.GENDERS)
            first, last = _person_name(rng, gender)
            age = weighted_choice(
                rng,
                [
                    (rng.randint(0, 17), 0.14),
                    (rng.randint(18, 39), 0.32),
                    (rng.randint(40, 64), 0.36),
                    (rng.randint(65, 92), 0.18),
                ],
            )
            birth_date = date(2026, 6, 30) - timedelta(days=age * 365 + rng.randint(0, 364))
            registered = random_datetime(
                rng, registration_floor, datetime(2026, 6, 15)
            )
            insurer = weighted_choice(rng, ref.INSURERS)
            rows.append(
                {
                    "patient_id": f"P{10001 + index}",
                    "facility_id": facility["facility_id"],
                    "first_name": first,
                    "last_name": last,
                    "date_of_birth": birth_date,
                    "gender": gender,
                    "phone": _phone(rng),
                    "email": _email(rng, first, last),
                    "address_line1": f"{rng.randint(1, 499)} {rng.choice(['Main Road', 'Sector 15', 'Model Town', 'Civil Lines', 'Green Park', 'MG Road'])}",
                    "city": facility["city"],
                    "state": facility["state"],
                    "postal_code": facility["postal_code"],
                    "insurance_provider": insurer,
                    "insurance_member_id": (
                        None if insurer == "Self Pay"
                        else f"{insurer[:3].upper()}{rng.randint(10000000, 99999999)}"
                    ),
                    "registration_date": registered.date(),
                    "created_at": registered,
                    "updated_at": registered,
                }
            )
    return rows


def _department_for(specialty: str) -> str:
    mapping = {
        "General Medicine": "Internal Medicine",
        "Obstetrics & Gynaecology": "Obstetrics",
        "Emergency Medicine": "Emergency",
        "Pathology": "Laboratory",
    }
    return mapping.get(specialty, specialty)


def _preferred_specialties(encounter_type: str, diagnosis_specialty: str, age: int) -> list[str]:
    if encounter_type == "EMERGENCY":
        return ["Emergency Medicine", "General Medicine"]
    if encounter_type == "DIAGNOSTIC":
        return ["Radiology", "Pathology"]
    if age < 18:
        return ["Pediatrics", diagnosis_specialty, "General Medicine"]
    return [diagnosis_specialty, "General Medicine"]


def generate_encounters(
    rng: random.Random, count: int, patients: list[dict], providers: list[dict]
) -> list[dict]:
    facility_by_id = {facility["facility_id"]: facility for facility in ref.FACILITIES}
    providers_by_facility: dict[str, list[dict]] = {
        facility["facility_id"]: [] for facility in ref.FACILITIES
    }
    for provider in providers:
        if not provider["is_active"]:
            continue
        for facility_id in provider["facility_ids"]:
            providers_by_facility[facility_id].append(provider)

    by_facility_specialty: dict[tuple[str, str], list[dict]] = {}
    for facility_id, facility_providers in providers_by_facility.items():
        for provider in facility_providers:
            by_facility_specialty.setdefault(
                (facility_id, provider["specialty"]), []
            ).append(provider)

    # Visit frequency is uneven in reality: most patients attend once or
    # twice, a small share are frequent attenders.
    visit_weights = [
        weighted_choice(rng, [(1, 0.62), (3, 0.28), (9, 0.10)]) for _ in patients
    ]

    rows = []
    for index in range(count):
        patient = rng.choices(patients, weights=visit_weights, k=1)[0]
        facility = facility_by_id[patient["facility_id"]]
        encounter_type = weighted_choice(
            rng, ref.FACILITY_ENCOUNTER_TYPES[facility["facility_type"]]
        )
        earliest = max(WINDOW_START, patient["created_at"])
        admitted = random_datetime(rng, earliest, WINDOW_END)

        cancelled = rng.random() < 0.02
        if cancelled:
            status, discharged = "CANCELLED", None
        elif encounter_type == "INPATIENT":
            status = "DISCHARGED"
            discharged = admitted + timedelta(days=rng.randint(1, 8), hours=rng.randint(0, 23))
        elif encounter_type == "EMERGENCY":
            status = "DISCHARGED"
            discharged = admitted + timedelta(hours=rng.randint(2, 12))
        else:
            status = "COMPLETED"
            discharged = admitted + timedelta(minutes=rng.randint(20, 120))

        eligible = [
            entry for entry in ref.DIAGNOSES
            if not entry[4] or patient["gender"] == "F"
        ]
        diagnosis_code, diagnosis_desc, diagnosis_specialty = weighted_choice(
            rng,
            [((code, desc, specialty), weight) for code, desc, weight, specialty, _ in eligible],
        )

        age = (admitted.date() - patient["date_of_birth"]).days // 365
        provider = None
        for specialty in _preferred_specialties(encounter_type, diagnosis_specialty, age):
            candidates = by_facility_specialty.get((facility["facility_id"], specialty))
            if candidates:
                provider = rng.choice(candidates)
                break
        if provider is None:
            provider = rng.choice(providers_by_facility[facility["facility_id"]])

        rows.append(
            {
                "encounter_id": f"ENC{index + 1:08d}",
                "facility_id": facility["facility_id"],
                "patient_id": patient["patient_id"],
                "provider_id": provider["provider_id"],
                "encounter_type": encounter_type,
                "encounter_status": status,
                "department": _department_for(provider["specialty"]),
                "admission_timestamp": admitted,
                "discharge_timestamp": discharged,
                "primary_diagnosis_code": diagnosis_code,
                "primary_diagnosis_desc": diagnosis_desc,
                "created_at": admitted,
                "updated_at": discharged or admitted,
            }
        )
    return rows


_LAB_PROBABILITY = {"DIAGNOSTIC": 0.95, "HOSPITAL": 0.55, "CLINIC": 0.35}


def generate_lab_results(rng: random.Random, encounters: list[dict]) -> list[dict]:
    facility_type_by_id = {
        facility["facility_id"]: facility["facility_type"] for facility in ref.FACILITIES
    }
    rows = []
    sequence = 0
    for encounter in encounters:
        if encounter["encounter_status"] == "CANCELLED":
            continue
        facility_type = facility_type_by_id[encounter["facility_id"]]
        if rng.random() > _LAB_PROBABILITY[facility_type]:
            continue
        for test in rng.sample(ref.LAB_TESTS, rng.randint(1, 4)):
            code, name, unit, low, high, decimals = test
            span = high - low
            if rng.random() < 0.78:
                value = rng.uniform(low, high)
                flag = "NORMAL"
            elif rng.random() < 0.5:
                value = rng.uniform(max(low - span * 0.9, 0), low)
                flag = "CRITICAL" if value < low - span * 0.6 else "LOW"
            else:
                value = rng.uniform(high, high + span * 0.9)
                flag = "CRITICAL" if value > high + span * 0.6 else "HIGH"

            collected = encounter["admission_timestamp"] + timedelta(
                minutes=rng.randint(10, 240)
            )
            sequence += 1
            rows.append(
                {
                    "lab_result_id": f"LAB{sequence:09d}",
                    "encounter_id": encounter["encounter_id"],
                    "facility_id": encounter["facility_id"],
                    "patient_id": encounter["patient_id"],
                    "test_code": code,
                    "test_name": name,
                    "result_value": round(value, decimals),
                    "result_unit": unit,
                    "reference_range_low": low,
                    "reference_range_high": high,
                    "abnormal_flag": flag,
                    "specimen_collected_at": collected,
                    "result_reported_at": collected + timedelta(hours=rng.randint(1, 48)),
                    "result_version": 1,
                    "created_at": collected,
                    "updated_at": collected,
                }
            )
    return rows


_PRESCRIPTION_PROBABILITY = {"DIAGNOSTIC": 0.05, "HOSPITAL": 0.55, "CLINIC": 0.60}


def generate_prescriptions(rng: random.Random, encounters: list[dict]) -> list[dict]:
    facility_type_by_id = {
        facility["facility_id"]: facility["facility_type"] for facility in ref.FACILITIES
    }
    rows = []
    sequence = 0
    for encounter in encounters:
        if encounter["encounter_status"] == "CANCELLED":
            continue
        facility_type = facility_type_by_id[encounter["facility_id"]]
        if rng.random() > _PRESCRIPTION_PROBABILITY[facility_type]:
            continue
        for medication in rng.sample(ref.MEDICATIONS, rng.randint(1, 3)):
            code, name, dosage, frequency = medication
            status = weighted_choice(
                rng, [("FILLED", 0.82), ("PRESCRIBED", 0.14), ("CANCELLED", 0.04)]
            )
            prescribed = encounter["admission_timestamp"].date()
            duration = rng.choice([3, 5, 7, 10, 14, 30, 90])
            sequence += 1
            rows.append(
                {
                    "prescription_id": f"RX{sequence:08d}",
                    "encounter_id": encounter["encounter_id"],
                    "facility_id": encounter["facility_id"],
                    "patient_id": encounter["patient_id"],
                    "provider_id": encounter["provider_id"],
                    "medication_code": code,
                    "medication_name": name,
                    "dosage": dosage,
                    "frequency": frequency,
                    "duration_days": duration,
                    "quantity": duration * (2 if frequency == "BD" else 3 if frequency == "TDS" else 1),
                    "prescription_status": status,
                    "prescribed_date": prescribed,
                    "filled_date": (
                        prescribed + timedelta(days=rng.randint(0, 3))
                        if status == "FILLED"
                        else None
                    ),
                    "created_at": encounter["admission_timestamp"],
                    "updated_at": encounter["admission_timestamp"],
                }
            )
    return rows


_BILLED_RANGES = {
    ("FACILITY_FEE", "INPATIENT"): (25000, 180000),
    ("FACILITY_FEE", "EMERGENCY"): (8000, 45000),
    ("FACILITY_FEE", "OUTPATIENT"): (500, 2500),
    ("FACILITY_FEE", "DIAGNOSTIC"): (300, 1500),
    ("PROFESSIONAL_FEE", "INPATIENT"): (5000, 40000),
    ("PROFESSIONAL_FEE", "EMERGENCY"): (2000, 12000),
    ("PROFESSIONAL_FEE", "OUTPATIENT"): (500, 3000),
    ("PROFESSIONAL_FEE", "DIAGNOSTIC"): (400, 2000),
    ("LAB", None): (300, 6000),
    ("PHARMACY", None): (200, 9000),
}


def generate_claims(
    rng: random.Random,
    encounters: list[dict],
    patients: list[dict],
    lab_results: list[dict],
    prescriptions: list[dict],
) -> list[dict]:
    patient_by_key = {
        (patient["facility_id"], patient["patient_id"]): patient for patient in patients
    }
    encounters_with_labs = {row["encounter_id"] for row in lab_results}
    encounters_with_prescriptions = {row["encounter_id"] for row in prescriptions}

    rows = []
    sequence = 0
    for encounter in encounters:
        if encounter["encounter_status"] == "CANCELLED":
            continue
        patient = patient_by_key[(encounter["facility_id"], encounter["patient_id"])]
        if patient["insurance_provider"] == "Self Pay":
            continue

        categories = ["FACILITY_FEE"]
        if rng.random() < 0.85:
            categories.append("PROFESSIONAL_FEE")
        if encounter["encounter_id"] in encounters_with_labs and rng.random() < 0.80:
            categories.append("LAB")
        if encounter["encounter_id"] in encounters_with_prescriptions and rng.random() < 0.70:
            categories.append("PHARMACY")

        for category in categories:
            low, high = _BILLED_RANGES.get(
                (category, encounter["encounter_type"]), _BILLED_RANGES.get((category, None))
            )
            billed = round(rng.uniform(low, high), 2)
            submitted = encounter["admission_timestamp"].date() + timedelta(
                days=rng.randint(0, 5)
            )
            # Recently submitted claims cannot plausibly be settled yet.
            if (WINDOW_END.date() - submitted).days < 30:
                status = weighted_choice(rng, [("SUBMITTED", 0.55), ("IN_REVIEW", 0.45)])
            else:
                status = weighted_choice(rng, ref.CLAIM_STATUSES)

            if status in ("SUBMITTED", "IN_REVIEW"):
                allowed = paid = None
                status_updated = None if status == "SUBMITTED" else submitted + timedelta(
                    days=rng.randint(1, 10)
                )
            elif status == "DENIED":
                allowed = paid = 0.0
                status_updated = submitted + timedelta(days=rng.randint(5, 45))
            else:
                allowed = round(billed * rng.uniform(0.70, 1.0), 2)
                paid = allowed if status == "PAID" else 0.0
                status_updated = submitted + timedelta(days=rng.randint(5, 45))

            sequence += 1
            rows.append(
                {
                    "claim_id": f"CLM{sequence:08d}",
                    "encounter_id": encounter["encounter_id"],
                    "facility_id": encounter["facility_id"],
                    "patient_id": encounter["patient_id"],
                    "service_category": category,
                    "insurance_provider": patient["insurance_provider"],
                    "insurance_member_id": patient["insurance_member_id"],
                    "billed_amount": billed,
                    "allowed_amount": allowed,
                    "paid_amount": paid,
                    "claim_status": status,
                    "denial_reason": (
                        rng.choice(ref.DENIAL_REASONS) if status == "DENIED" else None
                    ),
                    "submitted_date": submitted,
                    "status_updated_date": status_updated,
                    "created_at": datetime.combine(submitted, datetime.min.time()),
                    "updated_at": datetime.combine(
                        status_updated or submitted, datetime.min.time()
                    ),
                }
            )
    return rows
