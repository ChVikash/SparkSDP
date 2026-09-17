"""Single source of truth for the source-file schemas.

Column order, types, delivery format and filename are declared once here and
translated for whichever writer backend is in use, so the local and Spark
backends cannot drift apart.

Type vocabulary: string, int, double, boolean, date, timestamp, array<string>.
"""

ENTITIES: dict[str, dict] = {
    "patients": {
        "filename": "patients.csv",
        "format": "csv",
        "columns": [
            ("patient_id", "string"),
            ("facility_id", "string"),
            ("first_name", "string"),
            ("last_name", "string"),
            ("date_of_birth", "date"),
            ("gender", "string"),
            ("phone", "string"),
            ("email", "string"),
            ("address_line1", "string"),
            ("city", "string"),
            ("state", "string"),
            ("postal_code", "string"),
            ("insurance_provider", "string"),
            ("insurance_member_id", "string"),
            ("registration_date", "date"),
            ("created_at", "timestamp"),
            ("updated_at", "timestamp"),
        ],
    },
    "providers": {
        "filename": "providers.json",
        "format": "json",
        "columns": [
            ("provider_id", "string"),
            ("npi", "string"),
            ("first_name", "string"),
            ("last_name", "string"),
            ("specialty", "string"),
            ("credential", "string"),
            ("email", "string"),
            ("phone", "string"),
            ("facility_ids", "array<string>"),
            ("is_active", "boolean"),
            ("created_at", "timestamp"),
            ("updated_at", "timestamp"),
        ],
    },
    "facilities": {
        "filename": "facilities.json",
        "format": "json",
        "columns": [
            ("facility_id", "string"),
            ("facility_name", "string"),
            ("facility_type", "string"),
            ("address_line1", "string"),
            ("city", "string"),
            ("state", "string"),
            ("postal_code", "string"),
            ("phone", "string"),
            ("opened_date", "date"),
            ("created_at", "timestamp"),
            ("updated_at", "timestamp"),
        ],
    },
    "encounters": {
        "filename": "encounters.json",
        "format": "json",
        "columns": [
            ("encounter_id", "string"),
            ("facility_id", "string"),
            ("patient_id", "string"),
            ("provider_id", "string"),
            ("encounter_type", "string"),
            ("encounter_status", "string"),
            ("department", "string"),
            ("admission_timestamp", "timestamp"),
            ("discharge_timestamp", "timestamp"),
            ("primary_diagnosis_code", "string"),
            ("primary_diagnosis_desc", "string"),
            ("created_at", "timestamp"),
            ("updated_at", "timestamp"),
        ],
    },
    "lab_results": {
        "filename": "lab_results.parquet",
        "format": "parquet",
        "columns": [
            ("lab_result_id", "string"),
            ("encounter_id", "string"),
            ("facility_id", "string"),
            ("patient_id", "string"),
            ("test_code", "string"),
            ("test_name", "string"),
            ("result_value", "double"),
            ("result_unit", "string"),
            ("reference_range_low", "double"),
            ("reference_range_high", "double"),
            ("abnormal_flag", "string"),
            ("specimen_collected_at", "timestamp"),
            ("result_reported_at", "timestamp"),
            ("result_version", "int"),
            ("created_at", "timestamp"),
            ("updated_at", "timestamp"),
        ],
    },
    "prescriptions": {
        "filename": "prescriptions.csv",
        "format": "csv",
        "columns": [
            ("prescription_id", "string"),
            ("encounter_id", "string"),
            ("facility_id", "string"),
            ("patient_id", "string"),
            ("provider_id", "string"),
            ("medication_code", "string"),
            ("medication_name", "string"),
            ("dosage", "string"),
            ("frequency", "string"),
            ("duration_days", "int"),
            ("quantity", "int"),
            ("prescription_status", "string"),
            ("prescribed_date", "date"),
            ("filled_date", "date"),
            ("created_at", "timestamp"),
            ("updated_at", "timestamp"),
        ],
    },
    "claims": {
        "filename": "claims.json",
        "format": "json",
        "columns": [
            ("claim_id", "string"),
            ("encounter_id", "string"),
            ("facility_id", "string"),
            ("patient_id", "string"),
            ("service_category", "string"),
            ("insurance_provider", "string"),
            ("insurance_member_id", "string"),
            ("billed_amount", "double"),
            ("allowed_amount", "double"),
            ("paid_amount", "double"),
            ("claim_status", "string"),
            ("denial_reason", "string"),
            ("submitted_date", "date"),
            ("status_updated_date", "date"),
            ("created_at", "timestamp"),
            ("updated_at", "timestamp"),
        ],
    },
}

# Applied by both backends so the CSV and JSON deliveries are byte-identical
# whichever one produced them. Parquet carries its types natively, so the two
# differ only in timestamp precision (pyarrow micros, Spark nanos).
TIMESTAMP_FORMAT_JAVA = "yyyy-MM-dd'T'HH:mm:ss"
DATE_FORMAT_JAVA = "yyyy-MM-dd"


def column_names(entity: str) -> list[str]:
    return [name for name, _ in ENTITIES[entity]["columns"]]


def pyarrow_schema(entity: str):
    import pyarrow as pa

    mapping = {
        "string": pa.string(),
        "int": pa.int32(),
        "double": pa.float64(),
        "boolean": pa.bool_(),
        "date": pa.date32(),
        "timestamp": pa.timestamp("us"),
        "array<string>": pa.list_(pa.string()),
    }
    return pa.schema(
        [(name, mapping[kind]) for name, kind in ENTITIES[entity]["columns"]]
    )


def spark_schema(entity: str):
    from pyspark.sql import types as T

    mapping = {
        "string": T.StringType(),
        "int": T.IntegerType(),
        "double": T.DoubleType(),
        "boolean": T.BooleanType(),
        "date": T.DateType(),
        "timestamp": T.TimestampType(),
        "array<string>": T.ArrayType(T.StringType()),
    }
    return T.StructType(
        [
            T.StructField(name, mapping[kind], nullable=True)
            for name, kind in ENTITIES[entity]["columns"]
        ]
    )
