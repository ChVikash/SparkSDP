"""Local filesystem writer backend.

Used when no Spark session is available. Produces the same filenames, column
order and timestamp formatting as the Spark backend (see spark_writers.py).
"""

import csv
import json
from datetime import date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from . import schemas


def _serialise(value):
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        # csv defaults to CRLF; Spark writes LF, and the two backends are
        # meant to produce byte-identical files.
        writer = csv.DictWriter(
            handle, fieldnames=columns, extrasaction="raise", lineterminator="\n"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _serialise(row.get(column)) for column in columns})


def _write_jsonl(path: Path, rows: list[dict], columns: list[str]) -> None:
    """Newline-delimited JSON: one object per line, which is what Auto Loader
    reads by default without multiLine handling."""
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = {column: _serialise(row.get(column)) for column in columns}
            handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def _write_parquet(path: Path, rows: list[dict], schema: pa.Schema) -> None:
    columns = {field.name: [row.get(field.name) for row in rows] for field in schema}
    table = pa.Table.from_pydict(columns, schema=schema)
    pq.write_table(table, path, compression="snappy")


def write_entity(entity: str, rows: list[dict], target: str) -> None:
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    fmt = schemas.ENTITIES[entity]["format"]
    columns = schemas.column_names(entity)

    if fmt == "csv":
        _write_csv(path, rows, columns)
    elif fmt == "json":
        _write_jsonl(path, rows, columns)
    else:
        _write_parquet(path, rows, schemas.pyarrow_schema(entity))
