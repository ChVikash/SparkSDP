"""Spark writer backend.

Uses only the SparkSession DataFrame API. Nothing here touches
`spark.sparkContext`, `_jsc` or `_jvm`, because those are unavailable on
serverless and standard access mode, where Spark Connect provides no JVM
escape hatch. That rules out the Hadoop FileSystem API, so Spark writes its
own part file into the load directory rather than a file named by us; Auto
Loader ingests the directory either way.

Records are generated on the driver (see entities.py) and only written through
Spark, which keeps output deterministic for a given seed. Distributing the
generation itself would mean per-partition RNG state and reproducibility would
be lost -- not worth it at this project's volumes. If the simulation ever needs
hundreds of millions of rows, that is the point to revisit.

Paths go through Spark's own resolution, so the same code writes to a Unity
Catalog Volume, DBFS, S3, ADLS or a local path.
"""

from . import schemas


def _write_options(fmt: str) -> dict:
    if fmt == "csv":
        return {
            "header": "true",
            "timestampFormat": schemas.TIMESTAMP_FORMAT_JAVA,
            "dateFormat": schemas.DATE_FORMAT_JAVA,
        }
    if fmt == "json":
        # Spark drops null fields from JSON output by default; keeping them
        # makes the delivered schema stable across loads, which is what
        # Bronze schema handling is being tested against.
        return {
            "ignoreNullFields": "false",
            "timestampFormat": schemas.TIMESTAMP_FORMAT_JAVA,
            "dateFormat": schemas.DATE_FORMAT_JAVA,
        }
    return {"compression": "snappy"}


def write_entity(spark, entity: str, rows: list[dict], load_dir: str) -> str:
    """Write one entity's rows into `load_dir`. Returns the directory written."""
    spec = schemas.ENTITIES[entity]
    columns = schemas.column_names(entity)
    ordered = [{column: row.get(column) for column in columns} for row in rows]
    dataframe = spark.createDataFrame(ordered, schema=schemas.spark_schema(entity))

    target = load_dir.rstrip("/")
    writer = dataframe.coalesce(1).write.format(spec["format"]).mode("overwrite")
    for key, value in _write_options(spec["format"]).items():
        writer = writer.option(key, value)
    writer.save(target)
    return target
