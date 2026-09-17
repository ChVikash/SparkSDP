"""Output writers for the source-file formats defined in README.md section 6."""

import csv
import json
from datetime import date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def _prepare(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _serialise(value):
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    return value


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    _prepare(path)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _serialise(row.get(column)) for column in columns})


def write_jsonl(path: Path, rows: list[dict]) -> None:
    """Newline-delimited JSON: one object per line, which is what Auto Loader
    reads by default without multiLine handling."""
    _prepare(path)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = {key: _serialise(value) for key, value in row.items()}
            handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def write_parquet(path: Path, rows: list[dict], schema: pa.Schema) -> None:
    _prepare(path)
    columns = {field.name: [row.get(field.name) for row in rows] for field in schema}
    table = pa.Table.from_pydict(columns, schema=schema)
    pq.write_table(table, path, compression="snappy")
