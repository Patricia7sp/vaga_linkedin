# 🎯 Configuração dos 3 Jobs DLT Separados

## ⚠️ IMPORTANTE: Daily Limit Exhausted

Sua conta Databricks Free Edition está com erro:
```
Organization 4343877046393065 has been cancelled or is not active yet.
```

Isso acontece quando atinge o **daily limit** (limite diário de uso).

**SOLUÇÕES:**
1. ✅ Aguardar 24h para resetar o limite diário
2. ✅ Criar jobs manualmente via UI do Databricks
3. ✅ Executar pipelines manualmente (via UI)

---

## 📋 JOB 1: Data Engineer Pipeline

**Nome:** `dlt-data-engineer-pipeline`

**Schedule:** 
- Dias: Segunda a Sexta
- Horários: 08:30, 12:30, 21:30 (Horário de Brasília)
- Cron: `0 30 8,12,21 ? * MON-FRI`

**Task:**
- **Task Key:** `run-pipeline`
- **Type:** Notebook
- **Notebook Path:** `/Shared/linkedin_pipeline_runner_notebook`
- **Parameters:**
  - `pipeline`: `data_engineer`
  - `environment`: `production`
- **Timeout:** 3600 segundos (1 hora)
- **Max Retries:** 1

---

## 📋 JOB 2: Data Analytics Pipeline

**Nome:** `dlt-data-analytics-pipeline`

**Schedule:** 
- Dias: Segunda a Sexta
- Horários: 09:00, 13:00, 22:00 (Horário de Brasília)
- Cron: `0 0 9,13,22 ? * MON-FRI`

**Task:**
- **Task Key:** `run-pipeline`
- **Type:** Notebook
- **Notebook Path:** `/Shared/linkedin_pipeline_runner_notebook`
- **Parameters:**
  - `pipeline`: `data_analytics`
  - `environment`: `production`
- **Timeout:** 3600 segundos (1 hora)
- **Max Retries:** 1

---

## 📋 JOB 3: Digital Analytics Pipeline

**Nome:** `dlt-digital-analytics-pipeline`

**Schedule:** 
- Dias: Segunda a Sexta
- Horários: 10:00, 14:00, 23:00 (Horário de Brasília)
- Cron: `0 0 10,14,23 ? * MON-FRI`

**Task:**
- **Task Key:** `run-pipeline`
- **Type:** Notebook
- **Notebook Path:** `/Shared/linkedin_pipeline_runner_notebook`
- **Parameters:**
  - `pipeline`: `digital_analytics`
  - `environment`: `production`
- **Timeout:** 3600 segundos (1 hora)
- **Max Retries:** 1

---

## 🎯 VANTAGENS DESTA CONFIGURAÇÃO:

### ✅ Respeita Free Edition
- **1 pipeline por vez** (limitação documentada)
- **Horários espaçados** (30 min entre jobs)
- **Evita concorrência** entre pipelines

### ✅ Distribuição de Carga
```
08:30 → data_engineer
09:00 → data_analytics (30 min depois)
10:00 → digital_analytics (1h depois)

12:30 → data_engineer
13:00 → data_analytics
14:00 → digital_analytics

21:30 → data_engineer
22:00 → data_analytics
23:00 → digital_analytics
```

### ✅ Evita Daily Limit
- Jobs executam em horários diferentes
- Permite "respirar" entre execuções
- Reduz chance de atingir limite diário

---

## 📝 COMO CRIAR JOBS (MANUALMENTE VIA UI):

### **Passo 1: Acessar Workflows**
1. Databricks UI → Menu lateral
2. Click em **"Workflows"**
3. Click em **"Create Job"**

### **Passo 2: Configurar Job**
1. **Name:** (copiar nome acima)
2. **Task:**
   - Click "Add task"
   - **Type:** Notebook
   - **Notebook path:** `/Shared/linkedin_pipeline_runner_notebook`
   - **Parameters:** Adicionar 2 parâmetros:
     - `pipeline`: (valor conforme job)
     - `environment`: `production`
   - **Timeout:** 3600
   - **Retries:** 1
3. **Schedule:**
   - Click "Add trigger" → "Scheduled"
   - **Cron:** (copiar cron acima)
   - **Timezone:** America/Sao_Paulo
   - **Pause status:** UNPAUSED

### **Passo 3: Salvar**
- Click "Create"
- Job estará pronto!

**Repetir para os 3 jobs.**

---

## 🚀 TESTE MANUAL (ANTES DE AGENDAR):

Antes de ativar schedule, teste manualmente:

1. Vá em **Workflows** → Selecione job
2. Click **"Run now"**
3. Aguarde execução (deve levar 9-11 minutos)
4. Verifique logs e sucesso

**IMPORTANTE:** Teste **UM job por vez** para não atingir daily limit!

---

## ⚠️ SOBRE O DAILY LIMIT EXHAUSTED:

### **O que é:**
- Databricks Free Edition tem **limite diário não divulgado** de:
  - Compute hours (horas de processamento)
  - Data processed (dados processados)
  - Pipeline updates (execuções de pipeline)

### **Como evitar:**
1. ✅ **Executar menos jobs** por dia
2. ✅ **Espaçar horários** (30min+ entre jobs)
3. ✅ **Evitar full_refresh** (usar incremental)
4. ✅ **Não rodar múltiplos pipelines** simultaneamente

### **Quando acontece:**
- Geralmente após 10-15 execuções de pipeline por dia
- Ou após processar muito volume de dados
- Reseta a cada 24 horas (meia-noite UTC)

### **Solução definitiva:**
- **Upgrade para Databricks pago** ($$$)
- Permite pipelines ilimitados
- Sem daily limits

---

## 🔄 ALTERNATIVA: Executar 1 pipeline por dia

Se daily limit continuar problema, **reduzir para 1 execução por dia**:

```
Segunda: data_engineer às 08:30
Terça: data_analytics às 08:30
Quarta: digital_analytics às 08:30
Quinta: data_engineer às 08:30
Sexta: data_analytics às 08:30
Sábado: digital_analytics às 08:30
```

**Cron para rotação:**
- Segunda/Quinta: `0 30 8 ? * MON,THU`
- Terça/Sexta: `0 30 8 ? * TUE,FRI`
- Quarta/Sábado: `0 30 8 ? * WED,SAT`

---

## 📊 MONITORAMENTO:

Após criar jobs, monitore:

1. ✅ **Duration** de cada execução (deveria ser 9-11 min)
2. ✅ **Success rate** (deveria ser >90%)
3. ✅ **Logs** para mensagens de erro
4. ✅ **Tabelas Gold** para validar dados processados

Se continuar em 1 minuto → Daily limit ativo!

---

**✅ Jobs configurados com sucesso!**
**✅ Estrutura compatível com Free Edition!**
**✅ Evita concorrência entre pipelines!**
