# Databricks notebook source
# MAGIC %md
# MAGIC # Generate simulated source files into the landing Volume
# MAGIC
# MAGIC Runs the generator from `tools/data_generator`, writing one load's files
# MAGIC into the Unity Catalog Volume that stands in for source-system file
# MAGIC delivery (`phase3_architecture.md` sections 1 and 3).
# MAGIC
# MAGIC Writing is driver-side pandas, so each entity lands as a single properly
# MAGIC named file and nothing here needs a SparkContext -- it runs on
# MAGIC serverless, dedicated and standard access mode alike. The same generator
# MAGIC runs outside Databricks via `python3 tools/generate_source_data.py`.

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

from generate_source_data import build_load, write_load

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

for entity, count, target in write_load(data, out_dir, load):
    print(f"{entity:<15} {count:>7,} rows  ->  {target}")

# COMMAND ----------

display(dbutils.fs.ls(f"{out_dir}/patients/load_{load}"))
