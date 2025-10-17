# 🚀 DevOps Quick Start Guide

## 📋 Configuração Inicial

### 1. Configurar GitHub Secrets

Acesse: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

Adicione os seguintes secrets:

```bash
GCP_SA_KEY              # Service Account JSON do GCP
DATABRICKS_HOST         # https://dbc-14d16b60-2882.cloud.databricks.com
DATABRICKS_TOKEN        # Token de acesso do Databricks
RAPIDAPI_KEY            # Chave da RapidAPI
TELEGRAM_BOT_TOKEN      # Token do bot Telegram
TELEGRAM_CHAT_ID        # ID do chat Telegram
SLACK_WEBHOOK           # Webhook do Slack (opcional)
CODECOV_TOKEN           # Token do Codecov (opcional)
```

### 2. Configurar GitHub Environments

Crie 3 environments em `Settings` → `Environments`:

**Development:**
- Nome: `development`
- Protection rules: Nenhuma
- Secrets: Usar secrets de dev

**Staging:**
- Nome: `staging`
- Protection rules: Nenhuma
- Secrets: Usar secrets de staging

**Production:**
- Nome: `production`
- Protection rules: ✅ Required reviewers (1-2 pessoas)
- Secrets: Usar secrets de produção

---

## 🔄 Workflow de Desenvolvimento

### Branch Strategy

```
main (production)
  ↑
  └── develop (staging)
        ↑
        └── feature/nova-funcionalidade
```

### Fluxo Completo

1. **Criar feature branch:**
```bash
git checkout develop
git pull origin develop
git checkout -b feature/minha-feature
```

2. **Desenvolver e testar localmente:**
```bash
# Instalar dependências
pip install -r requirements.txt
pip install -r app_production/requirements.txt

# Rodar testes localmente
pytest tests/unit/ -v

# Verificar code quality
black --check app_production/ agents/
flake8 app_production/ agents/
```

3. **Commit e push:**
```bash
git add .
git commit -m "feat: adiciona nova funcionalidade"
git push origin feature/minha-feature
```

4. **Criar Pull Request:**
- Abrir PR de `feature/minha-feature` → `develop`
- Pipeline CI/CD será executado automaticamente
- Aguardar aprovação e merge

5. **Deploy automático para DEV:**
- Após merge em `develop`, deploy automático para ambiente DEV

6. **Promover para STAGING:**
```bash
git checkout main
git pull origin main
git merge develop
git push origin main
```
- Deploy automático para STAGING
- Smoke tests executados automaticamente

7. **Deploy para PRODUCTION:**
- Acesse GitHub Actions
- Execute workflow `CI/CD Pipeline`
- Selecione `environment: prod`
- **Aprovação manual necessária**
- Deploy para produção

---

## 🧪 Executar Testes Localmente

### Todos os testes:
```bash
pytest tests/ -v
```

### Apenas unit tests:
```bash
pytest tests/unit/ -v
```

### Com coverage:
```bash
pytest tests/ --cov=app_production --cov=agents --cov-report=html
open htmlcov/index.html
```

### Testes específicos:
```bash
pytest tests/unit/test_rapidapi_extractor.py -v
```

### Testes por marker:
```bash
pytest -m unit          # Apenas unit tests
pytest -m integration   # Apenas integration tests
pytest -m "not slow"    # Excluir testes lentos
```

---

## 🔍 Code Quality Local

### Black (formatting):
```bash
black app_production/ agents/
```

### isort (imports):
```bash
isort app_production/ agents/
```

### Flake8 (linting):
```bash
flake8 app_production/ agents/
```

### MyPy (type checking):
```bash
mypy app_production/agents/ --ignore-missing-imports
```

### Bandit (security):
```bash
bandit -r app_production/ agents/
```

### Executar tudo de uma vez:
```bash
# Criar script helper
cat > check_quality.sh << 'EOF'
#!/bin/bash
echo "🔍 Running code quality checks..."
black --check app_production/ agents/ && \
isort --check-only app_production/ agents/ && \
flake8 app_production/ agents/ && \
echo "✅ All checks passed!"
EOF

chmod +x check_quality.sh
./check_quality.sh
```

---

## 🏗️ Terraform

### Validar localmente:
```bash
cd terraform
terraform fmt -recursive
terraform init
terraform validate
terraform plan
```

### Deploy manual (emergência):
```bash
cd terraform
terraform apply
```

---

## 🐳 Docker

### Build local:
```bash
cd app_production
docker build -t vaga-linkedin-prod:local .
```

### Testar container localmente:
```bash
docker run --rm \
  -e RAPIDAPI_KEY=$RAPIDAPI_KEY \
  -e DATABRICKS_TOKEN=$DATABRICKS_TOKEN \
  vaga-linkedin-prod:local
```

### Scan de segurança:
```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image vaga-linkedin-prod:local
```

---

## 📊 Monitoramento

### Ver logs do Cloud Run:
```bash
gcloud logging read "resource.type=cloud_run_job" \
  --limit=100 \
  --project=vaga-linkedin
```

### Ver status do job:
```bash
gcloud run jobs describe vaga-linkedin-prod-v5 \
  --region=us-central1 \
  --project=vaga-linkedin
```

### Ver execuções recentes:
```bash
gcloud run jobs executions list \
  --job=vaga-linkedin-prod-v5 \
  --region=us-central1 \
  --project=vaga-linkedin
```

---

## 🚨 Troubleshooting

### Pipeline falhou no stage de testes:
1. Ver logs no GitHub Actions
2. Executar testes localmente: `pytest tests/ -v`
3. Corrigir erros
4. Commit e push novamente

### Pipeline falhou no deploy:
1. Verificar secrets do GitHub
2. Verificar permissões do Service Account
3. Ver logs do Cloud Build
4. Rollback se necessário

### Rollback de produção:
```bash
# Ver versões anteriores
gcloud container images list-tags gcr.io/vaga-linkedin/vaga-linkedin-prod

# Fazer rollback para versão anterior
gcloud run jobs update vaga-linkedin-prod-v5 \
  --image=gcr.io/vaga-linkedin/vaga-linkedin-prod:v5-COMMIT_ANTERIOR \
  --region=us-central1 \
  --project=vaga-linkedin
```

---

## 📚 Recursos Úteis

- **GitHub Actions**: https://github.com/Patricia7sp/vaga_linkedin/actions
- **Cloud Run Console**: https://console.cloud.google.com/run?project=vaga-linkedin
- **Databricks**: https://dbc-14d16b60-2882.cloud.databricks.com
- **Codecov**: https://codecov.io/gh/Patricia7sp/vaga_linkedin

---

## ✅ Checklist Pré-Deploy

Antes de fazer deploy para produção, verifique:

- [ ] Todos os testes passando
- [ ] Code coverage > 70%
- [ ] Code quality checks passando
- [ ] Terraform validado
- [ ] Docker image escaneada (sem vulnerabilidades críticas)
- [ ] Smoke tests passando em staging
- [ ] Documentação atualizada
- [ ] Changelog atualizado
- [ ] Aprovação do time

---

## 🎓 Próximos Passos

1. ✅ Configurar secrets no GitHub
2. ✅ Criar environments (dev/staging/prod)
3. ✅ Fazer primeiro PR para testar pipeline
4. ✅ Validar deploy em DEV
5. ✅ Validar deploy em STAGING
6. ✅ Deploy em PRODUCTION

---

**Dúvidas?** Consulte o [DEVOPS_PLAN.md](./DEVOPS_PLAN.md) para mais detalhes.
