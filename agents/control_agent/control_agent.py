#!/usr/bin/env python3
"""
Control Agent for Vagas LinkedIn Project.
Orchestrates the execution of the pipeline with user approval at each step.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infra_agent.infra_agent import run_infra
from extract_agent.extract_agent import run_extract
from load_agent.load_agent_cli import run_load
from transform_agent.transform_agent import run_transform
from viz_agent.viz_agent import run_viz


def validate_step_completion(step_name, result):
    """
    Validate if a step was completed successfully based on the result.
    """
    if step_name == "Infraestrutura":
        # Check if all 4 components are present: GCP, Buckets, Terraform, Databricks
        required_components = ["Bucket", "Terraform", "Databricks"]
        missing_components = []

        for component in required_components:
            if component not in result:
                missing_components.append(component)

        if missing_components:
            print(f"⚠️  Componentes faltando na infraestrutura: {', '.join(missing_components)}")
            return False

        # Check for critical errors
        if "não instalado" in result or "com erro" in result:
            print("⚠️  Alguns componentes têm problemas de instalação ou configuração")
            return False

        return True

    elif step_name == "Extração":
        # Check if data was extracted and saved
        return "vagas processadas" in result or "Dados extraídos" in result

    elif step_name == "Carregamento":
        # Check if data was loaded successfully via CLI
        return "ready_for_transform_agent" in result or "registros" in result or "Unity Catalog" in result

    elif step_name == "Transformação":
        # Check if data was transformed into tables
        return "tabelas:" in result or "transformados" in result

    elif step_name == "Visualização":
        # Check if visualizations were created
        return "Dashboard" in result or "visualizações" in result

    # Default validation - just check if there's no error message
    return "Erro" not in result and "erro" not in result


def run_pipeline():
    """
    Run the complete pipeline with user approval at each step.
    """
    steps = [
        {"name": "Infraestrutura", "function": run_infra, "status": "pending"},
        {"name": "Extração", "function": run_extract, "status": "pending"},
        {"name": "Carregamento", "function": run_load, "status": "pending"},
        {"name": "Transformação", "function": run_transform, "status": "pending"},
        {"name": "Visualização", "function": run_viz, "status": "pending"},
    ]

    print("🚀 Iniciando o Pipeline de Vagas LinkedIn")
    print("Cada etapa requer sua aprovação para prosseguir.\n")

    for i, step in enumerate(steps):
        print(f"📌 Etapa {i+1}: {step['name']}")
        print("Status atual:")
        for j, s in enumerate(steps):
            status = "✅ Concluída" if j < i else ("🔄 Ativa" if j == i else "⏳ Pendente")
            print(f"  - Etapa {j+1}: {s['name']} - {status}")

        if i > 0:
            print(f"Resultado da etapa anterior ({steps[i-1]['name']}): Simulado com sucesso.")

        instructions = input(
            f"Digite instruções para a etapa '{step['name']}' (ou caminho para arquivo.md) ou 's' para prosseguir sem instruções: "
        ).strip()

        if instructions.endswith(".md") and os.path.exists(instructions):
            with open(instructions, "r", encoding="utf-8") as f:
                print("Instruções do arquivo:")
                print(f.read())
        elif instructions != "s":
            print("Instruções:", instructions)

        response = input(f"\nDeseja iniciar a etapa '{step['name']}' com essas instruções? (s/n): ").strip().lower()
        if response != "s":
            print("Pipeline interrompido pelo usuário.")
            return

        print(f"\nExecutando {step['name']}...")
        try:
            if instructions != "s" and instructions:
                result = step["function"](instructions)
            else:
                result = step["function"]()

            # Validate step completion
            if validate_step_completion(step["name"], result):
                print(f"✅ Etapa '{step['name']}' concluída com sucesso. Resultado: {result}")
                step["status"] = "completed"
            else:
                print(f"⚠️  Etapa '{step['name']}' completada parcialmente. Resultado: {result}")
                retry = input("Deseja continuar mesmo assim? (s/n): ").strip().lower()
                if retry != "s":
                    print("Pipeline interrompido para correções.")
                    return
                step["status"] = "completed"
        except Exception as e:
            print(f"❌ Erro na etapa '{step['name']}': {e}")
            return

    print("\n🎉 Pipeline concluído com sucesso!")


if __name__ == "__main__":
    run_pipeline()
