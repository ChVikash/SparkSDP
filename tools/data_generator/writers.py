"""Writes a load's records out as source-system file deliveries.

Writing happens on the driver with pandas, which produces one properly named
file per entity rather than Spark's part-file directory. That keeps the
landing zone looking like a real source extract, keeps `_source_file` in
Bronze meaningful, and works unchanged on serverless, dedicated and standard
access mode, since Unity Catalog Volume paths are reachable from the driver
and nothing here needs a SparkContext.

Parquet goes through pyarrow rather than pandas so the column types in
schemas.py are written exactly as declared; pandas would widen int32 and turn
the date columns into timestamps.
"""

from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from . import schemas


def _serialise(value):
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _frame(rows: list[dict], columns: list[str]) -> pd.DataFrame:
    """Build a text-ready frame.

    dtype=object throughout: pandas would otherwise promote an integer column
    containing nulls to float and write `5.0` where the source system wrote
    `5`.
    """
    serialised = [
        {column: _serialise(row.get(column)) for column in columns} for row in rows
    ]
    return pd.DataFrame(serialised, columns=columns, dtype=object)


def _write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    _frame(rows, columns).to_csv(path, index=False, lineterminator="\n")


def _write_jsonl(path: Path, rows: list[dict], columns: list[str]) -> None:
    """Newline-delimited JSON: one object per line, which is what Auto Loader
    reads by default without multiLine handling."""
    _frame(rows, columns).to_json(
        path, orient="records", lines=True, force_ascii=False
    )


def _write_parquet(path: Path, rows: list[dict], schema: pa.Schema) -> None:
    columns = {field.name: [row.get(field.name) for row in rows] for field in schema}
    table = pa.Table.from_pydict(columns, schema=schema)
    pq.write_table(table, path, compression="snappy")


def write_entity(entity: str, rows: list[dict], load_dir: str) -> str:
    """Write one entity's rows into `load_dir`. Returns the file written."""
    spec = schemas.ENTITIES[entity]
    directory = Path(load_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / spec["filename"]
    columns = schemas.column_names(entity)

    if spec["format"] == "csv":
        _write_csv(path, rows, columns)
    elif spec["format"] == "json":
        _write_jsonl(path, rows, columns)
    else:
        _write_parquet(path, rows, schemas.pyarrow_schema(entity))
    return str(path)
