# 📧 Configuração Gmail para Notificações CI/CD

## 🔐 Secrets Necessários no GitHub

Adicione os seguintes secrets em:
`https://github.com/Patricia7sp/vaga_linkedin/settings/secrets/actions`

### 1. **GMAIL_USERNAME**
Seu email completo do Gmail
```
exemplo: seu.email@gmail.com
```

### 2. **GMAIL_APP_PASSWORD**
**NÃO use sua senha normal!** Use uma App Password:

**Como gerar:**
1. Acesse: https://myaccount.google.com/apppasswords
2. Nome do app: "GitHub Actions"
3. Copie a senha de 16 caracteres gerada
4. Cole no secret `GMAIL_APP_PASSWORD`

### 3. **NOTIFICATION_EMAIL**
Email que receberá as notificações (pode ser o mesmo)
```
exemplo: seu.email@gmail.com
```

---

## ✅ Secrets Já Existentes (não mexer)

- `GCP_SA_KEY` - Service Account GCP
- `DATABRICKS_HOST` - URL Databricks
- `DATABRICKS_TOKEN` - Token Databricks

---

## 📬 O que Você Receberá

Notificações por email sobre:
- ✅ Deploy em produção (sucesso/falha)
- 🤖 Auto-promoção para produção
- ⚠️ Falhas no pipeline

---

**Atenção:** Se não configurar os secrets de email, o pipeline continuará funcionando, mas não enviará notificações.
