-- =============================================================================
-- CRIAÇÃO DE VOLUMES E TABELAS RAW NO UNITY CATALOG
-- Execute este script no Databricks SQL Warehouse ou Notebook
-- =============================================================================

-- Catalog: vagas_linkedin (deve existir com managed location)
-- Schemas: data_analytics_raw, data_engineer_raw, digital_analytics_raw
-- External Location: gs://linkedin-dados-raw/temp_gcs_data/

-- =============================================================================
-- VOLUMES RAW - Apontam para o GCS storage
-- =============================================================================

-- Volume para Data Analytics
CREATE VOLUME IF NOT EXISTS vagas_linkedin.data_analytics_raw.linkedin_data_volume
USING 'gs://linkedin-dados-raw/data_analytics/'
COMMENT 'Volume para dados JSON Data Analytics do LinkedIn no GCS';

-- Volume para Data Engineer  
CREATE VOLUME IF NOT EXISTS vagas_linkedin.data_engineer_raw.linkedin_data_volume
USING 'gs://linkedin-dados-raw/data_engineer/'
COMMENT 'Volume para dados JSON Data Engineer do LinkedIn no GCS';

-- Volume para Digital Analytics
CREATE VOLUME IF NOT EXISTS vagas_linkedin.digital_analytics_raw.linkedin_data_volume
USING 'gs://linkedin-dados-raw/digital_analytics/'
COMMENT 'Volume para dados JSON Digital Analytics do LinkedIn no GCS';

-- =============================================================================
-- TABELAS RAW - Referenciam os volumes criados
-- =============================================================================

-- Tabela Data Analytics usando volume
CREATE TABLE IF NOT EXISTS vagas_linkedin.data_analytics_raw.jobs_data_analytics
USING JSON
OPTIONS (
  path '/Volumes/vagas_linkedin/data_analytics_raw/linkedin_data_volume/*.json',
  multiline 'true'
)
COMMENT 'Tabela RAW para dados Data Analytics extraídos do LinkedIn via volume'
TBLPROPERTIES (
  'layer' = 'raw',
  'domain' = 'data_analytics',
  'source' = 'linkedin',
  'format' = 'json',
  'created_by' = 'load_agent_cli',
  'created_at' = '2025-09-03T17:10:00Z',
  'volume_path' = '/Volumes/vagas_linkedin/data_analytics_raw/linkedin_data_volume/'
);

-- Tabela Data Engineer usando volume
CREATE TABLE IF NOT EXISTS vagas_linkedin.data_engineer_raw.jobs_data_engineer
USING JSON
OPTIONS (
  path '/Volumes/vagas_linkedin/data_engineer_raw/linkedin_data_volume/*.json',
  multiline 'true'
)
COMMENT 'Tabela RAW para dados Data Engineer extraídos do LinkedIn via volume'
TBLPROPERTIES (
  'layer' = 'raw',
  'domain' = 'data_engineer',
  'source' = 'linkedin',
  'format' = 'json',
  'created_by' = 'load_agent_cli',
  'created_at' = '2025-09-03T17:10:00Z',
  'volume_path' = '/Volumes/vagas_linkedin/data_engineer_raw/linkedin_data_volume/'
);

-- Tabela Digital Analytics usando volume
CREATE TABLE IF NOT EXISTS vagas_linkedin.digital_analytics_raw.jobs_digital_analytics
USING JSON
OPTIONS (
  path '/Volumes/vagas_linkedin/digital_analytics_raw/linkedin_data_volume/*.json',
  multiline 'true'
)
COMMENT 'Tabela RAW para dados Digital Analytics extraídos do LinkedIn via volume'
TBLPROPERTIES (
  'layer' = 'raw',
  'domain' = 'digital_analytics',
  'source' = 'linkedin',
  'format' = 'json',
  'created_by' = 'load_agent_cli',
  'created_at' = '2025-09-03T17:10:00Z',
  'volume_path' = '/Volumes/vagas_linkedin/digital_analytics_raw/linkedin_data_volume/'
);

-- =============================================================================
-- VERIFICAÇÃO DOS VOLUMES E TABELAS CRIADAS
-- =============================================================================

-- Listar volumes criados
SHOW VOLUMES IN vagas_linkedin.data_analytics_raw;
SHOW VOLUMES IN vagas_linkedin.data_engineer_raw;
SHOW VOLUMES IN vagas_linkedin.digital_analytics_raw;

-- Listar tabelas criadas
SHOW TABLES IN vagas_linkedin.data_analytics_raw;
SHOW TABLES IN vagas_linkedin.data_engineer_raw;
SHOW TABLES IN vagas_linkedin.digital_analytics_raw;

-- Verificar estrutura das tabelas
DESCRIBE EXTENDED vagas_linkedin.data_analytics_raw.jobs_data_analytics;
DESCRIBE EXTENDED vagas_linkedin.data_engineer_raw.jobs_data_engineer;
DESCRIBE EXTENDED vagas_linkedin.digital_analytics_raw.jobs_digital_analytics;

-- Listar arquivos dentro dos volumes (validar GCS sync)
LIST '/Volumes/vagas_linkedin/data_analytics_raw/linkedin_data_volume/';
LIST '/Volumes/vagas_linkedin/data_engineer_raw/linkedin_data_volume/';
LIST '/Volumes/vagas_linkedin/digital_analytics_raw/linkedin_data_volume/';

-- Contar registros (teste de conectividade via volumes)
SELECT COUNT(*) as total_data_analytics FROM vagas_linkedin.data_analytics_raw.jobs_data_analytics;
SELECT COUNT(*) as total_data_engineer FROM vagas_linkedin.data_engineer_raw.jobs_data_engineer;
SELECT COUNT(*) as total_digital_analytics FROM vagas_linkedin.digital_analytics_raw.jobs_digital_analytics;

-- Query de exemplo para visualizar dados via volumes
SELECT * FROM vagas_linkedin.data_analytics_raw.jobs_data_analytics LIMIT 5;
