#!/usr/bin/env python3
"""
🔍 Databricks Job Monitor
Monitor jobs do Databricks e envia alertas se houver falhas.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Configurações
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Jobs críticos para monitorar
CRITICAL_JOBS = [
    "linkedin-agent-chat-notifications",
    "linkedin-dlt-pipeline",
    "linkedin-extract-agent",
]


class DatabricksMonitor:
    """Monitor de Jobs do Databricks."""

    def __init__(self, host: str, token: str):
        self.host = host.rstrip("/")
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def list_jobs(self) -> List[Dict]:
        """Lista todos os jobs do Databricks."""
        url = f"{self.host}/api/2.1/jobs/list"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("jobs", [])
        except Exception as e:
            print(f"❌ Erro ao listar jobs: {e}")
            return []

    def get_job_runs(self, job_id: int, limit: int = 10) -> List[Dict]:
        """Busca runs recentes de um job."""
        url = f"{self.host}/api/2.1/jobs/runs/list"
        params = {"job_id": job_id, "limit": limit, "expand_tasks": False}

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("runs", [])
        except Exception as e:
            print(f"❌ Erro ao buscar runs do job {job_id}: {e}")
            return []

    def check_job_health(self, job_name: str) -> Dict:
        """Verifica a saúde de um job específico."""
        jobs = self.list_jobs()

        # Encontrar o job pelo nome
        job = next((j for j in jobs if j.get("settings", {}).get("name") == job_name), None)

        if not job:
            return {
                "job_name": job_name,
                "status": "NOT_FOUND",
                "message": f"Job '{job_name}' não encontrado",
                "severity": "ERROR",
            }

        job_id = job.get("job_id")
        job_settings = job.get("settings", {})

        # Buscar runs recentes
        runs = self.get_job_runs(job_id, limit=5)

        if not runs:
            return {
                "job_name": job_name,
                "job_id": job_id,
                "status": "NO_RUNS",
                "message": "Job não tem execuções recentes",
                "severity": "WARNING",
            }

        # Analisar último run
        latest_run = runs[0]
        run_state = latest_run.get("state", {})
        life_cycle_state = run_state.get("life_cycle_state")
        result_state = run_state.get("result_state")

        # Verificar tempo desde último run
        start_time = latest_run.get("start_time", 0) / 1000  # milliseconds to seconds
        last_run_date = datetime.fromtimestamp(start_time)
        hours_since_last_run = (datetime.now() - last_run_date).total_seconds() / 3600

        # Determinar status
        if result_state == "SUCCESS":
            if hours_since_last_run > 24:
                status = "STALE"
                severity = "WARNING"
                message = f"Último run bem-sucedido há {hours_since_last_run:.1f}h"
            else:
                status = "HEALTHY"
                severity = "INFO"
                message = f"Último run bem-sucedido há {hours_since_last_run:.1f}h"
        elif result_state == "FAILED":
            status = "FAILED"
            severity = "ERROR"
            message = f"Último run FALHOU há {hours_since_last_run:.1f}h"
        elif life_cycle_state == "RUNNING":
            status = "RUNNING"
            severity = "INFO"
            message = "Job em execução"
        else:
            status = "UNKNOWN"
            severity = "WARNING"
            message = f"Estado desconhecido: {life_cycle_state}/{result_state}"

        # Calcular taxa de sucesso (últimos 5 runs)
        success_count = sum(1 for r in runs if r.get("state", {}).get("result_state") == "SUCCESS")
        success_rate = (success_count / len(runs)) * 100 if runs else 0

        return {
            "job_name": job_name,
            "job_id": job_id,
            "status": status,
            "severity": severity,
            "message": message,
            "last_run_date": last_run_date.isoformat(),
            "hours_since_last_run": hours_since_last_run,
            "success_rate": success_rate,
            "schedule": job_settings.get("schedule", {}).get("quartz_cron_expression", "Manual"),
            "run_url": f"{self.host}/#job/{job_id}/run/{latest_run.get('run_id')}",
        }

    def monitor_all_critical_jobs(self) -> List[Dict]:
        """Monitora todos os jobs críticos."""
        results = []

        print("🔍 Monitorando jobs críticos do Databricks...")
        print("=" * 60)

        for job_name in CRITICAL_JOBS:
            health = self.check_job_health(job_name)
            results.append(health)

            # Print status
            severity_icon = {"INFO": "✅", "WARNING": "⚠️", "ERROR": "❌"}.get(health["severity"], "❓")
            print(f"{severity_icon} {job_name}")
            print(f"   Status: {health['status']}")
            print(f"   Mensagem: {health['message']}")
            if "success_rate" in health:
                print(f"   Taxa de Sucesso: {health['success_rate']:.1f}%")
            print()

        return results

    def send_telegram_alert(self, health_report: Dict) -> bool:
        """Envia alerta via Telegram para jobs com problemas."""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("⚠️ Telegram não configurado. Pulando envio de alerta.")
            return False

        # Só envia alerta se for WARNING ou ERROR
        if health_report["severity"] not in ["WARNING", "ERROR"]:
            return False

        severity_icon = {"WARNING": "⚠️", "ERROR": "🚨"}.get(health_report["severity"])

        message = f"""
{severity_icon} **Alerta Databricks Job**

**Job:** {health_report['job_name']}
**Status:** {health_report['status']}
**Mensagem:** {health_report['message']}

**Taxa de Sucesso (últimos 5 runs):** {health_report.get('success_rate', 'N/A'):.1f}%
**Última Execução:** {health_report.get('hours_since_last_run', 'N/A'):.1f}h atrás
**Schedule:** {health_report.get('schedule', 'N/A')}

**Ver Detalhes:** {health_report.get('run_url', 'N/A')}
        """.strip()

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            print(f"📨 Alerta Telegram enviado para {health_report['job_name']}")
            return True
        except Exception as e:
            print(f"❌ Erro ao enviar alerta Telegram: {e}")
            return False


def main():
    """Função principal."""
    if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
        print("❌ DATABRICKS_HOST e DATABRICKS_TOKEN são necessários!")
        print("Configure via variáveis de ambiente.")
        sys.exit(1)

    monitor = DatabricksMonitor(DATABRICKS_HOST, DATABRICKS_TOKEN)

    # Monitorar jobs críticos
    health_reports = monitor.monitor_all_critical_jobs()

    # Enviar alertas para jobs com problemas
    alerts_sent = 0
    for report in health_reports:
        if report["severity"] in ["WARNING", "ERROR"]:
            if monitor.send_telegram_alert(report):
                alerts_sent += 1

    # Resumo
    print("=" * 60)
    print(f"✅ Monitoramento concluído")
    print(f"📊 Jobs verificados: {len(health_reports)}")
    print(f"📨 Alertas enviados: {alerts_sent}")

    # Retornar exit code baseado em severidade
    has_errors = any(r["severity"] == "ERROR" for r in health_reports)
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
