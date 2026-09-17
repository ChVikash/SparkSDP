"""Spark writer backend.

Records are generated on the driver (see entities.py) and only written through
Spark, which keeps output deterministic for a given seed. Distributing the
generation itself would mean per-partition RNG state and reproducibility would
be lost -- not worth it at this project's volumes. If the simulation ever needs
hundreds of millions of rows, that is the point to revisit.

Paths are handled through Spark's Hadoop FileSystem abstraction, so the same
code writes to a Unity Catalog Volume, DBFS, S3, ADLS or a local path.
"""

from . import schemas


def _hadoop(spark):
    jvm = spark.sparkContext._jvm
    return jvm.org.apache.hadoop.fs.Path, spark.sparkContext._jsc.hadoopConfiguration()


def _write_single_file(dataframe, target: str, fmt: str, options: dict) -> None:
    """Write one named file rather than Spark's part-file directory.

    The simulation stands in for a source system delivering a file per
    extract, and the Bronze layer records `_source_file` per record, so a
    stable filename is worth the coalesce at these volumes.
    """
    spark = dataframe.sparkSession
    Path, hadoop_conf = _hadoop(spark)

    staging_path = Path(f"{target}__staging")
    filesystem = staging_path.getFileSystem(hadoop_conf)

    writer = dataframe.coalesce(1).write.format(fmt).mode("overwrite")
    for key, value in options.items():
        writer = writer.option(key, value)
    writer.save(staging_path.toString())

    part_files = [
        status.getPath()
        for status in filesystem.listStatus(staging_path)
        if status.getPath().getName().startswith("part-")
    ]
    if len(part_files) != 1:
        raise RuntimeError(
            f"expected exactly one part file under {staging_path}, found {len(part_files)}"
        )

    final_path = Path(target)
    if filesystem.exists(final_path):
        filesystem.delete(final_path, False)
    filesystem.rename(part_files[0], final_path)
    filesystem.delete(staging_path, True)

    # Hadoop's local filesystem writes a checksum sidecar next to each file and
    # renames it along with the part file. Volumes and object stores do not, so
    # this only bites when running against a local path -- drop it either way so
    # the landing directory holds just the delivered file.
    checksum_path = Path(final_path.getParent(), f".{final_path.getName()}.crc")
    if filesystem.exists(checksum_path):
        filesystem.delete(checksum_path, False)


def write_entity(spark, entity: str, rows: list[dict], target: str) -> None:
    spec = schemas.ENTITIES[entity]
    columns = schemas.column_names(entity)
    ordered = [{column: row.get(column) for column in columns} for row in rows]
    dataframe = spark.createDataFrame(ordered, schema=schemas.spark_schema(entity))

    if spec["format"] == "csv":
        options = {
            "header": "true",
            "timestampFormat": schemas.TIMESTAMP_FORMAT_JAVA,
            "dateFormat": schemas.DATE_FORMAT_JAVA,
        }
    elif spec["format"] == "json":
        # Spark drops null fields from JSON output by default; keeping them
        # makes the delivered schema stable across loads, which is what
        # Bronze schema handling is being tested against.
        options = {
            "ignoreNullFields": "false",
            "timestampFormat": schemas.TIMESTAMP_FORMAT_JAVA,
            "dateFormat": schemas.DATE_FORMAT_JAVA,
        }
    else:
        options = {"compression": "snappy"}

    _write_single_file(dataframe, target, spec["format"], options)
