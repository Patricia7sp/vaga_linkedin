#!/bin/bash
# Deploy Secrets to GCP Secret Manager for Cloud Run

set -e

PROJECT_ID="vaga-linkedin"
ENV_FILE=".env.production"

echo "🔐 Deploying secrets to GCP Secret Manager..."

# Função para criar secret
create_secret() {
    local secret_name=$1
    local secret_value=$2
    
    echo "Creating secret: $secret_name"
    
    # Verificar se o secret já existe
    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" >/dev/null 2>&1; then
        echo "Secret $secret_name exists, updating..."
        echo -n "$secret_value" | gcloud secrets versions add "$secret_name" --data-file=- --project="$PROJECT_ID"
    else
        echo "Creating new secret $secret_name..."
        echo -n "$secret_value" | gcloud secrets create "$secret_name" --data-file=- --project="$PROJECT_ID"
    fi
}

# Ler arquivo .env.production e criar secrets
while IFS='=' read -r key value; do
    # Ignorar linhas vazias e comentários
    if [[ $key =~ ^#.*$ ]] || [[ -z $key ]]; then
        continue
    fi
    
    # Remover espaços
    key=$(echo $key | xargs)
    value=$(echo $value | xargs)
    
    # Pular se valor estiver vazio
    if [[ -z $value ]]; then
        continue
    fi
    
    # Criar secret no formato lowercase com hífens
    secret_name=$(echo $key | tr '[:upper:]' '[:lower:]' | tr '_' '-')
    
    create_secret "$secret_name" "$value"
    
done < "$ENV_FILE"

echo "✅ All secrets deployed to GCP Secret Manager!"

# Listar secrets criados
echo ""
echo "📋 Secrets created:"
gcloud secrets list --project="$PROJECT_ID" --filter="name~vaga-linkedin"
