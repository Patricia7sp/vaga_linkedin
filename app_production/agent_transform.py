#!/usr/bin/env python3
"""
Databricks Job Entry Point: executa transformações e notificações.

Este script é pensado para rodar como tarefa (Python Script) em um job 
no Databricks, acionando os pipelines DLT (Bronze → Silver → Gold) e, em
seguida, o Agent Chat para avisar sobre vagas novas.
"""

import os
import sys
from datetime import datetime

# Garantir acesso aos módulos do projeto
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from agents.control_agent.production_agent_databricks import run_databricks_pipeline
try:
    from agents.agent_chat.agent_chat import AgentChat
    AGENT_CHAT_AVAILABLE = True
except ImportError:
    AGENT_CHAT_AVAILABLE = False


def run_bronze():
    """Entry point para tarefa Bronze do job Databricks"""
    print("🥉 Executando transformação Bronze...")
    # Este será substituído por chamada específica do pipeline Bronze
    return run_databricks_pipeline(stage="bronze")


def run_silver():
    """Entry point para tarefa Silver do job Databricks"""
    print("🥈 Executando transformação Silver...")
    # Este será substituído por chamada específica do pipeline Silver
    return run_databricks_pipeline(stage="silver")


def run_gold():
    """Entry point para tarefa Gold do job Databricks"""
    print("🥇 Executando transformação Gold...")
    # Este será substituído por chamada específica do pipeline Gold
    return run_databricks_pipeline(stage="gold")


def run_agent_chat():
    """Entry point para notificações Telegram via Agent Chat"""
    print("📱 Executando Agent Chat (notificações)...")
    if not AGENT_CHAT_AVAILABLE:
        print("⚠️ Agent Chat não disponível. Pulando notificações.")
        return True
    
    try:
        chat_agent = AgentChat()
        return chat_agent.send_pipeline_summary()
    except Exception as e:
        print(f"❌ Erro no Agent Chat: {e}")
        return False


def main() -> None:
    """Execução completa de todos os estágios (para teste local)"""
    start_ts = datetime.now()
    print("🚀 Iniciando Databricks Agent Transform...")
    print(f"🕒 Horário inicial: {start_ts.isoformat()}")

    success = run_databricks_pipeline()

    end_ts = datetime.now()
    duration = (end_ts - start_ts).total_seconds()

    print("=" * 70)
    print(f"🏁 Execução concluída às {end_ts.isoformat()}")
    print(f"⏱️ Duração total: {duration:.2f}s")

    if success:
        print("🎉 Transformações e notificações concluídas com sucesso!")
    else:
        print("❌ Falha na execução do pipeline Databricks. Verifique os logs.")


if __name__ == "__main__":
    main()
