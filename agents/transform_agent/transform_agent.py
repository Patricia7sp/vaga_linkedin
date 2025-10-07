#!/usr/bin/env python3
"""
Transform Agent: Transforms and cleans data in Databricks.
"""

import glob
import os
import subprocess
from datetime import datetime

import pandas as pd


def run_transform(instructions=None):
    """
    Transform data: clean, create derived columns, separate tables.
    Real implementation for production use.
    """
    print("🚀 Iniciando transformação dos dados...")

    try:
        data_dir = os.path.join(os.path.dirname(__file__), "../../data")

        # Find the most recent parquet file from load stage
        parquet_files = glob.glob(os.path.join(data_dir, "vagas_databricks_*.parquet"))
        if not parquet_files:
            # Fallback to old format
            parquet_files = glob.glob(os.path.join(data_dir, "vagas_databricks.parquet"))

        if not parquet_files:
            error_msg = "❌ Nenhum arquivo de dados encontrado. Execute o carregamento primeiro."
            print(error_msg)
            return error_msg

        # Get the most recent file
        latest_file = max(parquet_files, key=os.path.getctime)
        print(f"📂 Carregando arquivo: {latest_file}")

        # Load data
        df = pd.read_parquet(latest_file)
        print(f"✅ Dados carregados: {len(df)} registros.")

        # Data cleaning and transformations
        print("🔧 Aplicando transformações...")

        # Extract primary technology from skills
        df["tecnologia_principal"] = df["skills"].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "N/A")

        # Extract salary numbers
        df["salario_min"] = (
            df["salary_range"]
            .str.extract(r"R\$ ([\d,]+)")
            .iloc[:, 0]
            .str.replace(",", "")
            .astype(float, errors="ignore")
        )
        df["salario_max"] = (
            df["salary_range"]
            .str.extract(r"- R\$ ([\d,]+)")
            .iloc[:, 0]
            .str.replace(",", "")
            .astype(float, errors="ignore")
        )

        # Create experience level from title
        df["nivel_experiencia"] = df["title"].apply(
            lambda x: (
                "Senior"
                if "Sênior" in x or "Senior" in x
                else "Pleno" if "Pleno" in x else "Junior" if "Junior" in x or "Jr" in x else "Não especificado"
            )
        )

        # Extract state from location
        df["estado"] = df["location"].str.extract(r", ([A-Z]{2})$").iloc[:, 0]
        df["cidade"] = df["location"].str.replace(r", [A-Z]{2}$", "", regex=True)

        # Clean data
        df_clean = df.dropna(subset=["title", "company"])
        print(f"✅ Limpeza concluída: {len(df_clean)} registros válidos.")

        # Create separate tables
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Main jobs table
        jobs_table = df_clean[
            [
                "id",
                "title",
                "company",
                "cidade",
                "estado",
                "posted_date",
                "description",
                "salary_range",
                "salario_min",
                "salario_max",
                "nivel_experiencia",
                "tecnologia_principal",
            ]
        ]
        jobs_file = os.path.join(data_dir, f"vagas_transformado_{timestamp}.parquet")
        jobs_table.to_parquet(jobs_file, index=False)
        print(f"✅ Tabela de vagas salva: {jobs_file}")

        # Skills table (normalized)
        skills_data = []
        for _, row in df_clean.iterrows():
            if isinstance(row["skills"], list):
                for skill in row["skills"]:
                    skills_data.append({"job_id": row["id"], "skill": skill})

        skills_df = pd.DataFrame(skills_data)
        skills_file = os.path.join(data_dir, f"skills_transformado_{timestamp}.parquet")
        skills_df.to_parquet(skills_file, index=False)
        print(f"✅ Tabela de skills salva: {skills_file}")

        # Companies summary
        companies_df = (
            df_clean.groupby("company")
            .agg({"id": "count", "salario_min": "mean", "salario_max": "mean"})
            .rename(columns={"id": "total_vagas"})
            .reset_index()
        )
        companies_file = os.path.join(data_dir, f"empresas_transformado_{timestamp}.parquet")
        companies_df.to_parquet(companies_file, index=False)
        print(f"✅ Tabela de empresas salva: {companies_file}")

        # Try uploading to GCP if available
        print("☁️  Tentando upload para GCP Storage...")
        try:
            result = subprocess.run(["gsutil", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                bucket_name = "linkedin-dados-processados"
                for file_path, table_name in [
                    (jobs_file, "vagas"),
                    (skills_file, "skills"),
                    (companies_file, "empresas"),
                ]:
                    gcp_path = f"gs://{bucket_name}/transformed_data/{timestamp}/{table_name}.parquet"
                    subprocess.run(["gsutil", "cp", file_path, gcp_path], check=True)
                    print(f"✅ {table_name} enviada para GCP: {gcp_path}")
            else:
                print("ℹ️  gsutil não disponível - dados salvos apenas localmente")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Erro no upload para GCP: {e}")

        return f"Transformação concluída: {len(df_clean)} registros processados em 3 tabelas: vagas, skills e empresas"

    except Exception as e:
        error_msg = f"Erro na transformação: {e}"
        print(f"❌ {error_msg}")
        return error_msg


if __name__ == "__main__":
    run_transform()
