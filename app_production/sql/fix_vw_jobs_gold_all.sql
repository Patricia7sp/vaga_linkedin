-- ============================================================================
-- CORREÇÃO DA VIEW vw_jobs_gold_all
-- ============================================================================
-- PROBLEMA: posted_time_ts pode ser NULL, fazendo com que vagas novas não
--           apareçam na view quando filtradas por data
-- 
-- SOLUÇÃO: Adicionar campo effective_posted_time que usa COALESCE para
--          garantir que sempre há uma data válida
-- ============================================================================

CREATE OR REPLACE VIEW vagas_linkedin.viz.vw_jobs_gold_all AS
SELECT 
    'data_engineer' AS domain,
    job_id,
    title,
    company,
    city,
    state,
    country,
    location_tier,
    category,
    search_term,
    work_modality,
    contract_type,
    salary_min,
    salary_max,
    salary_range,
    has_salary_info,
    is_premium_salary,
    posted_time_ts,
    is_recent_posting,
    description_quality_score,
    url,
    ingestion_timestamp,
    -- NOVO CAMPO: usa posted_time_ts se disponível, senão usa ingestion_timestamp
    COALESCE(posted_time_ts, ingestion_timestamp) as effective_posted_time
FROM vagas_linkedin.data_engineer_dlt.data_engineer_gold

UNION ALL

SELECT 
    'data_analytics' AS domain,
    job_id,
    title,
    company,
    city,
    state,
    country,
    location_tier,
    category,
    search_term,
    work_modality,
    contract_type,
    salary_min,
    salary_max,
    salary_range,
    has_salary_info,
    is_premium_salary,
    posted_time_ts,
    is_recent_posting,
    description_quality_score,
    url,
    ingestion_timestamp,
    COALESCE(posted_time_ts, ingestion_timestamp) as effective_posted_time
FROM vagas_linkedin.data_analytics_dlt.data_analytics_gold

UNION ALL

SELECT 
    'digital_analytics' AS domain,
    job_id,
    title,
    company,
    city,
    state,
    country,
    location_tier,
    category,
    search_term,
    work_modality,
    contract_type,
    salary_min,
    salary_max,
    salary_range,
    has_salary_info,
    is_premium_salary,
    posted_time_ts,
    is_recent_posting,
    description_quality_score,
    url,
    ingestion_timestamp,
    COALESCE(posted_time_ts, ingestion_timestamp) as effective_posted_time
FROM vagas_linkedin.digital_analytics_dlt.digital_analytics_gold;

-- ============================================================================
-- OBSERVAÇÕES:
-- ============================================================================
-- 1. effective_posted_time SEMPRE terá um valor (nunca NULL)
-- 2. Agent Chat deve filtrar por effective_posted_time ao invés de posted_time_ts
-- 3. Isso garante que vagas novas sejam identificadas mesmo se posted_time_ts for NULL
-- 4. O fallback para ingestion_timestamp garante que vagas recém-ingeridas apareçam
-- ============================================================================
