# 🎯 Produção vs Desenvolvimento

## ✅ ARQUIVOS EM PRODUÇÃO (Raiz do Projeto)

### **Código Principal**
- `main.py` - Entry point do pipeline
- `agent_chat.py` - Agent Chat (notificações Telegram)
- `app_production/` - Aplicação Cloud Run
- `agents/` - Agentes (extract, load, transform, viz)

### **Infraestrutura & DevOps**
- `terraform/` - Infraestrutura GCP/Databricks
- `.github/workflows/` - CI/CD pipelines
- `Dockerfile` - Build da imagem
- `.dockerignore` - Exclusões do build

### **Configuração**
- `requirements.txt` - Dependências Python
- `.env`, `.env.example` - Variáveis de ambiente
- `.flake8`, `pyproject.toml`, `pytest.ini` - Quality gates
- `.gitignore` - Exclusões do Git

### **Documentação**
- `Readme.md` - Documentação principal
- `DEVOPS_*.md` - Documentação DevOps
- `RAPIDAPI_SETUP.md` - Setup RapidAPI

### **Testes (Estruturados)**
- `tests/` - Testes unitários organizados

---

## 🧪 ARQUIVOS DE DESENVOLVIMENTO (desenvolvimento/)

Códigos usados apenas para desenvolver/testar, **NÃO em produção**:
- `scripts_teste/` - Scripts de teste/debug/verificação
- `notebooks_experimentais/` - Notebooks Databricks experimentais
- `config_experimentais/` - Configs testadas mas não usadas
- `logs/` - Logs e outputs de desenvolvimento
- `deprecated/` - Código obsoleto

---

## 🚀 Como o CI/CD Funciona (GitHub → Cloud Run)

```
1. git push origin main
   ↓
2. GitHub Actions dispara (ci-cd-pipeline.yml)
   ↓
3. gcloud builds submit (cria imagem Docker)
   ↓
4. gcloud run jobs update (atualiza Cloud Run)
   ↓
5. Próxima execução usa nova imagem
```

**NÃO usa Terraform para deploy contínuo!**
- Terraform: Cria infraestrutura inicial
- gcloud: Faz deploys contínuos

---

## 📊 Resumo

| Item | Produção | Desenvolvimento |
|------|----------|-----------------|
| **Código** | `main.py`, `agent_chat.py`, `app_production/` | `scripts_teste/`, notebooks |
| **Infra** | `terraform/`, `.github/workflows/` | terraform experimental |
| **Config** | `.env`, `requirements.txt` | configs experimentais |
| **Docs** | `Readme.md`, `DEVOPS_*.md` | docs antigas |
| **Testes** | `tests/` (estruturado) | `test_*.py` (ad-hoc) |

---

**Status:** ✅ Projeto organizado e pronto para produção!
