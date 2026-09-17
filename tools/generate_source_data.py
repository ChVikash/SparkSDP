#!/usr/bin/env python3
"""Generate MediCore's simulated source-system file deliveries.

Writes one load's files into the landing layout described in
phase3_architecture.md section 3:

    <out-dir>/<entity>/load_<n>/<file>

Output is deterministic for a given --seed, so a load can be regenerated
byte-for-byte rather than being treated as an untracked artefact.

Usage:
    python3 tools/generate_source_data.py --load 1
"""

import argparse
import random
import sys
from pathlib import Path

import pyarrow as pa

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_generator import entities, writers  # noqa: E402

PATIENT_COLUMNS = [
    "patient_id", "facility_id", "first_name", "last_name", "date_of_birth",
    "gender", "phone", "email", "address_line1", "city", "state", "postal_code",
    "insurance_provider", "insurance_member_id", "registration_date",
    "created_at", "updated_at",
]

PRESCRIPTION_COLUMNS = [
    "prescription_id", "encounter_id", "facility_id", "patient_id", "provider_id",
    "medication_code", "medication_name", "dosage", "frequency", "duration_days",
    "quantity", "prescription_status", "prescribed_date", "filled_date",
    "created_at", "updated_at",
]

LAB_RESULT_SCHEMA = pa.schema([
    ("lab_result_id", pa.string()),
    ("encounter_id", pa.string()),
    ("facility_id", pa.string()),
    ("patient_id", pa.string()),
    ("test_code", pa.string()),
    ("test_name", pa.string()),
    ("result_value", pa.float64()),
    ("result_unit", pa.string()),
    ("reference_range_low", pa.float64()),
    ("reference_range_high", pa.float64()),
    ("abnormal_flag", pa.string()),
    ("specimen_collected_at", pa.timestamp("us")),
    ("result_reported_at", pa.timestamp("us")),
    ("result_version", pa.int32()),
    ("created_at", pa.timestamp("us")),
    ("updated_at", pa.timestamp("us")),
])


def build_load_1(rng: random.Random, patients: int, providers: int, encounters: int) -> dict:
    """Load 1 is the clean baseline: full referential integrity, valid
    categoricals, no duplicates (README.md section 5)."""
    facility_rows = entities.generate_facilities()
    provider_rows = entities.generate_providers(rng, providers)
    patient_rows = entities.generate_patients(rng, patients)
    encounter_rows = entities.generate_encounters(rng, encounters, patient_rows, provider_rows)
    lab_rows = entities.generate_lab_results(rng, encounter_rows)
    prescription_rows = entities.generate_prescriptions(rng, encounter_rows)
    claim_rows = entities.generate_claims(
        rng, encounter_rows, patient_rows, lab_rows, prescription_rows
    )
    return {
        "facilities": facility_rows,
        "providers": provider_rows,
        "patients": patient_rows,
        "encounters": encounter_rows,
        "lab_results": lab_rows,
        "prescriptions": prescription_rows,
        "claims": claim_rows,
    }


def write_load(data: dict, out_dir: Path, load: int) -> list[tuple[str, int, Path]]:
    def target(entity: str, filename: str) -> Path:
        return out_dir / entity / f"load_{load}" / filename

    written = []

    path = target("patients", "patients.csv")
    writers.write_csv(path, data["patients"], PATIENT_COLUMNS)
    written.append(("patients", len(data["patients"]), path))

    path = target("providers", "providers.json")
    writers.write_jsonl(path, data["providers"])
    written.append(("providers", len(data["providers"]), path))

    path = target("facilities", "facilities.json")
    writers.write_jsonl(path, data["facilities"])
    written.append(("facilities", len(data["facilities"]), path))

    path = target("encounters", "encounters.json")
    writers.write_jsonl(path, data["encounters"])
    written.append(("encounters", len(data["encounters"]), path))

    path = target("lab_results", "lab_results.parquet")
    writers.write_parquet(path, data["lab_results"], LAB_RESULT_SCHEMA)
    written.append(("lab_results", len(data["lab_results"]), path))

    path = target("prescriptions", "prescriptions.csv")
    writers.write_csv(path, data["prescriptions"], PRESCRIPTION_COLUMNS)
    written.append(("prescriptions", len(data["prescriptions"]), path))

    path = target("claims", "claims.json")
    writers.write_jsonl(path, data["claims"])
    written.append(("claims", len(data["claims"]), path))

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--load", type=int, default=1, help="Load number to generate (1-5)")
    parser.add_argument("--out-dir", type=Path, default=Path("generated_data"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--patients", type=int, default=2000)
    parser.add_argument("--providers", type=int, default=120)
    parser.add_argument("--encounters", type=int, default=10000)
    args = parser.parse_args()

    if args.load != 1:
        parser.error(f"load {args.load} is not implemented yet; only load 1 exists so far")

    rng = random.Random(args.seed)
    data = build_load_1(rng, args.patients, args.providers, args.encounters)
    written = write_load(data, args.out_dir, args.load)

    print(f"Load {args.load} written to {args.out_dir}/ (seed {args.seed})")
    for entity, count, path in written:
        size_kb = path.stat().st_size / 1024
        print(f"  {entity:<15} {count:>7,} rows  {size_kb:>9,.0f} KB  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
