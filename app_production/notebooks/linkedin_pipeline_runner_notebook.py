# Databricks notebook source
# MAGIC %md
# MAGIC # LinkedIn DLT Pipeline Runner - Single Pipeline Mode
# MAGIC
# MAGIC **VERSÃO SIMPLIFICADA - APENAS DLT**
# MAGIC - Executa 1 pipeline DLT por vez (Free Edition compatible)
# MAGIC - Agent Chat tem job separado
# MAGIC
# MAGIC **PARÂMETRO:**
# MAGIC - pipeline: "data_engineer" | "data_analytics" | "digital_analytics"

# COMMAND ----------

# Parâmetros do job
dbutils.widgets.text("pipeline", "data_engineer", "Pipeline DLT a executar")
dbutils.widgets.text("environment", "production", "Ambiente")

PIPELINE = dbutils.widgets.get("pipeline")
ENVIRONMENT = dbutils.widgets.get("environment")

print(f"🚀 LinkedIn DLT Pipeline Runner - Single Mode")
print(f"🎯 Pipeline: {PIPELINE}")
print(f"🌍 Ambiente: {ENVIRONMENT}")
print("=" * 70)

# COMMAND ----------

import time
from datetime import datetime
from databricks.sdk import WorkspaceClient

# COMMAND ----------

# MAGIC %md
# MAGIC ## DLT Pipeline Executor

# COMMAND ----------

class DLTPipelineExecutor:
    """Executa 1 pipeline DLT específico (Free Edition compatible)"""
    
    def __init__(self, pipeline_name):
        self.pipeline_name = pipeline_name
        self.pipeline_map = {
            "data_engineer": "data_engineer_clean_pipeline",
            "data_analytics": "data_analytics_clean_pipeline_v2",
            "digital_analytics": "digital_analytics_clean_pipeline_v2"
        }
        try:
            self.client = WorkspaceClient()
            print(f"🔗 Databricks SDK inicializado")
        except Exception as e:
            print(f"⚠️ Erro ao inicializar SDK: {e}")
            self.client = None
    
    def run(self):
        """Executa o pipeline"""
        print(f"🚀 Iniciando pipeline: {self.pipeline_name}")
        
        if not self.client:
            print("❌ SDK não disponível")
            return False
        
        # 1. Buscar ID do pipeline
        pipeline_id = self._get_pipeline_id()
        if not pipeline_id:
            print(f"❌ Pipeline não encontrado")
            return False
        
        print(f"✅ Pipeline ID: {pipeline_id}")
        
        # 2. Parar outros pipelines (Free Edition: 1 por vez)
        print(f"⏸️ Parando outros pipelines...")
        self._stop_other_pipelines()
        time.sleep(5)
        
        # 3. Iniciar pipeline
        print(f"🚀 Iniciando {self.pipeline_name}...")
        try:
            update = self.client.pipelines.start_update(
                pipeline_id=pipeline_id,
                full_refresh=False
            )
            print(f"✅ Pipeline iniciado - Update ID: {update.update_id}")
        except Exception as e:
            print(f"❌ Erro ao iniciar: {e}")
            return False
        
        # 4. Aguardar conclusão
        print(f"⏳ Aguardando conclusão (timeout: 900s)...")
        if self._wait_until_idle(pipeline_id, timeout=900):
            print(f"✅ {self.pipeline_name} concluído com sucesso!")
            return True
        else:
            print(f"❌ {self.pipeline_name} falhou ou timeout")
            return False
    
    def _get_pipeline_id(self):
        """Busca ID do pipeline pelo nome"""
        try:
            all_pipelines = list(self.client.pipelines.list_pipelines())
            expected_name = self.pipeline_map.get(self.pipeline_name, "")
            
            print(f"📋 Procurando pipeline: {expected_name}")
            
            for p in all_pipelines:
                if p.name and expected_name.lower() in p.name.lower():
                    print(f"✅ Encontrado: {p.name} (ID: {p.pipeline_id})")
                    return p.pipeline_id
            
            print(f"❌ Pipeline {expected_name} não encontrado")
            print("📋 Pipelines disponíveis:")
            for p in all_pipelines:
                print(f"   - {p.name}")
            
            return None
        except Exception as e:
            print(f"❌ Erro ao buscar pipeline: {e}")
            return None
    
    def _stop_other_pipelines(self):
        """Para outros pipelines rodando"""
        try:
            all_pipelines = list(self.client.pipelines.list_pipelines())
            expected_name = self.pipeline_map.get(self.pipeline_name, "")
            
            for p in all_pipelines:
                # Pular o pipeline que queremos executar
                if p.name and expected_name.lower() in p.name.lower():
                    continue
                
                # Parar se estiver rodando
                if p.state and p.state.name in ["RUNNING", "STARTING"]:
                    try:
                        self.client.pipelines.stop(pipeline_id=p.pipeline_id)
                        print(f"⏹️ Parado: {p.name}")
                    except Exception as e:
                        print(f"⚠️ Erro ao parar {p.name}: {e}")
        except Exception as e:
            print(f"⚠️ Erro ao listar pipelines: {e}")
    
    def _wait_until_idle(self, pipeline_id, timeout=900):
        """Aguarda pipeline ficar IDLE/COMPLETED"""
        waited = 0
        while waited < timeout:
            try:
                pipeline = self.client.pipelines.get(pipeline_id=pipeline_id)
                state = pipeline.state.name if pipeline.state else "UNKNOWN"
                
                print(f"⏳ Estado: {state} (t+{waited}s)")
                
                if state in ["IDLE", "COMPLETED"]:
                    print(f"✅ Concluído em {waited}s")
                    return True
                elif state in ["FAILED", "CANCELED", "STOPPED"]:
                    print(f"❌ Falhou com estado: {state}")
                    return False
                
            except Exception as e:
                print(f"⚠️ Erro ao verificar estado: {e}")
            
            time.sleep(15)
            waited += 15
        
        print(f"⏱️ Timeout após {waited}s")
        return False

# COMMAND ----------

# MAGIC %md
# MAGIC ## Execução Principal

# COMMAND ----------

print("🚀 INICIANDO EXECUÇÃO")
print(f"📋 Pipeline: {PIPELINE}")
print("=" * 70)

executor = DLTPipelineExecutor(PIPELINE)
success = executor.run()

print("=" * 70)
if success:
    print("🎉 Pipeline executado com sucesso!")
    dbutils.notebook.exit("SUCCESS")
else:
    print("💥 Pipeline falhou - verifique os logs")
    dbutils.notebook.exit("FAILED")
