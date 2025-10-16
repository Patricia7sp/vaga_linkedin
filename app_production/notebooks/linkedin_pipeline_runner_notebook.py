# Databricks notebook source
# MAGIC %md
# MAGIC # LinkedIn Pipeline V4 Runner - Container Approach (Notebook)
# MAGIC
# MAGIC Script consolidado que incorpora a lógica real dos agents originais:
# MAGIC - agent_transform.py (via production_agent_databricks.py)
# MAGIC - agent_chat.py (classe AgentChat completa)
# MAGIC - transform_agent.py (via TransformAgent)
# MAGIC
# MAGIC Execução via notebook_task compatível com Databricks Community Edition

# COMMAND ----------

# Parâmetros do job (recebidos via base_parameters)
dbutils.widgets.text("mode", "transform", "Modo de execução")
dbutils.widgets.text("environment", "production", "Ambiente")
dbutils.widgets.text("telegram", "enabled", "Status Telegram")

MODE = dbutils.widgets.get("mode")
ENVIRONMENT = dbutils.widgets.get("environment") 
TELEGRAM = dbutils.widgets.get("telegram")

print(f"🚀 LinkedIn Pipeline V4 Runner - Notebook Mode")
print(f"📋 Modo: {MODE}")
print(f"🌍 Ambiente: {ENVIRONMENT}")
print(f"📱 Telegram: {TELEGRAM}")
print("=" * 70)

# COMMAND ----------

import sys
import os
from datetime import datetime
from typing import Optional

# COMMAND ----------

# MAGIC %md
# MAGIC ## Transform Agent - Lógica Real de DLT

# COMMAND ----------

# Transform Agent (lógica REAL de DLT via Databricks SDK - integrada do transform_agent.py)
try:
    import time
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.pipelines import PipelineStateInfo
    
    class TransformAgent:
        """Transform Agent que executa pipelines DLT reais (sequencial, Free Edition)"""
        
        def __init__(self):
            self.domains = ["data_engineer", "data_analytics", "digital_analytics"]
            try:
                self.client = WorkspaceClient()
                print("🔗 Cliente Databricks SDK inicializado com sucesso")
            except Exception as e:
                print(f"⚠️ Erro ao inicializar Databricks SDK: {e}")
                self.client = None
        
        def run_dlt_pipelines_execution(self):
            """EXECUTA pipelines DLT reais respeitando Free Edition (1 pipeline ativo por vez)"""
            print("🚀 Iniciando execução REAL dos pipelines DLT...")
            
            execution_results = {
                "timestamp": datetime.now().isoformat(),
                "status": "running",
                "pipelines_executed": [],
                "success_count": 0,
                "failed_count": 0,
                "total_pipelines": len(self.domains)
            }
            
            if not self.client:
                print("❌ Databricks SDK não disponível. Impossível executar pipelines.")
                execution_results["status"] = "error"
                execution_results["error"] = "sdk_unavailable"
                return execution_results
            
            # 1. Buscar IDs dos pipelines existentes (criados via Terraform)
            pipeline_ids = self._get_existing_pipeline_ids()
            
            if not pipeline_ids:
                print("❌ Nenhum pipeline DLT encontrado. Verifique deploy Terraform.")
                execution_results["status"] = "no_pipelines_found"
                return execution_results
            
            print(f"✅ Pipelines encontrados: {list(pipeline_ids.keys())}")
            
            # 2. Executar pipelines SEQUENCIALMENTE (Free Edition: 1 por vez)
            for idx, domain in enumerate(self.domains, 1):
                print("\n" + "=" * 70)
                print(f"🔄 [{idx}/3] Processando domain: {domain}")
                print("=" * 70)
                
                pipeline_id = pipeline_ids.get(domain)
                if not pipeline_id:
                    print(f"❌ Pipeline {domain} não encontrado nos IDs mapeados")
                    print(f"📌 IDs disponíveis: {list(pipeline_ids.keys())}")
                    execution_results["failed_count"] += 1
                    execution_results["pipelines_executed"].append({
                        "domain": domain,
                        "status": "not_found",
                        "error": "pipeline_id_not_mapped"
                    })
                    continue
                
                try:
                    print(f"🎯 Pipeline ID: {pipeline_id}")
                    
                    # Parar outros pipelines primeiro (Free Edition)
                    print(f"⏸️ Parando outros pipelines (Free Edition: 1 por vez)...")
                    self._stop_other_pipelines(exclude_domain=domain)
                    time.sleep(5)
                    
                    # Iniciar pipeline atual
                    print(f"🚀 Iniciando pipeline {domain}...")
                    start_result = self._start_pipeline_execution(pipeline_id, domain)
                    execution_results["pipelines_executed"].append(start_result)
                    
                    if start_result.get("status") != "started":
                        execution_results["failed_count"] += 1
                        print(f"❌ Falha ao iniciar {domain}: {start_result.get('error')}")
                        print(f"➡️ Continuando para próximo pipeline...")
                        continue
                    
                    # Aguardar conclusão antes de iniciar próximo
                    print(f"⏳ Aguardando conclusão do pipeline {domain}...")
                    if self._wait_until_idle(pipeline_id, domain, timeout_sec=900):
                        execution_results["success_count"] += 1
                        print(f"✅ Pipeline {domain} concluído com sucesso!")
                    else:
                        execution_results["failed_count"] += 1
                        print(f"❌ Pipeline {domain} timeout ou falhou")
                        print(f"➡️ Continuando para próximo pipeline...")
                        
                except Exception as e:
                    print(f"❌ Erro inesperado ao processar {domain}: {e}")
                    import traceback
                    print(f"📌 Traceback: {traceback.format_exc()}")
                    execution_results["failed_count"] += 1
                    execution_results["pipelines_executed"].append({
                        "domain": domain,
                        "status": "error",
                        "error": str(e)
                    })
                    print(f"➡️ Continuando para próximo pipeline...")
            
            # 3. Status final
            if execution_results["success_count"] == execution_results["total_pipelines"]:
                execution_results["status"] = "all_success"
                print("\n🎉 Todos os pipelines executados com sucesso!")
            elif execution_results["success_count"] > 0:
                execution_results["status"] = "partial_success"
                print(f"\n⚠️ {execution_results['success_count']}/{execution_results['total_pipelines']} pipelines executados")
            else:
                execution_results["status"] = "all_failed"
                print("\n❌ Nenhum pipeline executado com sucesso")
            
            execution_results["finished_at"] = datetime.now().isoformat()
            return execution_results
        
        def _get_existing_pipeline_ids(self):
            """Busca IDs dos pipelines DLT existentes (criados via Terraform)"""
            pipeline_ids = {}
            
            try:
                # Listar todos os pipelines
                all_pipelines = list(self.client.pipelines.list_pipelines())
                print(f"📋 Total de pipelines encontrados: {len(all_pipelines)}")
                print("📋 Listando pipelines disponíveis:")
                
                for p in all_pipelines:
                    print(f"   - {p.name} (ID: {p.pipeline_id})")
                
                # Padrões de nomes dos pipelines CORRETOS (clean_pipeline)
                pipeline_patterns = {
                    "data_engineer": ["data_engineer_clean_pipeline"],
                    "data_analytics": ["data_analytics_clean_pipeline_v2"],
                    "digital_analytics": ["digital_analytics_clean_pipeline_v2"]
                }
                
                for domain, patterns in pipeline_patterns.items():
                    found = False
                    for pipeline in all_pipelines:
                        pipeline_name = pipeline.name or ""
                        # Busca exata primeiro, depois parcial
                        if any(pattern.lower() == pipeline_name.lower() for pattern in patterns):
                            pipeline_ids[domain] = pipeline.pipeline_id
                            print(f"✅ Pipeline encontrado: {domain} -> {pipeline.pipeline_id} ({pipeline_name})")
                            found = True
                            break
                        # Busca parcial como fallback
                        elif any(pattern.lower() in pipeline_name.lower() for pattern in patterns):
                            pipeline_ids[domain] = pipeline.pipeline_id
                            print(f"✅ Pipeline encontrado (parcial): {domain} -> {pipeline.pipeline_id} ({pipeline_name})")
                            found = True
                            break
                    
                    if not found:
                        print(f"❌ Pipeline {domain} NÃO encontrado. Padrões: {patterns}")
                
                if len(pipeline_ids) < 3:
                    missing = set(self.domains) - set(pipeline_ids.keys())
                    print(f"⚠️ Pipelines faltando: {list(missing)}")
                    print(f"⚠️ Total encontrado: {len(pipeline_ids)}/3")
                else:
                    print(f"🎯 Todos os 3 pipelines encontrados!")
                
            except Exception as e:
                print(f"❌ Erro ao listar pipelines: {e}")
                import traceback
                print(f"📋 Traceback: {traceback.format_exc()}")
            
            return pipeline_ids
        
        def _start_pipeline_execution(self, pipeline_id, domain):
            """Inicia execução de um pipeline DLT"""
            result = {
                "pipeline_id": pipeline_id,
                "domain": domain,
                "status": "unknown",
                "started_at": datetime.now().isoformat()
            }
            
            try:
                # Iniciar pipeline com full refresh
                update = self.client.pipelines.start_update(
                    pipeline_id=pipeline_id,
                    full_refresh=False  # Incremental para ser mais rápido
                )
                
                result["status"] = "started"
                result["update_id"] = update.update_id
                print(f"🚀 Pipeline {domain} iniciado - Update ID: {update.update_id}")
                
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
                print(f"❌ Erro ao iniciar {domain}: {e}")
            
            return result
        
        def _wait_until_idle(self, pipeline_id, domain, timeout_sec=900):
            """Aguarda pipeline ficar IDLE/COMPLETED (integrado do transform_agent.py)"""
            waited = 0
            while waited < timeout_sec:
                try:
                    pipeline = self.client.pipelines.get(pipeline_id=pipeline_id)
                    state = pipeline.state.name if pipeline.state else "UNKNOWN"
                    
                    print(f"⏳ {domain}: {state} (t+{waited}s)")
                    
                    if state in ["IDLE", "COMPLETED"]:
                        print(f"✅ {domain} concluído em {waited}s")
                        return True
                    elif state in ["FAILED", "CANCELED", "STOPPED"]:
                        print(f"❌ {domain} falhou com estado: {state}")
                        return False
                    
                except Exception as e:
                    print(f"⚠️ Erro ao verificar estado {domain}: {e}")
                
                time.sleep(15)
                waited += 15
            
            print(f"⏱️ Timeout após {waited}s aguardando {domain}")
            return False
        
        def _stop_other_pipelines(self, exclude_domain=None):
            """Para outros pipelines rodando (Free Edition: 1 por vez)"""
            try:
                all_pipelines = list(self.client.pipelines.list_pipelines())
                
                for pipeline in all_pipelines:
                    # Pular o pipeline que queremos manter
                    if exclude_domain and exclude_domain in (pipeline.name or "").lower():
                        continue
                    
                    # Parar se estiver rodando
                    if pipeline.state and pipeline.state.name in ["RUNNING", "STARTING"]:
                        try:
                            self.client.pipelines.stop(pipeline_id=pipeline.pipeline_id)
                            print(f"⏹️ Parado: {pipeline.name}")
                        except Exception as e:
                            print(f"⚠️ Erro ao parar {pipeline.name}: {e}")
                
            except Exception as e:
                print(f"⚠️ Erro ao listar/parar pipelines: {e}")
    
    TRANSFORM_AGENT_AVAILABLE = True
    
except ImportError as e:
    print(f"⚠️ TransformAgent não disponível: {e}")
    TRANSFORM_AGENT_AVAILABLE = False

# COMMAND ----------

# MAGIC %md
# MAGIC ## Agent Chat - Carregar do Notebook

# COMMAND ----------

# MAGIC %run /Shared/agent_chat_standalone

# COMMAND ----------

# Agent Chat Wrapper
try:
    # A classe AgentChatDatabricks já foi carregada via %run /Shared/agent_chat_standalone acima
    # Aqui apenas criamos um wrapper para usar no pipeline
    
    class AgentChatReal:
        """Wrapper para AgentChat real - usa classe carregada via %run /Shared/agent_chat_standalone"""
        
        def __init__(self):
            try:
                # A classe AgentChatDatabricks já foi carregada via %run /Shared/agent_chat_standalone
                # Usar variáveis globais que foram configuradas no notebook standalone
                self.agent = AgentChatDatabricks(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
                self.start_time = datetime.now()
                print("✅ AgentChatDatabricks REAL inicializado")
            except NameError as e:
                print(f"⚠️ AgentChatDatabricks não disponível: {e}")
                print("ℹ️ Certifique-se de executar: %run /Shared/agent_chat_standalone antes desta célula")
                self.agent = None
            
        def run_polling_cycle(self):
            """Executa ciclo de polling REAL para novas vagas"""
            print("📱 Executando Agent Chat - Polling de Vagas (VERSÃO REAL)")
            
            if self.agent is None:
                print("❌ AgentChatDatabricks não disponível - execute %run /Shared/agent_chat_standalone primeiro")
                return []
            
            try:
                # Executar polling cycle REAL (AgentChatDatabricks usa método run())
                jobs = self.agent.run()
                
                if jobs and len(jobs) > 0:
                    print(f"✅ {len(jobs)} vagas notificadas via Telegram!")
                    for job in jobs:
                        print(f"   📤 {job.title} - {job.company}")
                else:
                    print("ℹ️ Nenhuma nova vaga encontrada desde o último checkpoint")
                    
                return jobs
                
            except Exception as e:
                print(f"❌ Erro no polling cycle: {e}")
                import traceback
                print(f"📋 Traceback: {traceback.format_exc()}")
                return []
    
    AGENT_CHAT_AVAILABLE = True
    
except ImportError as e:
    print(f"⚠️ AgentChat não disponível: {e}")
    AGENT_CHAT_AVAILABLE = False

# COMMAND ----------

# MAGIC %md
# MAGIC ## Funções de Execução (baseadas em production_agent_databricks.py)

# COMMAND ----------

def run_transform_only(instructions: Optional[str] = None) -> str:
    """Executa apenas a transformação DLT - baseado na lógica real"""
    print("🚀 Iniciando Transform Agent - DLT Pipeline Execution")
    
    if not TRANSFORM_AGENT_AVAILABLE:
        print("⚠️ TransformAgent não disponível - simulando execução")
        return "Transform Agent simulado - pipelines DLT não executados"
    
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
    """Executa apenas o Agent Chat - baseado na lógica real"""
    print("📱 Iniciando Agent Chat - Telegram Notification")
    print(f"🔍 AGENT_CHAT_AVAILABLE: {AGENT_CHAT_AVAILABLE}")
    
    if not AGENT_CHAT_AVAILABLE:
        print("⚠️ Agent Chat não disponível - simulando execução")
        return "Agent Chat simulado - sem notificações enviadas"
    
    print("✅ Instanciando AgentChatReal...")
    agent = AgentChatReal()
    
    print("✅ Executando run_polling_cycle...")
    jobs = agent.run_polling_cycle()
    
    print(f"✅ Resultado: {len(jobs) if jobs else 0} jobs retornados")
    
    if jobs and len(jobs) > 0:
        msg = f"Agent Chat executado! {len(jobs)} vagas notificadas"
    else:
        msg = "Agent Chat executado! Nenhuma novidade encontrada"
        
    print(f"🎯 {msg}")
    return msg


def run_databricks_pipeline() -> bool:
    """Pipeline completo: Transform + Agent Chat - baseado na lógica real"""
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

    print("\n❌ Pipeline Databricks encontrou problemas. Verifique os logs.")
    return False

# COMMAND ----------

# MAGIC %md
# MAGIC ## Execução Principal baseada nos parâmetros

# COMMAND ----------

print("🚀 INICIANDO EXECUÇÃO DO NOTEBOOK")
print(f"📋 MODE: {MODE}")
print(f"📋 TELEGRAM: {TELEGRAM}")
print(f"📋 ENVIRONMENT: {ENVIRONMENT}")
print("=" * 70)

# Executar conforme modo solicitado
success = True

if MODE == 'transform':
    print("🔧 Executando modo TRANSFORM")
    result = run_transform_only()
    success = "erro" not in result.lower()
    
elif MODE == 'chat':
    print("💬 Executando modo CHAT")
    if TELEGRAM == 'enabled':
        print("✅ Telegram ENABLED - executando Agent Chat")
        result = run_agent_chat_only()
        success = "erro" not in result.lower()
    else:
        print("📱 Telegram desabilitado - pulando Agent Chat")
        
elif MODE == 'full':
    print("🎯 Executando modo FULL")
    success = run_databricks_pipeline()
else:
    print(f"⚠️ Modo desconhecido: {MODE}")

# Resultado final
print("=" * 70)
if success:
    print("🎉 Pipeline V4 executado com sucesso!")
    dbutils.notebook.exit("SUCCESS")
else:
    print("💥 Pipeline V4 falhou - verifique os logs")
    dbutils.notebook.exit("FAILED")