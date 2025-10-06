# 🧠 Etapa 2 – extract_agent com Kafka + PySpark Streaming

Este agente é responsável por capturar dados de vagas do LinkedIn em tempo real, utilizando Apache Kafka como mecanismo de ingestão e PySpark Structured Streaming como motor de processamento. Os dados serão tratados e enviados diretamente para o bucket GCP em arquivos JSON.


## Kafka
Broker local ou remoto (pode usar Docker ou serviço gerenciado).
Criar tópico único: vagas_dados.
Mensagens no tópico devem ser formatadas como JSON com chave "type".

## PySpark
Job PySpark deve:
Ler do tópico Kafka em tempo real.
Filtrar os dados por tipo de vaga.
Escrever em JSON para o caminho no bucket correspondente

## exemplo de script pyspark
```

query = df \
  .filter("type = 'data_engineer'") \
  .writeStream \
  .format("json") \
  .option("path", "gs://linkedin-dados-raw/data_engineer/") \
  .option("checkpointLocation", "/tmp/checkpoints/data_engineer") \
  .start()
```


---

## 🎯 Objetivo Geral

- Conectar à API do LinkedIn utilizando autenticação via token.
- Realizar a extração das vagas com base em três filtros específicos.
- Salvar os dados extraídos em arquivos separados e organizados no bucket GCP.

--

## Tecnologias Utilizadas
- PySpark Structured Streaming
- Apache Kafka
- LinkedIn API ou Web Scraping
- Cloud Storage (GCP)-

## 📚 Bibliotecas Utilizadas
- requests
- json
- os
- subprocess
- time
- datetime
- dotenv    



## 🔍 Filtros de Busca

A busca deverá ser segmentada por três perfis distintos de vaga:

1. **Data Engineer** – Vagas com títulos como “Engenheiro de Dados” ou “Data Engineer”.
2. **Data Analytics** – Vagas com títulos como “Analista de Dados” ou “Data Analytics”.
3. **Digital Analytics** – Vagas relacionadas a métricas digitais, produtos, marketing, etc.

Cada tipo de vaga gerará um **arquivo JSON independente**, nomeado da seguinte forma:

- `data_engineer_<data>.json`
- `data_analytics_<data>.json`
- `digital_analytics_<data>.json`

Exemplo de caminho no bucket:
- gs://linkedin-dados-raw/data_engineer/2025-09-01/data_engineer_2025-09-01.json

## 🔐 Autenticação na API do LinkedIn

O acesso à API oficial do LinkedIn exige:

- Conta de desenvolvedor (via [LinkedIn Developer Portal](https://www.linkedin.com/developers))
- Criação de uma aplicação
- Geração de um **token OAuth 2.0** com os escopos necessários (ex: `r_jobs`, `r_ads`, etc.)

### 🚨 Ponto de atenção:
Caso a API oficial não permita esse tipo de consulta, será necessário utilizar **web scraping responsável** (com limitações de taxa e respeitando os termos de uso).



---

## 🧠 Responsabilidades do `extract_agent`

1. **Autenticar-se** na API do LinkedIn com o token OAuth.
2. Realizar **três requisições separadas**, com base nos filtros definidos.
3. Tratar e organizar os dados brutos: cargo, empresa, localização, data da vaga, link, etc.
4. **Salvar os dados localmente** em JSON.
5. Realizar o **upload dos arquivos para os buckets correspondentes**.
6. Retornar um **resumo estruturado** com:
   - Quantidade de vagas por tipo
   - Caminho dos arquivos no bucket
   - Logs de execução
   - Erros (caso ocorram)

---

## ✅ Validações Esperadas

- Os três arquivos foram criados corretamente?
- Foram salvos no bucket correto e com data correspondente?
- Houve sucesso na autenticação com a API do LinkedIn?
- A estrutura dos dados contém os seguintes campos:
  - `job_title`, `company_name`, `location`, `posted_date`, `job_url`, `description_snippet`

---

## 📎 Pontos de Atenção

- A API do LinkedIn pode limitar o número de requisições por hora.
- Os tokens OAuth expiram — o agente deve verificar e renovar se necessário.
- Se scraping for usado como fallback, respeitar o `robots.txt` e limitar o número de requisições (delay de 2–5 segundos entre requisições).
- Armazenar os arquivos com **timestamp diário** para controle histórico.
- Verificar se os arquivos não estão vazios antes de subir.

---

## 🧪 Logs e Saída Esperada

Formato JSON de resposta:

```json
{
  "kafka_status": "OK",
  "spark_streaming_status": "RUNNING",
  "outputs": {
    "data_engineer": {
      "count": 102,
      "path": "gs://linkedin-dados-raw/data_engineer/..."
    },
    "data_analytics": {
      "count": 86,
      "path": "gs://linkedin-dados-raw/data_analytics/..."
    },
    "digital_analytics": {
      "count": 47,
      "path": "gs://linkedin-dados-raw/digital_analytics/..."
    }
  }
}

``` 

## 📤 Saída Esperada

- JSON com os nomes e status dos recursos criados.
- Logs de execução do Terraform.    



 
## Responsabilidades Atualizadas do extract_agent

Iniciar e manter o producer Kafka alimentando o tópico vagas_dados.
Validar a autenticação com a API do LinkedIn (ou fallback scraping).
Rodar o PySpark Structured Streaming job que:
Consome o tópico vagas_dados
Processa as mensagens em tempo real
Salva os dados separados por tipo em buckets no GCP
Garantir consistência do schema e salvar em formato JSON.
Retornar relatório de execução com:
Contagem de mensagens por tipo
Caminhos de saída
Status dos jobs


## 📚 Pontos de Atenção Reforçados
- O PySpark Structured Streaming deve ser tolerante a falhas (uso de checkpoint).
- O Kafka deve ter política de retenção compatível com frequência de consumo. 

## ✅ Checklist Final da Etapa

- Kafka Broker iniciado e tópico vagas_dados criado
- Producer está enviando mensagens formatadas corretamente
- PySpark Structured Streaming está rodando e processando sem erro
- Arquivos estão sendo salvos no bucket GCP com nomes e partições corretas
- Logs e status do job retornados ao control_agent