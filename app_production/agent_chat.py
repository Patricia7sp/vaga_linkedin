#!/usr/bin/env python3
"""agent_chat
=================

Agente responsável por:

- Monitorar a view ``vagas_linkedin.viz.vw_jobs_gold_all`` para detectar novas
  vagas publicadas (mesmo critério usado no dataset ``dataset_jobs_recent`` do
  dashboard Lakeview).
- Disparar notificações via Telegram com os campos principais da vaga
  (``title``, ``company``, ``work_modality`` e ``url``).
- Perguntar ao usuário se a inscrição foi realizada e registrar as respostas
  (``SIM``/``NAO``) em uma tabela de controle capaz de alimentar widgets do
  dashboard.

O módulo foi desenhado para ser executado de forma agendada (ex.: Databricks Job
ou cron) e também expõe utilitários para processar mensagens de retorno (podendo
ser acoplado a um webhook do bot no Telegram).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from logging import Logger
from typing import Dict, Iterable, List, Optional

import requests


# ---------------------------------------------------------------------------
# Utilidades compartilhadas
# ---------------------------------------------------------------------------


def _load_env_file(filename: str = ".env") -> None:
    """Carrega variáveis de ambiente de um arquivo ``.env`` (se existir)."""

    try:
        # Tentar usar __file__ (funciona em scripts Python normais)
        env_path = Path(__file__).resolve().parent / filename
    except NameError:
        # Em notebooks Databricks, __file__ não existe - usar caminho alternativo
        env_path = Path(".") / filename

    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


# Carregar .env apenas se não estiver em ambiente Databricks
try:
    # Se dbutils existe, estamos no Databricks - não carregar .env
    from pyspark.dbutils import DBUtils
except ImportError:
    # Ambiente local - carregar .env
    _load_env_file()


def _clean_secret(s: Optional[str]) -> Optional[str]:
    """Sanitiza secrets removendo aspas, espaços, prefixo 'bot' e quebras de linha."""
    if not s:
        return s
    s = s.strip().strip('"').strip("'").replace("\n", "").replace("\r", "")
    if s.lower().startswith("bot"):
        s = s[3:]
    return s


DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "https://dbc-14d16b60-2882.cloud.databricks.com")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "ab43ca87b28a5a1d")

# Tentar ler do Databricks secrets primeiro, fallback para env vars
try:
    from pyspark.dbutils import DBUtils
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()
    dbutils = DBUtils(spark)

    TELEGRAM_BOT_TOKEN = _clean_secret(dbutils.secrets.get("vaga_linkedin_agent_chat", "telegram_bot_token"))
    TELEGRAM_CHAT_ID = _clean_secret(dbutils.secrets.get("vaga_linkedin_agent_chat", "telegram_chat_id"))
    if not DATABRICKS_TOKEN:
        DATABRICKS_TOKEN = dbutils.secrets.get("vaga_linkedin_agent_chat", "databricks_pat")

    print(
        f"🔐 Secrets carregados do Databricks: BOT_TOKEN={'*' * 10 + TELEGRAM_BOT_TOKEN[-10:] if TELEGRAM_BOT_TOKEN and len(TELEGRAM_BOT_TOKEN) > 10 else '[REDACTED]'}, CHAT_ID={TELEGRAM_CHAT_ID}"
    )

except Exception as e:
    # Fallback para variáveis de ambiente locais
    TELEGRAM_BOT_TOKEN = _clean_secret(os.getenv("TELEGRAM_BOT_TOKEN"))
    TELEGRAM_CHAT_ID = _clean_secret(os.getenv("TELEGRAM_CHAT_ID"))
    print(f"📝 Usando variáveis de ambiente locais (secrets não disponíveis: {e})")


def _configure_logger() -> Logger:
    level_name = os.getenv("AGENT_CHAT_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger("agent_chat")

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(level)
    logger.propagate = False
    logger.debug("Logger configurado com nível %s", level_name)
    return logger


LOGGER = _configure_logger()

if not DATABRICKS_TOKEN:
    raise RuntimeError("Variável de ambiente DATABRICKS_TOKEN não configurada.")


API_HEADERS = {
    "Authorization": f"Bearer {DATABRICKS_TOKEN}",
    "Content-Type": "application/json",
}


@dataclass
class JobRecord:
    """Representa uma vaga retornada pela view gold."""

    job_id: str
    title: str
    company: str
    work_modality: str
    url: str
    posted_time_ts: datetime

    @classmethod
    def from_row(cls, row: Dict[str, object]) -> "JobRecord":
        posted_raw = row["posted_time_ts"]

        if isinstance(posted_raw, datetime):
            posted_dt = posted_raw
        else:
            posted_dt = datetime.fromisoformat(str(posted_raw).replace("Z", "+00:00"))

        return cls(
            job_id=str(row["job_id"]),
            title=str(row["title"]),
            company=str(row.get("company", "")),
            work_modality=str(row.get("work_modality", "")),
            url=str(row.get("url", "")),
            posted_time_ts=posted_dt,
        )


# ---------------------------------------------------------------------------
# Cliente simples para executar SQL no Databricks Warehouse
# ---------------------------------------------------------------------------


class DatabricksSQLClient:
    """Cliente mínimo para executar consultas SQL via REST API."""

    def __init__(self, host: str, token: str, warehouse_id: str):
        self._host = host.rstrip("/")
        self._token = token
        self._warehouse_id = warehouse_id

    # API Endpoints -----------------------------------------------------
    def _statements_url(self, suffix: str = "") -> str:
        base = f"{self._host}/api/2.0/sql/statements"
        return f"{base}/{suffix}" if suffix else base

    def execute(self, query: str, *, wait_seconds: int = 30) -> List[Dict[str, object]]:
        payload = {
            "warehouse_id": self._warehouse_id,
            "statement": query,
            "wait_timeout": f"{wait_seconds}s",
        }

        response = requests.post(self._statements_url(), headers=API_HEADERS, json=payload, timeout=60)

        if response.status_code != 200:
            raise RuntimeError(f"Falha ao executar SQL (status {response.status_code}): {response.text}")

        data = response.json()
        status = data.get("status", {}).get("state")
        statement_id = data.get("statement_id")

        if status == "FAILED":
            raise RuntimeError(f"Consulta com falha: {json.dumps(data, ensure_ascii=False)}")

        if status == "FINISHED":
            return self._parse_result(data)

        if not statement_id:
            raise RuntimeError("Resposta inesperada: statement_id ausente.")

        return self._poll_results(statement_id, wait_seconds)

    def _poll_results(self, statement_id: str, wait_seconds: int) -> List[Dict[str, object]]:
        deadline = time.time() + wait_seconds

        while time.time() < deadline:
            time.sleep(1)
            response = requests.get(self._statements_url(statement_id), headers=API_HEADERS, timeout=30)

            if response.status_code != 200:
                raise RuntimeError(f"Erro ao consultar status ({response.status_code}): {response.text}")

            data = response.json()
            status = data.get("status", {}).get("state")

            if status == "FINISHED":
                return self._parse_result(data)

            if status == "FAILED":
                raise RuntimeError(f"Consulta com falha: {json.dumps(data, ensure_ascii=False)}")

        raise TimeoutError(f"Tempo excedido aguardando resultado da consulta {statement_id}.")

    @staticmethod
    def _parse_result(payload: Dict[str, object]) -> List[Dict[str, object]]:
        result = payload.get("result")

        if not result:
            return []

        columns = [col["name"] for col in result.get("schema", {}).get("columns", [])]
        rows = result.get("data_array", [])

        return [dict(zip(columns, row)) for row in rows]


# ---------------------------------------------------------------------------
# Telegram Messenger
# ---------------------------------------------------------------------------


class TelegramMessenger:
    """Responsável por enviar mensagens via Telegram Bot API.

    Se ``TELEGRAM_BOT_TOKEN`` e ``TELEGRAM_CHAT_ID`` estiverem definidos,
    envia a mensagem usando ``sendMessage``. Caso contrário, apenas loga no console.
    """

    API_URL_TEMPLATE = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, bot_token: Optional[str], chat_id: Optional[str], logger: Logger):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.logger = logger
        retry_env = os.getenv("AGENT_CHAT_SEND_RETRIES", "3")
        try:
            self.max_retries = max(1, int(retry_env))
        except ValueError:
            self.max_retries = 3
            self.logger.warning("Valor inválido para AGENT_CHAT_SEND_RETRIES (%s). Usando 3.", retry_env)

    def _api(self, method: str) -> str:
        """Constrói URL da API do Telegram."""
        return self.API_URL_TEMPLATE.format(token=self.bot_token, method=method)

    def healthcheck(self) -> None:
        """Valida conexão com Telegram via getMe e sendChatAction."""
        if not self.bot_token or not self.chat_id:
            self.logger.warning("Bot token ou chat_id não configurados. Pulando healthcheck.")
            return

        # 1) getMe - valida token
        try:
            response = requests.get(self._api("getMe"), timeout=10)
            if response.status_code != 200 or not response.json().get("ok"):
                raise RuntimeError(f"Telegram getMe falhou: {response.status_code} {response.text}")

            bot_info = response.json()["result"]
            self.logger.info("✅ Bot conectado: @%s (ID: %s)", bot_info.get("username"), bot_info.get("id"))
        except Exception as e:
            raise RuntimeError(f"Healthcheck getMe falhou: {e}")

        # 2) sendChatAction - valida chat_id e permissões
        try:
            payload = {"chat_id": self.chat_id, "action": "typing"}
            response = requests.post(self._api("sendChatAction"), json=payload, timeout=10)
            if response.status_code != 200 or not response.json().get("ok"):
                raise RuntimeError(f"Telegram sendChatAction falhou: {response.status_code} {response.text}")

            self.logger.info("✅ Chat ID %s validado com sucesso", self.chat_id)
        except Exception as e:
            raise RuntimeError(f"Healthcheck sendChatAction falhou: {e}")

    def send_message(self, body: str) -> None:
        if not self.bot_token or not self.chat_id:
            self.logger.info("[SIMULAÇÃO Telegram]\n%s", body)
            return

        url = self._api("sendMessage")
        payload = {
            "chat_id": self.chat_id,
            "text": body,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(url, json=payload, timeout=15)
                if response.status_code != 200:
                    self.logger.warning(
                        "Falha ao enviar mensagem Telegram (tentativa %s/%s): %s",
                        attempt,
                        self.max_retries,
                        response.text,
                    )
                    time.sleep(1 * attempt)
                    continue

                self.logger.info("Mensagem enviada via Telegram (tentativa %s)", attempt)
                return
            except requests.RequestException as exc:  # pragma: no cover - somente log
                self.logger.error(
                    "Erro inesperado ao enviar mensagem Telegram (tentativa %s/%s): %s",
                    attempt,
                    self.max_retries,
                    exc,
                )
                time.sleep(1 * attempt)

        self.logger.error("Não foi possível enviar mensagem após %s tentativas", self.max_retries)


# ---------------------------------------------------------------------------
# Persistência e lógica principal do Agent Chat
# ---------------------------------------------------------------------------


class AgentChat:
    STATE_TABLE = "vagas_linkedin.viz.chat_agent_state"
    SENT_TABLE = "vagas_linkedin.viz.chat_agent_sent_jobs"
    RESPONSES_TABLE = "vagas_linkedin.viz.chat_agent_responses"
    VIEW_RESPONSES = "vagas_linkedin.viz.vw_chat_agent_responses"
    VIEW_SUMMARY = "vagas_linkedin.viz.vw_chat_agent_summary"
    VIEW_TOTALS = "vagas_linkedin.viz.vw_chat_agent_totals"

    BASE_QUERY = """
        SELECT
            domain,
            job_id,
            title,
            company,
            work_modality,
            country,
            state,
            city,
            posted_time_ts,
            url
        FROM vagas_linkedin.viz.vw_jobs_gold_all
        WHERE posted_time_ts > {since_ts}
        ORDER BY posted_time_ts ASC
    """

    def __init__(self, sql_client: Optional[DatabricksSQLClient] = None, logger: Logger = LOGGER):
        self.sql = sql_client or DatabricksSQLClient(DATABRICKS_HOST, DATABRICKS_TOKEN, WAREHOUSE_ID)
        self.logger = logger
        self.messenger = TelegramMessenger(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, logger)

    # --- Setup ---------------------------------------------------------
    def ensure_tables(self) -> None:
        statements = [
            f"""
            CREATE TABLE IF NOT EXISTS {self.STATE_TABLE} (
                last_posted_time_ts TIMESTAMP
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {self.SENT_TABLE} (
                job_id STRING,
                title STRING,
                company STRING,
                work_modality STRING,
                url STRING,
                posted_time_ts TIMESTAMP,
                notified_ts TIMESTAMP
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {self.RESPONSES_TABLE} (
                job_id STRING,
                decision STRING,
                decision_ts TIMESTAMP,
                responder STRING,
                title STRING,
                company STRING,
                work_modality STRING,
                url STRING
            )
            """,
        ]

        for statement in statements:
            self.sql.execute(statement)

        view_statements = [
            f"""
            CREATE OR REPLACE VIEW {self.VIEW_RESPONSES} AS
            SELECT
                job_id,
                decision,
                decision_ts,
                responder,
                title,
                company,
                work_modality,
                url
            FROM {self.RESPONSES_TABLE}
            """,
            f"""
            CREATE OR REPLACE VIEW {self.VIEW_SUMMARY} AS
            SELECT
                DATE(decision_ts) AS decision_date,
                decision,
                COUNT(*) AS decisions_count
            FROM {self.RESPONSES_TABLE}
            GROUP BY DATE(decision_ts), decision
            """,
            f"""
            CREATE OR REPLACE VIEW {self.VIEW_TOTALS} AS
            SELECT
                decision,
                COUNT(*) AS total
            FROM {self.RESPONSES_TABLE}
            GROUP BY decision
            """,
        ]

        for statement in view_statements:
            try:
                self.sql.execute(statement)
            except Exception as exc:
                self.logger.error("Erro ao criar view: %s", exc)

    # --- Polling -------------------------------------------------------
    def run_polling_cycle(self) -> List[JobRecord]:
        self.ensure_tables()

        # Healthcheck do Telegram antes de buscar vagas
        try:
            self.messenger.healthcheck()
        except Exception as e:
            self.logger.error("❌ Healthcheck do Telegram falhou: %s", e)
            self.logger.error("Abortando envio de notificações. Verifique token e chat_id.")
            return []

        since = self._get_last_checkpoint()
        jobs = self._fetch_new_jobs(since)

        if not jobs:
            self.logger.info("Sem novas vagas desde o último checkpoint.")
            return []

        for job in jobs:
            body = self._build_message(job)
            self.messenger.send_message(body)
            self._register_sent_job(job)

        newest_ts = max(job.posted_time_ts for job in jobs)
        self._update_checkpoint(newest_ts)

        self.logger.info("%s nova(s) vaga(s) notificadas.", len(jobs))
        return jobs

    def poll_and_notify(self) -> List[JobRecord]:
        """Alias para run_polling_cycle() - usado no notebook."""
        return self.run_polling_cycle()

    def _fetch_new_jobs(self, since: datetime) -> List[JobRecord]:
        since_literal = self._timestamp_literal(since)

        # Query com filtro de job_id já enviados
        # IMPORTANTE: Usando ingestion_timestamp porque posted_time_ts vem NULL da API RapidAPI
        query = f"""
        SELECT
            domain,
            job_id,
            title,
            company,
            work_modality,
            country,
            state,
            city,
            COALESCE(posted_time_ts, ingestion_timestamp) as posted_time_ts,
            url
        FROM vagas_linkedin.viz.vw_jobs_gold_all
        WHERE ingestion_timestamp > {since_literal}
          AND job_id NOT IN (
              SELECT job_id FROM {self.SENT_TABLE}
          )
        ORDER BY ingestion_timestamp ASC
        """

        rows = self.sql.execute(query)
        return [JobRecord.from_row(row) for row in rows]

    @staticmethod
    def _timestamp_literal(dt: datetime) -> str:
        return f"TIMESTAMP '{dt.strftime('%Y-%m-%d %H:%M:%S')}'"

    def _get_last_checkpoint(self) -> datetime:
        rows = self.sql.execute(
            f"SELECT last_posted_time_ts FROM {self.STATE_TABLE} ORDER BY last_posted_time_ts DESC LIMIT 1"
        )

        if not rows or rows[0]["last_posted_time_ts"] is None:
            default_since = datetime.utcnow() - timedelta(hours=6)
            self.logger.info(
                "Nenhum checkpoint encontrado. Usando janela inicial de 6 horas (%s)",
                default_since.isoformat(timespec="seconds"),
            )
            return default_since

        value = rows[0]["last_posted_time_ts"]
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    def _update_checkpoint(self, new_ts: datetime) -> None:
        timestamp_literal = self._timestamp_literal(new_ts)
        statements = [
            f"DELETE FROM {self.STATE_TABLE}",
            f"INSERT INTO {self.STATE_TABLE} VALUES ({timestamp_literal})",
        ]
        for statement in statements:
            self.sql.execute(statement)

    # --- Mensageria ----------------------------------------------------
    @staticmethod
    def _build_message(job: JobRecord) -> str:
        job_id_short = job.job_id
        posted = job.posted_time_ts.strftime("%d/%m/%Y")

        return (
            "*Nova vaga disponível!*\n"
            f"ID: `{job_id_short}`\n"
            f"Título: {job.title}\n"
            f"Empresa: {job.company}\n"
            f"Modalidade: {job.work_modality}\n"
            f"Publicada em: {posted}\n"
            f"[Abrir vaga]({job.url})\n\n"
            "Você se candidatou? Responda aqui com:\n"
            f"SIM {job_id_short} ou NAO {job_id_short}."
        )

    def _register_sent_job(self, job: JobRecord) -> None:
        statement = f"""
            INSERT INTO {self.SENT_TABLE}
            VALUES (
                '{job.job_id}',
                {self._sql_str(job.title)},
                {self._sql_str(job.company)},
                {self._sql_str(job.work_modality)},
                {self._sql_str(job.url)},
                {self._timestamp_literal(job.posted_time_ts)},
                current_timestamp()
            )
        """
        self.sql.execute(statement)

    @staticmethod
    def _sql_str(value: str) -> str:
        escaped = value.replace("'", "''")
        return f"'{escaped}'"

    # --- Processamento de respostas -----------------------------------
    def process_incoming_message(self, sender: str, message: str) -> Optional[Dict[str, object]]:
        message = message.strip().upper()
        parts = message.split()

        if len(parts) < 2 or parts[0] not in {"SIM", "NAO"}:
            self.logger.warning("Mensagem ignorada: formato inválido (%s)", message)
            return None

        decision = parts[0]
        job_id = parts[1]

        job = self._fetch_sent_job(job_id)
        if not job:
            self.logger.warning("Job_id %s não encontrado no histórico de notificações.", job_id)
            return None

        self._record_decision(job, decision, sender)
        result = {"job_id": job.job_id, "decision": decision, "sender": sender}
        self.logger.info("Resposta registrada: %s", result)
        return result

    def _fetch_sent_job(self, job_id: str) -> Optional[JobRecord]:
        rows = self.sql.execute(
            f"""
            SELECT job_id, title, company, work_modality, url, posted_time_ts
            FROM {self.SENT_TABLE}
            WHERE job_id = '{job_id}'
            ORDER BY notified_ts DESC
            LIMIT 1
        """
        )

        if not rows:
            return None

        return JobRecord.from_row(rows[0])

    def _record_decision(self, job: JobRecord, decision: str, sender: str) -> None:
        statement = f"""
            INSERT INTO {self.RESPONSES_TABLE}
            VALUES (
                '{job.job_id}',
                '{decision}',
                current_timestamp(),
                {self._sql_str(sender)},
                {self._sql_str(job.title)},
                {self._sql_str(job.company)},
                {self._sql_str(job.work_modality)},
                {self._sql_str(job.url)}
            )
        """
        self.sql.execute(statement)


class FakeAgentChat(AgentChat):
    """Implementação em memória para testes locais sem Databricks."""

    def __init__(self):  # pragma: no cover - suporte a testes manuais
        self.logger = LOGGER
        self.sql = None
        self.messenger = TelegramMessenger(None, None, self.logger)
        now = datetime.utcnow()
        self.fake_jobs = [
            JobRecord(
                job_id="FAKE_JOB_1",
                title="Engenheiro(a) de Dados",
                company="Empresa Exemplo",
                work_modality="Remoto",
                url="https://www.example.com/vaga-fake",
                posted_time_ts=now - timedelta(minutes=10),
            ),
            JobRecord(
                job_id="FAKE_JOB_2",
                title="Analista de Dados",
                company="Dados SA",
                work_modality="Híbrido",
                url="https://www.example.com/vaga-fake-2",
                posted_time_ts=now - timedelta(minutes=5),
            ),
        ]
        self.sent_jobs: Dict[str, JobRecord] = {}
        self.responses: List[Dict[str, object]] = []
        self.last_checkpoint = now - timedelta(hours=1)

    def ensure_tables(self) -> None:
        self.logger.debug("FakeAgentChat.ensure_tables chamado")

    def _get_last_checkpoint(self) -> datetime:
        return self.last_checkpoint

    def _update_checkpoint(self, new_ts: datetime) -> None:
        self.last_checkpoint = new_ts

    def _fetch_new_jobs(self, since: datetime) -> List[JobRecord]:
        return [job for job in self.fake_jobs if job.posted_time_ts > since]

    def _register_sent_job(self, job: JobRecord) -> None:
        self.sent_jobs[job.job_id] = job

    def _fetch_sent_job(self, job_id: str) -> Optional[JobRecord]:
        return self.sent_jobs.get(job_id)

    def _record_decision(self, job: JobRecord, decision: str, sender: str) -> None:
        payload = {
            "job_id": job.job_id,
            "decision": decision,
            "sender": sender,
            "decision_ts": datetime.utcnow(),
        }
        self.responses.append(payload)
        self.logger.debug("Resposta registrada (fake): %s", payload)


# ---------------------------------------------------------------------------
# CLI de utilidade
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agent Chat - notificação de vagas via Telegram")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("poll", help="Executa um ciclo de verificação de novas vagas.")

    args_record = subparsers.add_parser(
        "record",
        help="Registra manualmente uma resposta (SIM/NAO job_id).",
    )
    args_record.add_argument("sender", help="Identificador de quem respondeu (ex.: telegram_user_id)")
    args_record.add_argument("decision", help="SIM ou NAO")
    args_record.add_argument("job_id", help="Identificador da vaga")

    args_process = subparsers.add_parser(
        "process-message",
        help="Processa mensagem já formatada (ex.: 'SIM 123').",
    )
    args_process.add_argument("sender")
    args_process.add_argument("message")

    return parser


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return

    fake_mode = os.getenv("AGENT_CHAT_FAKE_MODE", "false").lower() in {"1", "true", "yes"}

    if fake_mode:
        LOGGER.info("Executando AgentChat em modo fake (sem Databricks).")
        agent: AgentChat = FakeAgentChat()
    else:
        agent = AgentChat()

    if args.command == "poll":
        agent.run_polling_cycle()
        return

    if args.command == "process-message":
        agent.process_incoming_message(args.sender, args.message)
        return

    if args.command == "record":
        job = agent._fetch_sent_job(args.job_id)
        if not job:
            LOGGER.warning("Vaga %s não encontrada no histórico. Execute 'poll' primeiro.", args.job_id)
            return
        agent._record_decision(job, args.decision.upper(), args.sender)
        LOGGER.info("Resposta registrada manualmente para %s (%s).", args.job_id, args.decision.upper())
        return


# Não executar main() automaticamente quando importado via %run no Databricks
# O main() só deve ser executado quando chamado diretamente como script CLI
if __name__ == "__main__":
    # Verificar se estamos em ambiente Databricks
    try:
        from pyspark.dbutils import DBUtils

        # Estamos no Databricks - não executar main()
        print("ℹ️ Agent Chat carregado no Databricks - use AgentChat() diretamente")
    except ImportError:
        # Ambiente local/CLI - executar main()
        main()
