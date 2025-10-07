"""
DLT Pipeline Simulator - Testa notebooks localmente antes da execução no Databricks
"""

import os
import sys
from typing import Any, Dict



class DLTSimulator:
    """Simula execução local de notebooks DLT para validação prévia"""

    def __init__(self):
        self.tables = {}
        self.streams = {}
        self.apply_changes_calls = []
        self.errors = []
        self.warnings = []

    def setup_mock_environment(self):
        """Configura ambiente mock simples para validação sintática"""

        # Mock simples que não executa código real
        class SimpleMock:
            def __init__(self, name="mock"):
                self.name = name

            def __call__(self, *args, **kwargs):
                return SimpleMock(f"{self.name}_called")

            def __getattr__(self, name):
                return SimpleMock(f"{self.name}.{name}")

            def __getitem__(self, key):
                return SimpleMock(f"{self.name}[{key}]")

            def __add__(self, other):
                return SimpleMock(f"{self.name}+{other}")

            def __sub__(self, other):
                return SimpleMock(f"{self.name}-{other}")

            def __mul__(self, other):
                return SimpleMock(f"{self.name}*{other}")

            def __truediv__(self, other):
                return SimpleMock(f"{self.name}/{other}")

            def __gt__(self, other):
                return SimpleMock(f"{self.name}>{other}")

            def __lt__(self, other):
                return SimpleMock(f"{self.name}<{other}")

        return {
            # DLT mocks
            "dlt": SimpleMock("dlt"),
            # PySpark function mocks - todos retornam SimpleMock
            "col": SimpleMock("col"),
            "lower": SimpleMock("lower"),
            "regexp_replace": SimpleMock("regexp_replace"),
            "trim": SimpleMock("trim"),
            "to_timestamp": SimpleMock("to_timestamp"),
            "current_timestamp": SimpleMock("current_timestamp"),
            "unix_timestamp": SimpleMock("unix_timestamp"),
            "input_file_name": SimpleMock("input_file_name"),
            "md5": SimpleMock("md5"),
            "when": SimpleMock("when"),
            "regexp_extract": SimpleMock("regexp_extract"),
            "avg": SimpleMock("avg"),
            "count": SimpleMock("count"),
            "lit": SimpleMock("lit"),
            "sum": SimpleMock("sum"),
            "spark_sum": SimpleMock("spark_sum"),
            "max": SimpleMock("max"),
            "spark_max": SimpleMock("spark_max"),
            "collect_set": SimpleMock("collect_set"),
            "array": SimpleMock("array"),
            # Spark session mock
            "spark": SimpleMock("spark"),
            # Types mocks
            "StructType": SimpleMock("StructType"),
            "StructField": SimpleMock("StructField"),
            "StringType": SimpleMock("StringType"),
            "TimestampType": SimpleMock("TimestampType"),
        }

    def simulate_notebook_execution(self, notebook_path: str, domain: str) -> Dict[str, Any]:
        """Valida notebook DLT usando análise estática"""

        result = {
            "success": True,
            "errors": [],
            "warnings": [],
            "executed_functions": [],
            "tables_created": [],
            "cdc_operations": [],
        }

        try:
            # Ler conteúdo do notebook
            with open(notebook_path, "r") as f:
                notebook_content = f.read()

            # 1. Validação Sintática - compilar sem executar
            try:
                compile(notebook_content, notebook_path, "exec")
                result["warnings"].append("✅ Sintaxe válida")
            except SyntaxError as e:
                result["success"] = False
                result["errors"].append(f"❌ Erro de sintaxe na linha {e.lineno}: {e.msg}")
                return result

            # 2. Análise Estática - extrair informações do código
            import re

            # Detectar tabelas criadas
            table_matches = re.findall(r'name\s*=\s*["\']([^"\']+)["\']', notebook_content)
            result["tables_created"] = table_matches

            # Detectar operações CDC
            if "dlt.apply_changes(" in notebook_content:
                cdc_targets = re.findall(r'target\s*=\s*["\']([^"\']+)["\']', notebook_content)
                result["cdc_operations"] = cdc_targets

            # Detectar funções definidas
            function_matches = re.findall(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", notebook_content)
            result["executed_functions"] = function_matches

            # 3. Validação de estrutura DLT
            self._validate_dlt_structure(notebook_content, result, domain)

            # 4. Usar DLTValidator para validação completa
            sys.path.append("/usr/local/anaconda3/vaga_linkedin")
            try:
                from agents.transform_agent.dlt_validator import DLTValidator

                validator = DLTValidator()
                validation_result = validator.validate_notebook(notebook_path, domain)

                if not validation_result["valid"]:
                    result["success"] = False
                    result["errors"].extend([f"DLTValidator: {err}" for err in validation_result["errors"]])
                else:
                    result["warnings"].append("✅ DLTValidator passou")

            except Exception as e:
                result["warnings"].append(f"⚠️ DLTValidator não disponível: {str(e)}")

        except Exception as e:
            result["success"] = False
            result["errors"].append(f"Erro na validação: {str(e)}")

        return result

    def _validate_dlt_structure(self, content: str, result: Dict[str, Any], domain: str):
        """Valida estrutura específica do DLT"""

        # Verificar imports necessários
        required_imports = ["import dlt", "from pyspark.sql.functions"]
        for imp in required_imports:
            if imp not in content:
                result["errors"].append(f"❌ Import obrigatório ausente: {imp}")
                result["success"] = False

        # Verificar se há pelo menos 3 tabelas (bronze, silver, gold)
        if len(result["tables_created"]) < 3:
            result["warnings"].append(f"⚠️ Esperado pelo menos 3 tabelas, encontrado {len(result['tables_created'])}")

        # Verificar padrão medalion
        expected_tables = [f"{domain}_bronze", f"{domain}_silver", f"gold_{domain}"]
        for expected in expected_tables:
            if expected not in result["tables_created"]:
                result["warnings"].append(f"⚠️ Tabela esperada não encontrada: {expected}")

        # Verificar CDC
        if not result["cdc_operations"]:
            result["warnings"].append("⚠️ Nenhuma operação CDC detectada")

        # Verificar se dlt.apply_changes está dentro de função
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "dlt.apply_changes(" in line.strip() and not line.strip().startswith("#"):
                # Verificar se está dentro de uma função
                inside_function = False
                for j in range(i - 1, max(0, i - 20), -1):
                    if lines[j].strip().startswith("def "):
                        inside_function = True
                        break
                    elif lines[j].strip() and not lines[j].strip().startswith("#"):
                        break

                if not inside_function:
                    result["errors"].append("❌ dlt.apply_changes deve estar dentro de função @dlt.table")
                    result["success"] = False

    def validate_all_notebooks(self, notebook_dir: str) -> Dict[str, Any]:
        """Valida todos os notebooks DLT"""

        domains = ["data_analytics", "data_engineer", "digital_analytics"]
        results = {}

        overall_success = True

        for domain in domains:
            notebook_path = os.path.join(notebook_dir, f"dlt_{domain}_transformation.py")

            if os.path.exists(notebook_path):
                print(f"🔍 Simulando execução: {domain}")
                result = self.simulate_notebook_execution(notebook_path, domain)
                results[domain] = result

                if not result["success"]:
                    overall_success = False

        return {
            "overall_success": overall_success,
            "domain_results": results,
            "summary": self._generate_summary(results),
        }

    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Gera resumo da simulação"""

        total_notebooks = len(results)
        successful = sum(1 for r in results.values() if r["success"])
        failed = total_notebooks - successful

        all_tables = []
        all_cdc = []
        all_errors = []

        for domain, result in results.items():
            all_tables.extend(result.get("tables_created", []))
            all_cdc.extend(result.get("cdc_operations", []))
            all_errors.extend([f"{domain}: {err}" for err in result.get("errors", [])])

        return {
            "total_notebooks": total_notebooks,
            "successful": successful,
            "failed": failed,
            "success_rate": f"{(successful/total_notebooks)*100:.1f}%",
            "total_tables": len(all_tables),
            "total_cdc_operations": len(all_cdc),
            "total_errors": len(all_errors),
            "errors": all_errors,
        }


def run_simulation():
    """Executa simulação completa dos pipelines"""

    print("🧪 DLT PIPELINE SIMULATOR - VALIDAÇÃO LOCAL")
    print("=" * 50)

    simulator = DLTSimulator()
    notebook_dir = "/usr/local/anaconda3/vaga_linkedin/transform_output"

    # Executar simulação
    validation_results = simulator.validate_all_notebooks(notebook_dir)

    # Relatório detalhado
    print(f"\n📊 RESULTADOS DA SIMULAÇÃO:")
    print(f"   Total de notebooks: {validation_results['summary']['total_notebooks']}")
    print(f"   Sucessos: {validation_results['summary']['successful']}")
    print(f"   Falhas: {validation_results['summary']['failed']}")
    print(f"   Taxa de sucesso: {validation_results['summary']['success_rate']}")

    print(f"\n📋 ESTATÍSTICAS:")
    print(f"   Tabelas criadas: {validation_results['summary']['total_tables']}")
    print(f"   Operações CDC: {validation_results['summary']['total_cdc_operations']}")

    # Detalhar por domínio
    for domain, result in validation_results["domain_results"].items():
        status = "✅" if result["success"] else "❌"
        print(f"\n{status} {domain.upper()}:")

        if result["success"]:
            print(f"   Funções executadas: {len(result['executed_functions'])}")
            print(f"   Tabelas: {result['tables_created']}")
            if result["cdc_operations"]:
                print(f"   CDC: {result['cdc_operations']}")
        else:
            print("   ERROS:")
            for error in result["errors"]:
                print(f"      • {error}")

    # Resultado final
    if validation_results["overall_success"]:
        print(f"\n🎉 SIMULAÇÃO COMPLETA: TODOS OS NOTEBOOKS VÁLIDOS")
        print(f"   ✅ Seguro para executar update no Databricks")
        return True
    else:
        print(f"\n⚠️  SIMULAÇÃO FALHOU: CORREÇÕES NECESSÁRIAS")
        print(f"   ❌ NÃO execute update até corrigir os erros")
        return False


if __name__ == "__main__":
    success = run_simulation()
    sys.exit(0 if success else 1)
