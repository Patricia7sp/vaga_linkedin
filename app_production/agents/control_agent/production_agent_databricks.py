#!/usr/bin/env python3
"""
🚀 Production Agent (Databricks) - Transformação + Agent Chat

Orquestra a execução dos pipelines DLT e do Agent Chat dentro de Databricks.
"""

import os
import sys
from datetime import datetime
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from agents.transform_agent.transform_agent import TransformAgent

try:
    from agent_chat import AgentChat

    AGENT_CHAT_AVAILABLE = True
except ImportError:
    AGENT_CHAT_AVAILABLE = False


def run_transform_only(instructions: Optional[str] = None) -> str:
    agent = TransformAgent()
    execution_result = agent.run_dlt_pipelines_execution()
    status = execution_result.get("status", "unknown")
    success_count = execution_result.get("success_count", 0)
    total_pipelines = execution_result.get("total_pipelines", 3)

    if status == "all_success":
        msg = f"Arquitetura medalhão executada! {success_count}/{total_pipelines} pipelines DLT"
    elif status == "partial_success":
        msg = f"Transformação parcial: {success_count}/{total_pipelines} pipelines DLT executados"
    else:
        msg = f"Transform Agent executado com status: {status}"

    print(f"🎯 {msg}")
    return msg


def run_agent_chat_only(instructions: Optional[str] = None) -> str:
    if AGENT_CHAT_AVAILABLE:
        agent = AgentChat()
        jobs = agent.run_polling_cycle()
        if jobs:
            msg = f"Agent Chat executado! {len(jobs)} vagas notificadas"
        else:
            msg = "Agent Chat executado! Nenhuma novidade encontrada"
        print(f"🎯 {msg}")
        return msg

    print("📱 Agent Chat indisponível neste ambiente. Retornando simulação.")
    return "Agent Chat simulado - sem notificações enviadas"


def run_databricks_pipeline() -> bool:
    print("🚀 Iniciando Pipeline Databricks - Transformação + Agent Chat")
    print("=" * 60)

    start = datetime.now()
    transform_result = run_transform_only()
    transform_success = "erro" not in transform_result.lower()

    chat_result = run_agent_chat_only()
    chat_success = "erro" not in chat_result.lower()

    total_duration = (datetime.now() - start).total_seconds()
    print("=" * 60)
    print(f"⏱️ Tempo total: {total_duration:.2f}s")

    if transform_success and chat_success:
        print("\n🎉 Pipeline Databricks executado com sucesso!")
        return True

    print("\n❌ Pipeline Databricks encontrado problemas. Verifique os logs.")
    return False


if __name__ == "__main__":
    success = run_databricks_pipeline()
    sys.exit(0 if success else 1)
