#!/usr/bin/env python3
"""
🚀 Production Agent (Cloud Run v4) - Extração focada

Orquestra apenas o Extract Agent para o novo job do Cloud Run.
Responsável por enviar dados para o Cloud Storage (bronze-raw).
"""

import os
import sys
from datetime import datetime
from typing import Optional

# Garantir que o diretório raiz esteja no PYTHONPATH
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from agents.extract_agent.extract_agent import run_extract

try:
    from dotenv import load_dotenv

    load_dotenv()
    print("✅ Variáveis de ambiente carregadas do arquivo .env")
except ImportError:
    print("⚠️ python-dotenv não instalado. Usando variáveis de ambiente padrão.")


def run_extract_only(instructions: Optional[str] = None) -> str:
    """Executa somente o Extract Agent (Kafka + Cloud Storage)."""
    try:
        print("🔍 Iniciando Extract Agent - Extração LinkedIn (Cloud Run v4)...")
        result = run_extract(instructions)
        print(f"✅ Extract Agent concluído: {result}")
        return result
    except Exception as exc:  # pylint: disable=broad-except
        error_msg = f"Erro no Extract Agent: {exc}"
        print(f"❌ {error_msg}")
        return error_msg


def run_cloud_pipeline() -> bool:
    """Executa o pipeline Cloud Run v4: somente extração."""
    print("🚀 Iniciando Pipeline Cloud Run v4 - Extração")
    print("=" * 60)

    step_start = datetime.now()
    result = run_extract_only()

    # result pode ser dict ou string - tratar ambos os casos
    if isinstance(result, dict):
        # Verificar se houve extração de dados
        total_extracted = sum(v.get("count", 0) for v in result.values() if isinstance(v, dict))

        # Considerar sucesso se:
        # 1. Extraiu ao menos 1 vaga OU
        # 2. Processo completou sem erros (mesmo que sem vagas novas)
        # Isso evita falhas falsas quando API não retorna vagas temporariamente
        success = True  # Por padrão, sucesso se chegou até aqui sem exceção

        if total_extracted > 0:
            print(f"✅ {total_extracted} vagas extraídas com sucesso")
        else:
            print("⚠️ Nenhuma vaga nova extraída (pode ser temporário ou sem vagas disponíveis)")
            print("💡 Processo considerado sucesso pois não houve erro fatal")

    elif isinstance(result, str):
        # Se for string, verificar se não tem erro
        success = "erro" not in result.lower() and "falha" not in result.lower()
    else:
        success = False

    duration = (datetime.now() - step_start).total_seconds()
    status_icon = "✅" if success else "❌"
    print(f"{status_icon} Extração: {duration:.2f}s")

    if success:
        print("\n🎉 Extração concluída com sucesso! Dados sincronizados com GCS.")
    else:
        print("\n❌ Falha na extração. Verifique os logs para detalhes.")

    return success


def run_cloud_pipeline_async():
    """Executa o pipeline em modo assíncrono (compatível com Cloud Run)."""
    import threading

    def _run():
        run_cloud_pipeline()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    success = run_cloud_pipeline()
    sys.exit(0 if success else 1)
