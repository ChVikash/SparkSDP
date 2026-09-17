# Databricks notebook source
# MAGIC %md
# MAGIC # Generate simulated source files into the landing Volume
# MAGIC
# MAGIC Runs the generator from `tools/data_generator` against the active Spark
# MAGIC session, writing one load's files into the Unity Catalog Volume that
# MAGIC stands in for source-system file delivery
# MAGIC (`phase3_architecture.md` sections 1 and 3).
# MAGIC
# MAGIC Works as an interactive notebook or as a Lakeflow Job task. The same
# MAGIC generator runs outside Databricks via
# MAGIC `python3 tools/generate_source_data.py`.

# COMMAND ----------

import os
import random
import sys

# Databricks sets the working directory to the notebook's own folder in a Git
# folder; both candidates are added so this also works when the job's working
# directory is the repository root.
for candidate in (os.getcwd(), os.path.join(os.getcwd(), "tools")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from data_generator import schemas, spark_writers
from generate_source_data import build_load

# COMMAND ----------

dbutils.widgets.text("catalog", "medicore_dev", "Catalog")
dbutils.widgets.text("schema", "landing", "Landing schema")
dbutils.widgets.text("volume", "source_files", "Landing volume")
dbutils.widgets.text("load", "1", "Load number")
dbutils.widgets.text("seed", "42", "Random seed")
dbutils.widgets.text("patients", "2000", "Patient count")
dbutils.widgets.text("providers", "120", "Provider count")
dbutils.widgets.text("encounters", "10000", "Encounter count")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
volume = dbutils.widgets.get("volume")
load = int(dbutils.widgets.get("load"))
seed = int(dbutils.widgets.get("seed"))

out_dir = f"/Volumes/{catalog}/{schema}/{volume}"

# COMMAND ----------

# Convenience for bootstrapping an empty workspace. Once the asset bundle is in
# place it owns these objects and this cell becomes redundant.
spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog}.{schema}.{volume}")

# COMMAND ----------

data = build_load(
    load,
    random.Random(seed),
    int(dbutils.widgets.get("patients")),
    int(dbutils.widgets.get("providers")),
    int(dbutils.widgets.get("encounters")),
)

for entity, rows in data.items():
    target = f"{out_dir}/{entity}/load_{load}/{schemas.ENTITIES[entity]['filename']}"
    spark_writers.write_entity(spark, entity, rows, target)
    print(f"{entity:<15} {len(rows):>7,} rows  ->  {target}")

# COMMAND ----------

display(dbutils.fs.ls(f"{out_dir}/patients/load_{load}"))
