#!/bin/bash
# Verificar APIs e Permissões GCP necessárias para o pipeline

set -e

PROJECT_ID="vaga-linkedin"
USER_EMAIL="paty7sp@gmail.com"

echo "🔍 VERIFICAÇÃO COMPLETA - PROJETO: $PROJECT_ID"
echo "=========================================="

# 1. Verificar APIs habilitadas
echo ""
echo "📊 1. VERIFICANDO APIS HABILITADAS:"
echo "------------------------------------"

apis_needed=(
    "artifactregistry.googleapis.com"
    "run.googleapis.com" 
    "cloudbuild.googleapis.com"
    "cloudscheduler.googleapis.com"
    "secretmanager.googleapis.com"
    "storage.googleapis.com"
)

for api in "${apis_needed[@]}"; do
    if gcloud services list --enabled --project=$PROJECT_ID --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        echo "✅ $api - HABILITADA"
    else
        echo "❌ $api - NÃO HABILITADA"
    fi
done

# 2. Verificar roles IAM do usuário
echo ""
echo "🔐 2. VERIFICANDO ROLES IAM DO USUÁRIO:"
echo "--------------------------------------"

roles_needed=(
    "roles/artifactregistry.admin"
    "roles/run.admin"
    "roles/cloudbuild.builds.editor" 
    "roles/cloudscheduler.admin"
    "roles/secretmanager.admin"
    "roles/storage.admin"
)

echo "Roles atuais para $USER_EMAIL:"
current_roles=$(gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --format="table(bindings.role)" --filter="bindings.members:$USER_EMAIL" 2>/dev/null || echo "Erro ao verificar roles")

for role in "${roles_needed[@]}"; do
    if echo "$current_roles" | grep -q "$role"; then
        echo "✅ $role - ATRIBUÍDO"
    else
        echo "❌ $role - NÃO ATRIBUÍDO"
    fi
done

echo ""
echo "🚨 COMANDOS PARA HABILITAR (execute no Console GCP ou gcloud):"
echo "=============================================================="

echo ""
echo "📡 APIs (execute estes comandos):"
for api in "${apis_needed[@]}"; do
    echo "gcloud services enable $api --project=$PROJECT_ID"
done

echo ""
echo "🔐 ROLES IAM (execute estes comandos):"
for role in "${roles_needed[@]}"; do
    echo "gcloud projects add-iam-policy-binding $PROJECT_ID --member=\"user:$USER_EMAIL\" --role=\"$role\""
done

echo ""
echo "🌐 OU CONFIGURE VIA CONSOLE GCP:"
echo "https://console.cloud.google.com/iam-admin/iam?project=$PROJECT_ID"
