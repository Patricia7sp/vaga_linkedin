#!/usr/bin/env python3
"""
Viz Agent: Generates dashboards for data visualization.
"""

import glob
import os
import subprocess
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def run_viz(instructions=None):
    """
    Generate visualizations from transformed data.
    Real implementation for production use.
    """
    print("🚀 Gerando visualizações e dashboards...")

    try:
        data_dir = os.path.join(os.path.dirname(__file__), "../../data")

        # Find the most recent transformed files
        vagas_files = glob.glob(os.path.join(data_dir, "vagas_transformado_*.parquet"))
        skills_files = glob.glob(os.path.join(data_dir, "skills_transformado_*.parquet"))
        empresas_files = glob.glob(os.path.join(data_dir, "empresas_transformado_*.parquet"))

        if not vagas_files:
            # Fallback to old format
            vagas_files = glob.glob(os.path.join(data_dir, "vagas_transformado.parquet"))

        if not vagas_files:
            error_msg = "❌ Nenhum arquivo de dados transformados encontrado. Execute a transformação primeiro."
            print(error_msg)
            return error_msg

        # Get the most recent files
        latest_vagas = max(vagas_files, key=os.path.getctime)
        print(f"📂 Carregando dados de vagas: {latest_vagas}")

        # Load main data
        df_vagas = pd.read_parquet(latest_vagas)
        print(f"✅ Dados de vagas carregados: {len(df_vagas)} registros.")

        # Load additional tables if available
        df_skills = None
        df_empresas = None

        if skills_files:
            latest_skills = max(skills_files, key=os.path.getctime)
            df_skills = pd.read_parquet(latest_skills)
            print(f"✅ Dados de skills carregados: {len(df_skills)} registros.")

        if empresas_files:
            latest_empresas = max(empresas_files, key=os.path.getctime)
            df_empresas = pd.read_parquet(latest_empresas)
            print(f"✅ Dados de empresas carregados: {len(df_empresas)} registros.")

        # Set style for better plots
        plt.style.use("seaborn-v0_8")
        sns.set_palette("husl")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        viz_dir = os.path.join(data_dir, f"visualizations_{timestamp}")
        os.makedirs(viz_dir, exist_ok=True)

        print("📊 Gerando visualizações...")

        # 1. Vagas por cidade
        if "cidade" in df_vagas.columns:
            plt.figure(figsize=(12, 6))
            df_vagas["cidade"].value_counts().head(10).plot(kind="bar")
            plt.title("Top 10 Cidades com Mais Vagas")
            plt.xlabel("Cidade")
            plt.ylabel("Número de Vagas")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(os.path.join(viz_dir, "vagas_por_cidade.png"), dpi=300, bbox_inches="tight")
            plt.close()
            print("✅ Gráfico de vagas por cidade criado")

        # 2. Vagas por nível de experiência
        if "nivel_experiencia" in df_vagas.columns:
            plt.figure(figsize=(10, 6))
            df_vagas["nivel_experiencia"].value_counts().plot(kind="pie", autopct="%1.1f%%")
            plt.title("Distribuição por Nível de Experiência")
            plt.ylabel("")
            plt.savefig(os.path.join(viz_dir, "nivel_experiencia.png"), dpi=300, bbox_inches="tight")
            plt.close()
            print("✅ Gráfico de nível de experiência criado")

        # 3. Top empresas por número de vagas
        plt.figure(figsize=(12, 8))
        df_vagas["company"].value_counts().head(15).plot(kind="barh")
        plt.title("Top 15 Empresas com Mais Vagas")
        plt.xlabel("Número de Vagas")
        plt.ylabel("Empresa")
        plt.tight_layout()
        plt.savefig(os.path.join(viz_dir, "top_empresas.png"), dpi=300, bbox_inches="tight")
        plt.close()
        print("✅ Gráfico de top empresas criado")

        # 4. Skills mais demandadas (se disponível)
        if df_skills is not None:
            plt.figure(figsize=(12, 8))
            df_skills["skill"].value_counts().head(15).plot(kind="barh")
            plt.title("Top 15 Skills Mais Demandadas")
            plt.xlabel("Número de Vagas")
            plt.ylabel("Skill")
            plt.tight_layout()
            plt.savefig(os.path.join(viz_dir, "top_skills.png"), dpi=300, bbox_inches="tight")
            plt.close()
            print("✅ Gráfico de top skills criado")

        # 5. Distribuição salarial (se disponível)
        if "salario_min" in df_vagas.columns and not df_vagas["salario_min"].isna().all():
            plt.figure(figsize=(12, 6))
            df_salario = df_vagas.dropna(subset=["salario_min", "salario_max"])
            if len(df_salario) > 0:
                plt.hist(df_salario["salario_min"], bins=20, alpha=0.7, label="Salário Mínimo")
                plt.hist(df_salario["salario_max"], bins=20, alpha=0.7, label="Salário Máximo")
                plt.title("Distribuição Salarial")
                plt.xlabel("Salário (R$)")
                plt.ylabel("Frequência")
                plt.legend()
                plt.tight_layout()
                plt.savefig(os.path.join(viz_dir, "distribuicao_salarial.png"), dpi=300, bbox_inches="tight")
                plt.close()
                print("✅ Gráfico de distribuição salarial criado")

        # 6. Tecnologia principal
        if "tecnologia_principal" in df_vagas.columns:
            plt.figure(figsize=(10, 8))
            tech_counts = df_vagas["tecnologia_principal"].value_counts().head(10)
            tech_counts.plot(kind="barh")
            plt.title("Top 10 Tecnologias Principais")
            plt.xlabel("Número de Vagas")
            plt.ylabel("Tecnologia")
            plt.tight_layout()
            plt.savefig(os.path.join(viz_dir, "tecnologias_principais.png"), dpi=300, bbox_inches="tight")
            plt.close()
            print("✅ Gráfico de tecnologias principais criado")

        # Create a summary report
        report_file = os.path.join(viz_dir, "dashboard_report.txt")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(f"Dashboard Report - {timestamp}\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Total de vagas analisadas: {len(df_vagas)}\n")
            f.write(f"Empresas únicas: {df_vagas['company'].nunique()}\n")
            if "cidade" in df_vagas.columns:
                f.write(f"Cidades únicas: {df_vagas['cidade'].nunique()}\n")
            if df_skills is not None:
                f.write(f"Skills únicas: {df_skills['skill'].nunique()}\n")
            f.write(f"\nVisualizações geradas em: {viz_dir}\n")

        print(f"✅ Relatório salvo: {report_file}")

        # Try uploading to GCP if available
        print("☁️  Tentando upload para GCP Storage...")
        try:
            result = subprocess.run(["gsutil", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                bucket_name = "linkedin-dados-processados"
                gcp_viz_path = f"gs://{bucket_name}/visualizations/{timestamp}/"
                subprocess.run(["gsutil", "-m", "cp", "-r", viz_dir, gcp_viz_path], check=True)
                print(f"✅ Visualizações enviadas para GCP: {gcp_viz_path}")
            else:
                print("ℹ️  gsutil não disponível - visualizações salvas apenas localmente")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Erro no upload para GCP: {e}")

        return f"Dashboard gerado com sucesso! Visualizações salvas em: {viz_dir}"

    except Exception as e:
        error_msg = f"Erro na geração de visualizações: {e}"
        print(f"❌ {error_msg}")
        return error_msg


if __name__ == "__main__":
    run_viz()
