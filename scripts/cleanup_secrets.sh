#!/bin/bash
# Script para remover secrets desnecessários do GCP Secret Manager
# Economiza ~65% de custos mantendo apenas secrets essenciais

PROJECT_ID="vaga-linkedin"

echo "🧹 Limpeza de Secrets Desnecessários no GCP Secret Manager"
echo "=========================================================="
echo ""
echo "⚠️  ATENÇÃO: Este script removerá 17 secrets do projeto $PROJECT_ID"
echo "✅ Secrets que serão MANTIDOS (9 essenciais):"
echo "   - google-application-credentials"
echo "   - linkedin-email"
echo "   - linkedin-password"
echo "   - openai-api-key"
echo "   - rapidapi-key"
echo "   - telegram-bot-token"
echo "   - telegram-chat-id"
echo "   - email-user"
echo "   - email-pass"
echo ""
echo "❌ Secrets que serão REMOVIDOS (17 desnecessários):"

# Array de secrets para remover
SECRETS_TO_DELETE=(
    "java-home"
    "spark-home"
    "pyspark-python"
    "pyspark-driver-python"
    "uri-gsutil"
    "gcp-bucket-name"
    "gcp-project-id"
    "url-console-cloud"
    "email-host"
    "email-port"
    "email-from"
    "email-to"
    "quality-email-alerts"
    "port"
    "environment"
    "log-level"
    "enable-kafka"
)

# Listar secrets a serem removidos
for secret in "${SECRETS_TO_DELETE[@]}"; do
    echo "   - $secret"
done

echo ""
read -p "Deseja continuar com a remoção? (sim/NAO): " CONFIRM

if [ "$CONFIRM" != "sim" ]; then
    echo "❌ Operação cancelada pelo usuário"
    exit 0
fi

echo ""
echo "🗑️  Removendo secrets..."
echo ""

REMOVED_COUNT=0
FAILED_COUNT=0

for secret in "${SECRETS_TO_DELETE[@]}"; do
    echo -n "Removendo $secret... "
    
    if gcloud secrets delete "$secret" --project="$PROJECT_ID" --quiet 2>/dev/null; then
        echo "✅ OK"
        ((REMOVED_COUNT++))
    else
        echo "⚠️  FALHOU (pode já ter sido removido)"
        ((FAILED_COUNT++))
    fi
done

echo ""
echo "=========================================================="
echo "✅ Limpeza concluída!"
echo "   - Removidos com sucesso: $REMOVED_COUNT"
echo "   - Falhas/Já removidos: $FAILED_COUNT"
echo ""
echo "💰 Economia estimada: ~\$1.02/mês"
echo ""
echo "📝 Secrets remanescentes (essenciais):"
gcloud secrets list --project="$PROJECT_ID" --format="value(name)" | sort

echo ""
echo "✅ Use variáveis de ambiente (.env) para configs não-sensíveis"
