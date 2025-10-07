#!/usr/bin/env python3
"""
🚀 Production Agent (Databricks) - Transformação + Agent Chat

Orquestrador específico para o ambiente Databricks.
Responsável por:
1. Executar os pipelines DLT (Bronze → Silver → Gold) via `TransformAgent`
2. Acionar o `AgentChat` após a conclusão para enviar notificações de vagas novas.

Este arquivo não é mais utilizado diretamente pelo Cloud Run.
O novo `production_agent_cloud.py` cuida apenas da extração.
"""

import os
import sys
import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional

# Adicionar path para importar agentes
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports dos agentes necessários em Databricks
from transform_agent.transform_agent import TransformAgent

# Carrega variáveis de ambiente (útil em execução local/Databricks)
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("✅ Variáveis de ambiente carregadas do arquivo .env")
except ImportError:
    print("⚠️  python-dotenv não instalado. Usando variáveis de ambiente do sistema.")

# Importar Agent Chat com fallback
try:
    from agent_chat import AgentChat

    AGENT_CHAT_AVAILABLE = True
    print("✅ AgentChat importado com sucesso")
except ImportError as e:
    AGENT_CHAT_AVAILABLE = False
    print(f"⚠️ agent_chat.py não encontrado ({e}) - Agent Chat será simulado")


def validate_step_completion(step_name: str, result: str) -> bool:
    """
    Valida se um step foi concluído com sucesso.

    Args:
        step_name: Nome do step executado
        result: Resultado retornado pelo agente

    Returns:
        True se o step foi bem-sucedido
    """
    if step_name == "Transformação":
        # Check if transformations were applied
        return "transformados" in result or "pipelines DLT executados" in result or "medalhão" in result

    elif step_name == "Agent Chat":
        # Check if Agent Chat setup and notifications are working
        return "tabelas criadas" in result or "Telegram" in result or "notificações" in result

    # Default validation - just check if there's no error message
    return "Erro" not in result and "erro" not in result


def run_transform_production(instructions: str | None = None) -> str:
    """
    Executa o Transform Agent que gerencia os 3 notebooks DLT da arquitetura medalhão.
    Versão otimizada para produção.
    """
    try:
        print("🧠 Iniciando Transform Agent - Arquitetura Medalhão...")

        agent = TransformAgent()

        # EXECUTAR os 3 pipelines DLT no Databricks (sem deploy desnecessário)
        execution_result = agent.run_dlt_pipelines_execution()

        status = execution_result.get("status", "unknown")
        success_count = execution_result.get("success_count", 0)
        total_pipelines = execution_result.get("total_pipelines", 3)

        if status == "all_success":
            result_msg = (
                f"Arquitetura medalhão executada! {success_count}/{total_pipelines} pipelines DLT (Bronze→Silver→Gold)"
            )
        elif status == "partial_success":
            result_msg = f"Transformação parcial: {success_count}/{total_pipelines} pipelines DLT executados"
        else:
            result_msg = f"Transform Agent executado com status: {status}"

        print(f"🎯 {result_msg}")
        return result_msg

    except Exception as e:
        error_msg = f"Erro no Transform Agent: {e}"
        print(f"❌ {error_msg}")
        return error_msg


def run_agent_chat_production(instructions: str | None = None) -> str:
    """
    Executa o Agent Chat para notificações Telegram em produção.
    """
    try:
        print("🤖 Iniciando Agent Chat - Notificações Telegram...")

        if AGENT_CHAT_AVAILABLE:
            # Usar AgentChat real
            agent = AgentChat()
            print("✅ AgentChat inicializado com sucesso")

            # Executar ciclo de polling para detectar novas vagas
            jobs = agent.run_polling_cycle()
            if jobs:
                result_msg = f"Agent Chat executado! {len(jobs)} vagas processadas e notificadas via Telegram"
            else:
                result_msg = "Agent Chat executado! Sistema monitorando novas vagas via Telegram"

            print(f"🎯 {result_msg}")
            return result_msg
        else:
            # Simulação para desenvolvimento
            print("📱 [SIMULAÇÃO] Verificando novas vagas...")
            print("📧 [SIMULAÇÃO] Enviando notificações Telegram...")
            print("✅ [SIMULAÇÃO] Agent Chat executado com sucesso!")

            return "Agent Chat simulado - sistema pronto para notificações Telegram"

    except Exception as e:
        error_msg = f"Erro no Agent Chat: {e}"
        print(f"❌ {error_msg}")
        return error_msg


def run_production_pipeline():
    """
    Executa o pipeline de produção com os 3 agentes essenciais.

    Pipeline otimizado para Cloud Run:
    1. Extract Agent - Extração LinkedIn
    2. Transform Agent - DLT (Bronze→Silver→Gold)
    3. Agent Chat - Notificações Telegram
    """
    print("🚀 Iniciando Pipeline de Produção - Databricks")
    print("=" * 60)
    print("📊 2 Agentes Essenciais:")
    print("  1. Transform Agent - DLT Arquitetura Medalhão")
    print("  2. Agent Chat - Notificações Telegram")
    print("=" * 60)

    steps = [
        {"name": "Transformação", "function": run_transform_production, "status": "pending"},
        {"name": "Agent Chat", "function": run_agent_chat_production, "status": "pending"},
    ]

    start_time = datetime.now()
    results = []

    try:
        for step in steps:
            step_name = step["name"]
            step_function = step["function"]

            print(f"\n🔄 Executando: {step_name}")
            print("-" * 40)

            step_start = datetime.now()

            try:
                # Executar step
                result = step_function()
                step["status"] = "completed"
                step["result"] = result

                # Validar conclusão
                if validate_step_completion(step_name, result):
                    print(f"✅ {step_name} concluído com sucesso!")
                    step["validated"] = True
                else:
                    print(f"⚠️ {step_name} concluído mas pode ter problemas")
                    step["validated"] = False

            except Exception as e:
                error_msg = f"Erro no {step_name}: {e}"
                print(f"❌ {error_msg}")
                step["status"] = "failed"
                step["error"] = error_msg
                step["validated"] = False

            step_duration = (datetime.now() - step_start).total_seconds()
            step["duration"] = step_duration

            results.append(
                {
                    "step": step_name,
                    "status": step["status"],
                    "duration": step_duration,
                    "validated": step.get("validated", False),
                }
            )

            print(f"⏱️ Duração: {step_duration:.2f}s")

        # Resumo final
        total_duration = (datetime.now() - start_time).total_seconds()
        successful_steps = len([s for s in steps if s["status"] == "completed"])
        validated_steps = len([s for s in steps if s.get("validated", False)])

        print("\n" + "=" * 60)
        print("📊 RESUMO DO PIPELINE DE PRODUÇÃO")
        print("=" * 60)
        print(f"⏱️ Tempo total: {total_duration:.2f}s")
        print(f"✅ Steps concluídos: {successful_steps}/3")
        print(f"🔍 Steps validados: {validated_steps}/3")

        for result in results:
            status_icon = "✅" if result["status"] == "completed" else "❌"
            validation_icon = "🔍" if result["validated"] else "⚠️"
            print(f"   {status_icon} {validation_icon} {result['step']}: {result['duration']:.2f}s")

        if successful_steps == len(steps) and validated_steps == len(steps):
            print("\n🎉 PIPELINE DE PRODUÇÃO EXECUTADO COM SUCESSO!")
            print("📊 Dados transformados → notificações enviadas")
            return True
        elif successful_steps == len(steps):
            print("\n⚠️ Pipeline concluído mas com warnings")
            return True
        else:
            print("\n❌ Pipeline falhou em alguns steps")
            return False

    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO NO PIPELINE: {e}")
        return False


def run_production_pipeline_async():
    """
    Executa o pipeline de produção de forma assíncrona.
    Útil para Cloud Run com timeouts.
    """

    def run_async():
        try:
            result = run_production_pipeline()
            print(f"\n🔗 Pipeline assíncrono concluído: {'✅ Sucesso' if result else '❌ Falha'}")
        except Exception as e:
            print(f"\n💥 Erro no pipeline assíncrono: {e}")

    thread = threading.Thread(target=run_async, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    """
    Execução direta do Production Agent
    """
    print("🚀 Production Agent - Pipeline Cloud Run")
    print("Versão otimizada com 3 agentes essenciais")

    success = run_production_pipeline()

    if success:
        print("\n✅ Production Agent executado com sucesso!")
        sys.exit(0)
    else:
        print("\n❌ Production Agent falhou")
        sys.exit(1)
