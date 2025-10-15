# Databricks notebook source
# MAGIC %md
# MAGIC # Agent Chat - Notificações Telegram (ATUALIZADO)
# MAGIC
# MAGIC **VERSÃO:** 2.0 (15/10/2025)
# MAGIC
# MAGIC **CORREÇÕES APLICADAS:**
# MAGIC - ✅ COALESCE(posted_time_ts, ingestion_timestamp)
# MAGIC - ✅ F-strings em todas queries SQL
# MAGIC - ✅ Checkpoint persistente

# COMMAND ----------

print("🚀 Agent Chat v2.0 - Notificações Telegram")
print("📅 Data:", "2025-10-15")
print("=" * 70)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Importar Código Atualizado

# COMMAND ----------

# Importar código do agent_chat.py (ATUALIZADO)
import sys
sys.path.insert(0, '/Workspace/Shared')

# Imports necessários
import os
import logging
from datetime import datetime

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Configurar Secrets

# COMMAND ----------

def _clean_secret(s):
    """Sanitiza secrets removendo aspas, espaços, etc."""
    if not s:
        return s
    s = s.strip().strip('"').strip("'").replace("\n", "").replace("\r", "")
    if s.lower().startswith("bot"):
        s = s[3:]
    return s

# Carregar secrets
TELEGRAM_BOT_TOKEN = _clean_secret(dbutils.secrets.get("vaga_linkedin_agent_chat", "telegram_bot_token"))
TELEGRAM_CHAT_ID = _clean_secret(dbutils.secrets.get("vaga_linkedin_agent_chat", "telegram_chat_id"))

# Configurar variáveis de ambiente
os.environ["TELEGRAM_BOT_TOKEN"] = TELEGRAM_BOT_TOKEN
os.environ["TELEGRAM_CHAT_ID"] = TELEGRAM_CHAT_ID
os.environ["DATABRICKS_HOST"] = "https://dbc-14d16b60-2882.cloud.databricks.com"
os.environ["DATABRICKS_WAREHOUSE_ID"] = "ab43ca87b28a5a1d"

print("✅ Secrets configurados")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Executar Agent Chat (Código Inline com Correções)

# COMMAND ----------

# Como o Databricks não consegue importar .py files facilmente,
# vamos usar código inline mas COM AS CORREÇÕES aplicadas

import requests
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class JobRecord:
    job_id: str
    title: str
    company: str
    work_modality: str
    url: str
    posted_time_ts: datetime
    domain: str = "unknown"

class AgentChatDatabricks:
    """Agent Chat COM CORREÇÕES (COALESCE + F-strings)"""
    
    STATE_TABLE = "vagas_linkedin.viz.chat_agent_state"
    SENT_TABLE = "vagas_linkedin.viz.chat_agent_sent_jobs"
    
    def __init__(self, telegram_token: str, telegram_chat_id: str):
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
    
    def _timestamp_literal(self, dt: datetime) -> str:
        return f"TIMESTAMP '{dt.strftime('%Y-%m-%d %H:%M:%S')}'"
    
    def _get_last_checkpoint(self) -> datetime:
        """Pegar último checkpoint."""
        try:
            result = spark.sql(f"SELECT last_posted_time_ts FROM {self.STATE_TABLE} ORDER BY last_posted_time_ts DESC LIMIT 1").collect()
            if result and result[0]["last_posted_time_ts"]:
                return result[0]["last_posted_time_ts"]
        except:
            pass
        
        # Default: últimas 6 horas
        from datetime import timedelta
        default = datetime.now() - timedelta(hours=6)
        print(f"ℹ️ Sem checkpoint - usando janela de 6h: {default}")
        return default
    
    def _fetch_new_jobs(self, since: datetime) -> List[JobRecord]:
        """Buscar vagas NOVAS usando COALESCE (CORRIGIDO!)"""
        since_literal = self._timestamp_literal(since)
        
        # Query CORRIGIDA com COALESCE
        query = f"""
        SELECT
            domain,
            job_id,
            title,
            company,
            work_modality,
            url,
            COALESCE(posted_time_ts, ingestion_timestamp) as posted_time_ts
        FROM vagas_linkedin.viz.vw_jobs_gold_all
        WHERE COALESCE(posted_time_ts, ingestion_timestamp) > {since_literal}
          AND job_id NOT IN (
              SELECT job_id FROM {self.SENT_TABLE}
          )
        ORDER BY COALESCE(posted_time_ts, ingestion_timestamp) ASC
        LIMIT 50
        """
        
        print(f"🔍 Query executada com checkpoint: {since}")
        df = spark.sql(query)
        rows = df.collect()
        
        jobs = []
        for row in rows:
            jobs.append(JobRecord(
                job_id=str(row["job_id"]),
                title=str(row["title"]),
                company=str(row["company"]),
                work_modality=str(row.get("work_modality", "")),
                url=str(row["url"]),
                posted_time_ts=row["posted_time_ts"],
                domain=str(row.get("domain", "unknown"))
            ))
        
        return jobs
    
    def _send_telegram(self, message: str) -> bool:
        """Enviar mensagem para Telegram."""
        if not self.telegram_token or not self.telegram_chat_id:
            print(f"[SIMULAÇÃO Telegram]\n{message}")
            return True
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return True
            else:
                print(f"❌ Telegram erro: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Telegram exception: {e}")
            return False
    
    def _register_sent_job(self, job: JobRecord):
        """Registrar vaga enviada."""
        job_id = job.job_id.replace("'", "''")
        title = job.title.replace("'", "''")
        company = job.company.replace("'", "''")
        url = job.url.replace("'", "''")
        posted_ts = self._timestamp_literal(job.posted_time_ts)
        
        statement = f"""
            INSERT INTO {self.SENT_TABLE}
            VALUES (
                '{job_id}',
                '{title}',
                '{company}',
                '',
                '{url}',
                {posted_ts},
                current_timestamp()
            )
        """
        spark.sql(statement)
    
    def _update_checkpoint(self, new_ts: datetime):
        """Atualizar checkpoint."""
        ts_literal = self._timestamp_literal(new_ts)
        spark.sql(f"DELETE FROM {self.STATE_TABLE}")
        spark.sql(f"INSERT INTO {self.STATE_TABLE} VALUES ({ts_literal})")
    
    def run(self) -> List[JobRecord]:
        """Executar ciclo completo."""
        print("\n" + "=" * 70)
        print("🔄 INICIANDO CICLO DE POLLING")
        print("=" * 70)
        
        # 1. Pegar checkpoint
        since = self._get_last_checkpoint()
        print(f"📌 Checkpoint: {since}")
        
        # 2. Buscar vagas novas
        jobs = self._fetch_new_jobs(since)
        print(f"📊 Vagas encontradas: {len(jobs)}")
        
        if not jobs:
            print("ℹ️  Nenhuma vaga nova")
            return []
        
        # 3. Enviar notificações
        for i, job in enumerate(jobs, 1):
            message = (
                f"*🆕 Nova Vaga {i}/{len(jobs)}*\n\n"
                f"*Domínio:* {job.domain}\n"
                f"*Título:* {job.title}\n"
                f"*Empresa:* {job.company}\n"
                f"*Modalidade:* {job.work_modality}\n"
                f"*ID:* `{job.job_id[:10]}...`\n"
                f"[🔗 Ver vaga]({job.url})\n"
            )
            
            if self._send_telegram(message):
                print(f"✅ [{i}/{len(jobs)}] Enviado: {job.title}")
                self._register_sent_job(job)
                time.sleep(1)  # Rate limit
            else:
                print(f"❌ [{i}/{len(jobs)}] Falhou: {job.title}")
        
        # 4. Atualizar checkpoint
        newest_ts = max(job.posted_time_ts for job in jobs)
        self._update_checkpoint(newest_ts)
        print(f"✅ Checkpoint atualizado: {newest_ts}")
        
        return jobs

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Executar

# COMMAND ----------

import time

try:
    agent = AgentChatDatabricks(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    jobs = agent.run()
    
    if jobs:
        dbutils.notebook.exit(f"SUCCESS: {len(jobs)} vaga(s) enviada(s)")
    else:
        dbutils.notebook.exit("SUCCESS: Nenhuma nova vaga")
        
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    dbutils.notebook.exit(f"ERROR: {str(e)}")
