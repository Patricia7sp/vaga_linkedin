#!/usr/bin/env python3
"""
Infra Agent: Provisions infrastructure using Terraform.
"""

import subprocess
import os


def run_infra(instructions=None):
    """
    Provision GCP buckets, Databricks workspace, etc.
    Run real commands based on instructions.
    """
    print("🚀 Provisionando infraestrutura...")

    results = []

    try:
        # Check if gcloud is installed
        print("📋 Verificando instalação do gcloud...")
        result = subprocess.run(["gcloud", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Google Cloud SDK não está instalado. Por favor, instale primeiro.")
            return "Erro: Google Cloud SDK não encontrado."

        print("✅ Google Cloud SDK encontrado")

        # Authenticate with GCP
        print("🔐 Iniciando autenticação no GCP...")
        print("Por favor, complete a autenticação no browser que será aberto...")
        subprocess.run(["gcloud", "auth", "login"], check=True)

        # Set project
        project_id = input("Digite o ID do seu projeto GCP: ").strip()
        subprocess.run(["gcloud", "config", "set", "project", project_id], check=True)
        print(f"✅ Projeto configurado: {project_id}")

        # Enable required APIs
        print("🔧 Habilitando APIs necessárias...")
        subprocess.run(["gcloud", "services", "enable", "storage.googleapis.com"], check=True)
        print("✅ APIs habilitadas")

        # Create buckets
        print("📦 Criando buckets no Cloud Storage...")
        buckets = ["linkedin-dados-raw", "linkedin-dados-processados"]

        for bucket in buckets:
            try:
                subprocess.run(
                    ["gcloud", "storage", "buckets", "create", f"gs://{bucket}", "--location=us-central1"], check=True
                )
                print(f"✅ Bucket criado: {bucket}")
                results.append(f"Bucket {bucket} criado")
            except subprocess.CalledProcessError:
                print(f"ℹ️  Bucket {bucket} já existe ou erro na criação")
                results.append(f"Bucket {bucket} verificado")

        # Step 3: Terraform Authentication and Setup
        print("🔧 Configurando Terraform...")
        try:
            # Check if Terraform is installed
            result = subprocess.run(["terraform", "version"], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Terraform encontrado")

                # Initialize Terraform in terraform directory
                terraform_dir = os.path.join(os.path.dirname(__file__), "../../terraform")
                if os.path.exists(terraform_dir):
                    print("🔄 Inicializando Terraform...")
                    subprocess.run(["terraform", "init"], cwd=terraform_dir, check=True)
                    print("✅ Terraform inicializado")
                    results.append("Terraform configurado")
                else:
                    print("⚠️  Diretório terraform não encontrado")
                    results.append("Terraform - diretório não encontrado")
            else:
                print("❌ Terraform não está instalado. Por favor, instale o Terraform.")
                print("Visite: https://www.terraform.io/downloads.html")
                results.append("Terraform não instalado")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Erro na configuração do Terraform: {e}")
            results.append("Terraform com erro")
        except FileNotFoundError:
            print("❌ Terraform não encontrado. Por favor, instale o Terraform.")
            results.append("Terraform não instalado")

        # Step 4: Databricks CLI Installation and Authentication
        print("🏗️  Configurando Databricks CLI...")
        databricks_installed = False

        try:
            # Check if Databricks CLI is installed
            result = subprocess.run(["databricks", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Databricks CLI encontrado")
                databricks_installed = True
            else:
                print("❌ Databricks CLI não está instalado.")
                databricks_installed = False
        except FileNotFoundError:
            print("❌ Databricks CLI não encontrado.")
            databricks_installed = False
        except Exception as e:
            print(f"⚠️  Erro ao verificar Databricks CLI: {e}")
            databricks_installed = False

        # If not installed, offer to install
        if not databricks_installed:
            print("Para instalar: pip install databricks-cli")
            install_databricks = input("Deseja instalar o Databricks CLI agora? (s/n): ").strip().lower()
            if install_databricks == "s":
                try:
                    print("📦 Instalando Databricks CLI...")
                    # Use python -m pip to ensure it uses the correct environment
                    subprocess.run(["python", "-m", "pip", "install", "databricks-cli"], check=True)
                    print("✅ Databricks CLI instalado com sucesso")
                    databricks_installed = True
                    results.append("Databricks CLI instalado")
                except subprocess.CalledProcessError as e:
                    print(f"❌ Erro ao instalar Databricks CLI: {e}")
                    results.append("Databricks CLI erro na instalação")
                    databricks_installed = False
            else:
                print("ℹ️  Instalação do Databricks CLI pulada")
                results.append("Databricks CLI não instalado")

        # If installed, configure authentication
        if databricks_installed:
            setup_databricks = input("Deseja configurar autenticação do Databricks agora? (s/n): ").strip().lower()
            if setup_databricks == "s":
                try:
                    print("🔐 Configurando autenticação do Databricks...")

                    # Check if it's the new CLI version (supports 'auth login')
                    auth_check = subprocess.run(["databricks", "auth", "--help"], capture_output=True, text=True)

                    if auth_check.returncode == 0:
                        # New CLI version
                        print("Usando nova versão do Databricks CLI...")
                        print("Por favor, complete a autenticação no browser...")
                        subprocess.run(["databricks", "auth", "login"], check=True)
                        print("✅ Databricks autenticado")
                        results.append("Databricks configurado")
                    else:
                        # Legacy CLI version - use token-based authentication
                        print("Detectada versão legacy do Databricks CLI...")
                        print("Para configurar, você precisará de:")
                        print("1. Workspace URL (ex: https://your-workspace.cloud.databricks.com)")
                        print("2. Token de acesso pessoal do Databricks")
                        print("\nPara gerar um token:")
                        print("- Acesse seu workspace Databricks")
                        print("- Vá em Settings > User Settings > Access Tokens")
                        print("- Clique em 'Generate New Token'")

                        configure_token = input("\nDeseja configurar com token agora? (s/n): ").strip().lower()
                        if configure_token == "s":
                            workspace_url = input("Digite a URL do workspace: ").strip()
                            token = input("Digite o token de acesso: ").strip()

                            if workspace_url and token:
                                # Configure using the legacy method
                                config_process = subprocess.Popen(
                                    ["databricks", "configure", "--token"],
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                )

                                # Send inputs
                                stdout, stderr = config_process.communicate(input=f"{workspace_url}\n{token}\n")

                                if config_process.returncode == 0:
                                    print("✅ Databricks configurado com token")
                                    results.append("Databricks configurado")
                                else:
                                    print(f"⚠️  Erro na configuração: {stderr}")
                                    results.append("Databricks configuração com erro")
                            else:
                                print("⚠️  URL ou token não fornecidos")
                                results.append("Databricks configuração incompleta")
                        else:
                            print("ℹ️  Configuração manual do Databricks pulada")
                            results.append("Databricks configuração pulada")

                except subprocess.CalledProcessError as e:
                    print(f"⚠️  Erro na autenticação do Databricks: {e}")
                    results.append("Databricks autenticação com erro")
            else:
                print("ℹ️  Configuração do Databricks pulada")
                results.append("Databricks configuração pulada")

        print("🎉 Infraestrutura provisionada com sucesso!")

        # Generate summary report
        summary = f"Infraestrutura provisionada: {', '.join(results)}"
        print(f"\n📋 Resumo: {summary}")

        return summary

    except subprocess.CalledProcessError as e:
        error_msg = f"Erro ao executar comando: {e}"
        print(f"❌ {error_msg}")
        return error_msg
    except KeyboardInterrupt:
        print("❌ Operação cancelada pelo usuário")
        return "Operação cancelada"
    except Exception as e:
        error_msg = f"Erro inesperado: {e}"
        print(f"❌ {error_msg}")
        return error_msg


if __name__ == "__main__":
    run_infra()
