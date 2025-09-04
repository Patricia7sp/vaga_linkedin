#!/usr/bin/env python3
"""
Sistema de alertas Kafka em tempo real para vagas novas do LinkedIn
"""
import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))
load_dotenv()

from agents.extract_agent.extract_agent import extract_jobs_via_linkedin_scraping, check_for_new_jobs

def setup_kafka_real_time_monitoring():
    """
    Configura monitoramento em tempo real com Kafka para vagas novas
    """
    try:
        from kafka import KafkaProducer
        
        # Configuração Kafka
        kafka_config = {
            'bootstrap_servers': ['localhost:9092'],
            'value_serializer': lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
            'key_serializer': lambda k: k.encode('utf-8') if k else None
        }
        
        producer = KafkaProducer(**kafka_config)
        print("✅ Kafka Producer configurado para alertas em tempo real")
        return producer
        
    except ImportError:
        print("⚠️ Kafka não disponível - usando modo offline")
        return None
    except Exception as e:
        print(f"❌ Erro ao configurar Kafka: {e}")
        return None

def send_new_job_alert(producer, job, category):
    """
    Envia alerta Kafka para vaga nova detectada
    """
    try:
        if not producer:
            return False
            
        # Criar payload do alerta
        alert_payload = {
            'alert_type': 'NEW_JOB',
            'timestamp': datetime.now().isoformat(),
            'category': category,
            'job_data': job,
            'message': f"🚨 Nova vaga detectada: {job.get('title', 'N/A')} - {job.get('company', 'N/A')}",
            'priority': 'HIGH' if any(word in job.get('title', '').lower() for word in ['senior', 'sênior', 'lead']) else 'MEDIUM'
        }
        
        # Enviar para tópico Kafka
        topic_name = f"linkedin_job_alerts_{category}"
        future = producer.send(topic_name, key=category, value=alert_payload)
        
        # Aguardar confirmação
        record_metadata = future.get(timeout=5)
        print(f"🚨 Alerta enviado: {job['title']} ({job['company']}) -> Kafka topic: {topic_name}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar alerta Kafka: {e}")
        return False

def run_real_time_monitoring(check_interval_minutes=15):
    """
    Executa monitoramento em tempo real - verifica vagas novas periodicamente
    """
    print("🔴 INICIANDO MONITORAMENTO EM TEMPO REAL")
    print("=" * 60)
    print(f"⏰ Intervalo de verificação: {check_interval_minutes} minutos")
    print(f"📅 Trabalhando apenas com vagas de HOJE: {datetime.now().strftime('%Y-%m-%d')}")
    print()
    
    # Setup Kafka
    producer = setup_kafka_real_time_monitoring()
    
    # Categorias para monitorar
    categories = {
        'data_engineer': ['Data Engineer', 'Engenheiro de Dados'],
        'data_analytics': ['Data Analytics', 'Analista de Dados'], 
        'digital_analytics': ['Digital Analytics', 'Web Analytics']
    }
    
    # Diretório base para dados de hoje
    today_date = datetime.now().strftime('%Y-%m-%d')
    base_data_dir = f"data_extracts/{today_date}"
    
    cycle_count = 0
    
    try:
        while True:
            cycle_count += 1
            cycle_start = datetime.now()
            
            print(f"\n🔄 CICLO {cycle_count} - {cycle_start.strftime('%H:%M:%S')}")
            print("-" * 50)
            
            total_new_jobs = 0
            
            for category, search_terms in categories.items():
                print(f"\n📂 Verificando categoria: {category.upper()}")
                
                # Extrair vagas atuais
                category_jobs = []
                for search_term in search_terms:
                    jobs = extract_jobs_via_linkedin_scraping(
                        search_term, 
                        max_results=10,  # Menos vagas para monitoramento rápido
                        category=category
                    )
                    if jobs:
                        category_jobs.extend(jobs)
                        print(f"  ✅ {len(jobs)} vagas de '{search_term}'")
                
                if not category_jobs:
                    print(f"  ⚠️ Nenhuma vaga encontrada para {category}")
                    continue
                
                # Verificar vagas novas
                category_data_dir = os.path.join(base_data_dir, category)
                new_jobs = check_for_new_jobs(category_data_dir, category_jobs)
                
                if new_jobs:
                    print(f"  🚨 {len(new_jobs)} VAGAS NOVAS detectadas!")
                    
                    # Salvar vagas novas
                    os.makedirs(category_data_dir, exist_ok=True)
                    filename = f"{category}_{today_date.replace('-', '')}.jsonl"
                    filepath = os.path.join(category_data_dir, filename)
                    
                    with open(filepath, 'a', encoding='utf-8') as f:
                        for job in new_jobs:
                            f.write(json.dumps(job, ensure_ascii=False) + '\n')
                    
                    # Enviar alertas Kafka para cada vaga nova
                    for job in new_jobs:
                        if producer:
                            send_new_job_alert(producer, job, category)
                        print(f"    🆕 {job['title']} - {job['company']} ({job.get('location', 'N/A')})")
                    
                    total_new_jobs += len(new_jobs)
                else:
                    print(f"  ✅ Nenhuma vaga nova (já existem {len(category_jobs)} no storage)")
            
            # Resumo do ciclo
            cycle_end = datetime.now()
            cycle_duration = (cycle_end - cycle_start).total_seconds()
            
            print(f"\n📊 RESUMO CICLO {cycle_count}:")
            print(f"   ⏱️ Duração: {cycle_duration:.1f}s")
            print(f"   🆕 Vagas novas: {total_new_jobs}")
            print(f"   🚨 Alertas enviados: {total_new_jobs if producer else 0}")
            
            if total_new_jobs > 0:
                print(f"   🎯 Próxima verificação em {check_interval_minutes} minutos")
            else:
                print(f"   😴 Nenhuma vaga nova - próxima verificação em {check_interval_minutes} minutos")
            
            # Aguardar próximo ciclo
            time.sleep(check_interval_minutes * 60)
            
    except KeyboardInterrupt:
        print(f"\n🔴 Monitoramento interrompido pelo usuário")
    except Exception as e:
        print(f"\n💥 Erro no monitoramento: {e}")
    finally:
        if producer:
            producer.close()
            print("✅ Kafka Producer fechado")
        
        print(f"📊 Total de ciclos executados: {cycle_count}")

def run_single_check():
    """
    Executa uma única verificação de vagas novas (para testes)
    """
    print("🔍 VERIFICAÇÃO ÚNICA DE VAGAS NOVAS")
    print("=" * 50)
    
    producer = setup_kafka_real_time_monitoring()
    
    categories = {
        'data_engineer': ['Data Engineer'],
        'data_analytics': ['Data Analytics']
    }
    
    today_date = datetime.now().strftime('%Y-%m-%d')
    base_data_dir = f"data_extracts/{today_date}"
    
    total_new = 0
    
    for category, search_terms in categories.items():
        print(f"\n📂 Verificando {category}...")
        
        category_jobs = []
        for search_term in search_terms:
            jobs = extract_jobs_via_linkedin_scraping(search_term, max_results=5, category=category)
            if jobs:
                category_jobs.extend(jobs)
        
        if category_jobs:
            category_data_dir = os.path.join(base_data_dir, category)
            new_jobs = check_for_new_jobs(category_data_dir, category_jobs)
            
            if new_jobs:
                print(f"🚨 {len(new_jobs)} vagas novas em {category}!")
                for job in new_jobs:
                    if producer:
                        send_new_job_alert(producer, job, category)
                    print(f"  🆕 {job['title']} - {job['company']}")
                total_new += len(new_jobs)
            else:
                print(f"✅ Nenhuma vaga nova em {category}")
    
    if producer:
        producer.close()
    
    print(f"\n📊 Total: {total_new} vagas novas detectadas")
    return total_new

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Sistema de alertas Kafka para vagas LinkedIn')
    parser.add_argument('--mode', choices=['monitor', 'single'], default='single',
                      help='Modo: monitor (contínuo) ou single (única verificação)')
    parser.add_argument('--interval', type=int, default=15,
                      help='Intervalo de verificação em minutos (para modo monitor)')
    
    args = parser.parse_args()
    
    if args.mode == 'monitor':
        run_real_time_monitoring(args.interval)
    else:
        run_single_check()
