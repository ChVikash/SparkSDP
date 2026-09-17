#!/usr/bin/env python3
"""Generate MediCore's simulated source-system file deliveries.

Writes one load's files into the landing layout described in
phase3_architecture.md section 3:

    <out-dir>/<entity>/load_<n>/<file>

Records are generated deterministically, so a load can be regenerated
byte-for-byte from its seed, and each entity is written as a single properly
named file (README.md section 6).

Writing is plain driver-side pandas/pyarrow, so this runs the same way on a
laptop and on Databricks -- including serverless and standard access mode,
where a Unity Catalog Volume path is reachable from the driver and no
SparkContext is available.

Usage:
    python3 tools/generate_source_data.py --load 1
    python3 tools/generate_source_data.py --load 1 \
        --out-dir /Volumes/medicore_dev/landing/source_files
"""

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_generator import entities, writers  # noqa: E402


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


def build_load(load: int, rng: random.Random, patients: int, providers: int, encounters: int) -> dict:
    if load == 1:
        return build_load_1(rng, patients, providers, encounters)
    raise NotImplementedError(f"load {load} is not implemented yet; only load 1 exists so far")


def write_load(data: dict, out_dir: str, load: int) -> list[tuple[str, int, str]]:
    written = []
    for entity, rows in data.items():
        load_dir = f"{out_dir.rstrip('/')}/{entity}/load_{load}"
        written.append((entity, len(rows), writers.write_entity(entity, rows, load_dir)))
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--load", type=int, default=1, help="Load number to generate (1-5)")
    parser.add_argument(
        "--out-dir",
        default="generated_data",
        help="Landing root. On Databricks: /Volumes/<catalog>/landing/source_files",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--patients", type=int, default=2000)
    parser.add_argument("--providers", type=int, default=120)
    parser.add_argument("--encounters", type=int, default=10000)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    data = build_load(args.load, rng, args.patients, args.providers, args.encounters)
    written = write_load(data, args.out_dir, args.load)

    print(f"Load {args.load} written to {args.out_dir} (seed {args.seed})")
    for entity, count, target in written:
        print(f"  {entity:<15} {count:>7,} rows  {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
