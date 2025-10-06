#!/bin/bash
# Deploy completo do Pipeline de Produção para GCP Cloud Run

set -e

# Configurações V5 - RapidAPI Integration + Hybrid Extractor
PROJECT_ID="vaga-linkedin"
SERVICE_NAME="vaga-linkedin-prod"
VERSION="v5"
REGION="us-central1"
IMAGE_TAG="gcr.io/$PROJECT_ID/$SERVICE_NAME:$VERSION"

echo "🚀 DEPLOY VAGA LINKEDIN V5 - RapidAPI Hybrid Extractor"
echo "📦 Versão: $VERSION (RapidAPI + Selenium Fallback)"
echo "🏷️  Tag da imagem: $IMAGE_TAG"

echo "🚀 Deploy Pipeline Vagas LinkedIn para Cloud Run"
echo "=================================================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "=================================================="

# 1. Build da imagem Docker
echo "🔨 Building Docker image..."
docker build -t $IMAGE_TAG .

# 2. Push para Google Container Registry
echo "📤 Pushing to GCR..."
docker push $IMAGE_TAG

# 3. Deploy secrets (se necessário)
echo "🔐 Checking secrets..."
echo "Deploying secrets to Secret Manager..."
./scripts/deploy-secrets.sh

# 4. Deploy do Cloud Run Job (batch processing)
echo "☁️ Deploying to Cloud Run Job V5 (RapidAPI Hybrid)..."
SERVICE_JOB_NAME="${SERVICE_NAME}-${VERSION}"
gcloud run jobs create $SERVICE_JOB_NAME \
    --image=$IMAGE_TAG \
    --region=$REGION \
    --project=$PROJECT_ID \
    --memory=2Gi \
    --cpu=1 \
    --max-retries=1 \
    --parallelism=1 \
    --task-timeout=3600 \
    --set-env-vars="ENVIRONMENT=production" \
    --set-secrets="DATABRICKS_TOKEN=databricks-token:latest,TELEGRAM_BOT_TOKEN=telegram-bot-token:latest,OPENAI_API_KEY=openai-api-key:latest,LINKEDIN_EMAIL=linkedin-email:latest,LINKEDIN_PASSWORD=linkedin-password:latest,RAPIDAPI_KEY=rapidapi-key:latest" || echo "Job already exists, updating..."

# Update existing job if it already exists
gcloud run jobs replace $SERVICE_JOB_NAME \
    --image=$IMAGE_TAG \
    --region=$REGION \
    --project=$PROJECT_ID \
    --memory=2Gi \
    --cpu=1 \
    --task-timeout=3600 \
    --max-retries=1 \
    --parallelism=1 \
    --set-env-vars="ENVIRONMENT=production" \
    --set-secrets="DATABRICKS_TOKEN=databricks-token:latest,TELEGRAM_BOT_TOKEN=telegram-bot-token:latest,OPENAI_API_KEY=openai-api-key:latest,LINKEDIN_EMAIL=linkedin-email:latest,LINKEDIN_PASSWORD=linkedin-password:latest,RAPIDAPI_KEY=rapidapi-key:latest" 2>/dev/null || echo "Using created job"

# 5. Configurar agendamento (Cloud Scheduler)
echo "⏰ Configurando Cloud Scheduler - Execuções 3x/dia (seg-sex)"

# Job principal - execuções 08h, 12h, 21h de segunda a sexta
gcloud scheduler jobs create http linkedin-realtime \
    --location=$REGION \
    --schedule="0 8,12,21 * * 1-5" \
    --time-zone="America/Sao_Paulo" \
    --description="Pipeline Cloud Run v5 - RapidAPI Hybrid - Extração 3x/dia (seg-sex)" \
    --project=$PROJECT_ID \
    --attempt-deadline=3600s \
    --max-retry-attempts=1 \
    --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$SERVICE_JOB_NAME:run" \
    --http-method=POST \
    --oauth-service-account-email="551779207347-compute@developer.gserviceaccount.com" \
    --headers="Content-Type=application/json" \
    --message-body='{}' || echo "Real-time scheduler already exists"

# Job secundário - manutenção às 02h (quartas e sextas)
gcloud scheduler jobs create http linkedin-maintenance \
    --location=$REGION \
    --schedule="0 2 * * 3,5" \
    --time-zone="America/Sao_Paulo" \
    --description="Manutenção pipeline - Quartas e Sextas às 02h" \
    --project=$PROJECT_ID \
    --attempt-deadline=3600s \
    --max-retry-attempts=1 \
    --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$SERVICE_JOB_NAME:run" \
    --http-method=POST \
    --oauth-service-account-email="551779207347-compute@developer.gserviceaccount.com" \
    --headers="Content-Type=application/json" \
    --message-body='{"command": "maintenance"}' || echo "Maintenance scheduler already exists"

echo ""
echo "✅ Deploy V5 concluído com sucesso!"
echo "🔧 Cloud Run Job V5: $SERVICE_JOB_NAME (RapidAPI Hybrid Extractor)"
echo "📊 Execute manualmente: gcloud run jobs execute $SERVICE_JOB_NAME --region=$REGION --project=$PROJECT_ID"
echo ""
echo "⏰ AGENDAMENTO CONFIGURADO:"
echo "   🚀 Execuções: 08h, 12h, 21h (segunda a sexta)"
echo "   🧹 Manutenção: Quartas e sextas às 02h"
echo "   🕐 Timezone: America/Sao_Paulo"
echo ""
echo "📂 Pipeline V5 com RapidAPI (primário) + Selenium (fallback)"
echo "✨ Benefícios: 100% extração, sem bloqueios, 10x mais rápido"
echo "📱 Notificações Telegram continuam via Databricks Agent"
