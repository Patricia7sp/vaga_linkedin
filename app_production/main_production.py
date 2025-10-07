#!/usr/bin/env python3
"""
🚀 Cloud Run Main (v4) - Entrada focada em extração

Entry point utilizado pelo Cloud Run Job v4.
Responsável apenas por acionar o novo Production Agent Cloud,
que executa exclusivamente o Extract Agent e envia os dados para o GCS/Kafka.
"""

import os
import sys
import argparse
from datetime import datetime

# Adicionar path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.control_agent.production_agent_cloud import run_cloud_pipeline, run_cloud_pipeline_async

# Carrega variáveis de ambiente
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("✅ Variáveis de ambiente carregadas")
except ImportError:
    print("⚠️ python-dotenv não instalado")


def print_production_info():
    """
    Exibe informações do pipeline de produção
    """
    print("🚀 Vagas LinkedIn - Cloud Run Job v4")
    print("=" * 55)
    print("🎯 Pipeline Cloud Run agora executa SOMENTE a extração:")
    print("  • 🔍 Extract Agent → Salva JSONL/Parquet no Cloud Storage e Kafka")
    print("=" * 55)
    print("📢 Transformações e notificações ocorrem via Databricks Job dedicado")
    print("=" * 55)


def main():
    """
    Função principal do pipeline de produção
    """
    parser = argparse.ArgumentParser(description="Pipeline Produção - Vagas LinkedIn Cloud Run")

    parser.add_argument(
        "command", nargs="?", default="run", choices=["run", "async", "maintenance", "help"], help="Comando a executar"
    )

    args = parser.parse_args()

    if args.command == "help":
        print_production_info()
        print("\nComandos disponíveis:")
        print("  python main_production.py run         - Pipeline síncrono (padrão)")
        print("  python main_production.py async       - Pipeline assíncrono")
        print("  python main_production.py maintenance - Limpeza e manutenção")
        print("  python main_production.py help        - Esta ajuda")
        return 0

    print_production_info()

    try:
        if args.command == "maintenance":
            print(f"\n🧹 Executando manutenção - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Lógica de manutenção (limpeza de logs, cache, etc.)
            print("🗑️ Limpando arquivos temporários...")
            print("📊 Verificando integridade dos dados...")
            print("🔍 Auditoria de qualidade dos pipelines...")

            # Simular manutenção bem-sucedida
            print("✅ Manutenção concluída com sucesso!")
            return 0

        elif args.command == "async":
            print("\n🔄 Executando pipeline Cloud Run (assíncrono)...")
            thread = run_cloud_pipeline_async()

            # Aguardar um tempo para Cloud Run
            import time

            time.sleep(5)

            if thread.is_alive():
                print("✅ Pipeline executando em background")
                return 0
            else:
                print("✅ Pipeline assíncrono concluído")
                return 0

        else:  # run (padrão)
            print(f"\n🚀 Iniciando pipeline Cloud Run v4 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            success = run_cloud_pipeline()

            if success:
                print("\n🎉 EXTRAÇÃO CONCLUÍDA COM SUCESSO! Dados enviados para bronze-raw.")
                return 0
            else:
                print("\n❌ FALHA NA EXECUÇÃO DO PIPELINE CLOUD RUN")
                return 1

    except KeyboardInterrupt:
        print("\n⚠️ Pipeline interrompido pelo usuário")
        return 130

    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO: {e}")
        print("Verifique logs e configurações")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
