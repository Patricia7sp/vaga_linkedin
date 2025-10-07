# Databricks notebook source
import dlt
from pyspark.sql.functions import (
    col,
    current_timestamp,
    regexp_extract,
    to_timestamp,
    trim,
    lower,
    regexp_replace,
    split,
    expr,
    regexp_replace as re_replace,
    lit,
    input_file_name,
    when,
    coalesce,
)
from pyspark.sql.types import *

# =========================
# Configurações de entrada
# =========================
# Volume UC com JSONs organizados por dia: /YYYY-MM-DD/digital_analytics_*.json|jsonl
VOLUME_ROOT = "/Volumes/vagas_linkedin/digital_analytics_raw/linkedin_data_volume"
# Schema location para Auto Loader
SCHEMA_LOC = "/Volumes/vagas_linkedin/digital_analytics_raw/linkedin_data_volume/_schemas/bronze_linkedin_v10"

# =========================
# Schema raw (bronze)
# =========================
bronze_schema = StructType(
    [
        StructField("job_id", StringType(), True),
        StructField("title", StringType(), True),
        StructField("company", StringType(), True),
        StructField("location", StringType(), True),
        StructField("description", StringType(), True),
        StructField("description_snippet", StringType(), True),
        StructField("description_length", LongType(), True),
        StructField("url", StringType(), True),
        StructField("posted_time", StringType(), True),
        StructField("extract_timestamp", StringType(), True),
        StructField("source", StringType(), True),
        StructField("search_term", StringType(), True),
        StructField("category", StringType(), True),
        StructField("location_country", StringType(), True),
        StructField("has_company", BooleanType(), True),
        StructField("salary_min", StringType(), True),
        StructField("salary_max", StringType(), True),
        StructField("has_salary", BooleanType(), True),
        StructField("work_modality", StringType(), True),
        StructField("contract_type", StringType(), True),
    ]
)


# =========================
# BRONZE - Uma tabela por data de extração
# =========================
@dlt.table(
    name="digital_analytics_bronze",
    comment="Bronze — Uma tabela por data de extração (não unifica ainda)",
    table_properties={
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact": "true",
        "quality": "bronze",
    },
)
def bronze_digital_analytics():
    """
    Camada Bronze: Reproduz dados raw sem unificação
    Particiona por data de extração para criar "tabelas virtuais" por data
    """
    df = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.includeExistingFiles", "true")
        .option("cloudFiles.schemaLocation", SCHEMA_LOC)
        .option("cloudFiles.maxFilesPerTrigger", "1000")
        .option("rescuedDataColumn", "_rescued_data")
        .schema(bronze_schema)
        .load(VOLUME_ROOT)
        .where(col("_metadata.file_name").rlike("(?i)^digital_analytics_.*\\.json(l)?$"))
        .withColumn("ingestion_timestamp", current_timestamp())
        .withColumn("source_file", col("_metadata.file_path"))
        .withColumn(
            "extract_date",
            expr(
                """
                  coalesce(
                    regexp_extract(_metadata.file_path, '.*/([0-9]{4}-[0-9]{2}-[0-9]{2})/.*', 1),
                    regexp_extract(_metadata.file_name, '.*([0-9]{4}-[0-9]{2}-[0-9]{2}).*', 1),
                    regexp_extract(_metadata.file_path, '.*([0-9]{4}-[0-9]{2}-[0-9]{2}).*', 1)
                  )
                """
            ).cast("string"),
        )
    )

    # Garantir existência da coluna _rescued_data
    if "_rescued_data" not in df.columns:
        df = df.withColumn("_rescued_data", lit(None).cast("map<string,string>"))

    return df


# =========================
# SILVER-STG - Unificação dos dados bronze
# =========================
def to_double_safe(c):
    """Remove caracteres não numéricos e converte para double"""
    return re_replace(c, r"[^0-9\.\-]", "").cast("double")


@dlt.table(
    name="digital_analytics_silver_stg",
    comment="Silver STG — Unificação e normalização dos dados bronze",
    table_properties={
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact": "true",
        "quality": "silver_stg",
    },
)
@dlt.expect("job_id_not_null", "job_id IS NOT NULL")
@dlt.expect("title_not_null", "title IS NOT NULL")
@dlt.expect("company_not_null", "company IS NOT NULL")
@dlt.expect("location_not_null", "location IS NOT NULL")
def silver_stg_digital_analytics():
    """
    Camada Silver-STG: Unifica TODAS as tabelas bronze em uma única tabela
    Aplica normalização e limpeza básica dos dados
    """
    return (
        dlt.read_stream("digital_analytics_bronze")
        .withWatermark("ingestion_timestamp", "2 days")
        # Normalização de texto
        .withColumn("title", lower(trim(regexp_replace(col("title"), r"\s+", " "))))
        .withColumn("company", lower(trim(regexp_replace(col("company"), r"\s+", " "))))
        .withColumn("location", lower(trim(regexp_replace(col("location"), r"\s+", " "))))
        .withColumn("location_country", lower(trim(col("location_country"))))
        # Tipagem de timestamps
        .withColumn("posted_time_ts", to_timestamp(col("posted_time")))
        .withColumn("extract_ts", to_timestamp(col("extract_timestamp")))
        # Tipagem de salários (STRING → DOUBLE)
        .withColumn("salary_min", to_double_safe(col("salary_min")))
        .withColumn("salary_max", to_double_safe(col("salary_max")))
        # Adicionar flag de processamento
        .withColumn("processed_timestamp", current_timestamp())
        .select(
            "job_id",
            "title",
            "company",
            "location",
            "description",
            "description_snippet",
            "description_length",
            "url",
            "posted_time",
            "posted_time_ts",
            "extract_timestamp",
            "extract_ts",
            "source",
            "search_term",
            "category",
            "location_country",
            "has_company",
            "salary_min",
            "salary_max",
            "has_salary",
            "work_modality",
            "contract_type",
            "extract_date",
            "ingestion_timestamp",
            "processed_timestamp",
            "source_file",
            "_rescued_data",
        )
    )


# =========================
# SILVER-MD - Modelagem após transformações
# =========================
@dlt.table(
    name="digital_analytics_silver_md",
    comment="Silver MD — Modelagem final após transformações e regras de negócio",
    table_properties={
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact": "true",
        "quality": "silver_md",
    },
)
@dlt.expect("unique_job_id", "job_id IS NOT NULL")
@dlt.expect("valid_location", "location IS NOT NULL AND length(location) > 2")
def silver_md_digital_analytics():
    """
    Camada Silver-MD: Modelagem final com regras de negócio
    Deduplicação, parsing de localização, flags de qualidade
    """
    return (
        dlt.read_stream("digital_analytics_silver_stg")
        .withWatermark("processed_timestamp", "2 days")
        # Parsing de localização
        .withColumn("loc_left", trim(split(col("location"), "-").getItem(0)))  # cidade
        .withColumn("loc_right", trim(split(col("location"), "-").getItem(1)))  # "UF, país"
        .withColumn("city", col("loc_left"))
        .withColumn("state", trim(split(col("loc_right"), ",").getItem(0)))
        .withColumn("country", trim(split(col("loc_right"), ",").getItem(1)))
        .withColumn("country", coalesce(col("country"), col("location_country")))
        # Flags de qualidade e negócio
        .withColumn("has_salary_info", expr("coalesce(has_salary, salary_min IS NOT NULL OR salary_max IS NOT NULL)"))
        .withColumn(
            "salary_range",
            when(
                col("salary_max").isNotNull() & col("salary_min").isNotNull(), col("salary_max") - col("salary_min")
            ).otherwise(lit(None)),
        )
        .withColumn(
            "description_quality_score",
            when(col("description_length") > 500, lit("high"))
            .when(col("description_length") > 200, lit("medium"))
            .otherwise(lit("low")),
        )
        # Deduplicação final
        .dropDuplicates(["job_id"])
        .select(
            "job_id",
            "title",
            "company",
            "city",
            "state",
            "country",
            "location",
            "location_country",
            "category",
            "search_term",
            "work_modality",
            "contract_type",
            "salary_min",
            "salary_max",
            "salary_range",
            "has_salary",
            "has_salary_info",
            "posted_time",
            "posted_time_ts",
            "extract_timestamp",
            "extract_ts",
            "description",
            "description_snippet",
            "description_length",
            "description_quality_score",
            "url",
            "extract_date",
            "ingestion_timestamp",
            "processed_timestamp",
            "source_file",
        )
    )


# =========================
# GOLD - Camada final para consumo
# =========================
@dlt.table(
    name="digital_analytics_gold",
    comment="Gold — Controle de visões e métricas para demanda de negócio",
    table_properties={
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact": "true",
        "quality": "gold",
    },
)
@dlt.expect("has_job_id", "job_id IS NOT NULL")
@dlt.expect("has_ingestion_ts", "ingestion_timestamp IS NOT NULL")
def gold_digital_analytics():
    """
    Camada Gold: Visões e métricas finais para consumo de negócio
    """
    return (
        dlt.read_stream("digital_analytics_silver_md")
        .withWatermark("processed_timestamp", "2 days")
        # Métricas de negócio
        .withColumn("is_recent_posting", expr("datediff(current_date(), to_date(posted_time_ts)) <= 30"))
        .withColumn("is_premium_salary", when(col("salary_min") > 8000, lit(True)).otherwise(lit(False)))
        .withColumn(
            "location_tier",
            when(col("city").isin("são paulo", "rio de janeiro", "belo horizonte"), lit("tier_1"))
            .when(col("city").isin("brasília", "curitiba", "porto alegre"), lit("tier_2"))
            .otherwise(lit("tier_3")),
        )
        # Seleção final para consumo
        .select(
            "job_id",
            "title",
            "company",
            "city",
            "state",
            "country",
            "location_tier",
            "category",
            "search_term",
            "work_modality",
            "contract_type",
            "salary_min",
            "salary_max",
            "salary_range",
            "has_salary_info",
            "is_premium_salary",
            "posted_time_ts",
            "is_recent_posting",
            "description_quality_score",
            "url",
            "ingestion_timestamp",
        )
    )
