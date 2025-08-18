#!/usr/bin/env python3
"""
Script de monitoramento do cache Memcached para o Mindly
Monitora performance e estatísticas em tempo real
"""

import os
import time
import sys
from dotenv import load_dotenv

def monitor_cache_performance():
    """Monitora performance do cache em tempo real"""
    try:
        import memcache
        
        load_dotenv()
        servers = os.environ.get('MEMCACHED_SERVERS', 'localhost:11211')
        
        mc = memcache.Client([servers])
        
        print(f"🔍 Monitorando Memcached: {servers}")
        print("Pressione Ctrl+C para parar\n")
        
        last_stats = None
        
        while True:
            try:
                stats = mc.get_stats()
                
                if not stats:
                    print("❌ Não foi possível obter estatísticas")
                    time.sleep(5)
                    continue
                
                current_time = time.strftime("%H:%M:%S")
                
                for server, stat_dict in stats:
                    hits = int(stat_dict.get('get_hits', 0))
                    misses = int(stat_dict.get('get_misses', 0))
                    total_gets = hits + misses
                    
                    items = int(stat_dict.get('curr_items', 0))
                    connections = int(stat_dict.get('curr_connections', 0))
                    
                    bytes_used = int(stat_dict.get('bytes', 0))
                    limit_maxbytes = int(stat_dict.get('limit_maxbytes', 0))
                    
                    # Calcular taxa de hit
                    hit_rate = (hits / total_gets * 100) if total_gets > 0 else 0
                    
                    # Calcular uso de memória
                    memory_usage = (bytes_used / limit_maxbytes * 100) if limit_maxbytes > 0 else 0
                    
                    # Calcular diferenças desde a última medição
                    if last_stats:
                        last_hits = int(last_stats.get('get_hits', 0))
                        last_misses = int(last_stats.get('get_misses', 0))
                        
                        new_hits = hits - last_hits
                        new_misses = misses - last_misses
                        new_total = new_hits + new_misses
                        
                        new_hit_rate = (new_hits / new_total * 100) if new_total > 0 else 0
                        
                        print(f"\r{current_time} | Items: {items:4d} | Conexões: {connections:2d} | "
                              f"Hit Rate: {hit_rate:5.1f}% | Novo Hit Rate: {new_hit_rate:5.1f}% | "
                              f"Memória: {memory_usage:4.1f}% | Novos Gets: {new_total:3d}", end="")
                    else:
                        print(f"\r{current_time} | Items: {items:4d} | Conexões: {connections:2d} | "
                              f"Hit Rate: {hit_rate:5.1f}% | Memória: {memory_usage:4.1f}%", end="")
                    
                    last_stats = stat_dict
                
                time.sleep(2)  # Atualizar a cada 2 segundos
                
            except KeyboardInterrupt:
                print("\n\n👋 Monitoramento interrompido pelo usuário")
                break
            except Exception as e:
                print(f"\n❌ Erro no monitoramento: {e}")
                time.sleep(5)
                
    except ImportError:
        print("❌ python-memcached não instalado")
    except Exception as e:
        print(f"❌ Erro: {e}")

def cache_analysis():
    """Análise detalhada do cache"""
    try:
        import memcache
        
        load_dotenv()
        servers = os.environ.get('MEMCACHED_SERVERS', 'localhost:11211')
        
        mc = memcache.Client([servers])
        stats = mc.get_stats()
        
        if not stats:
            print("❌ Não foi possível obter estatísticas")
            return
        
        print("📊 Análise Detalhada do Cache Memcached")
        print("="*60)
        
        for server, stat_dict in stats:
            print(f"\n🖥️ Servidor: {server}")
            print("-" * 40)
            
            # Informações básicas
            version = stat_dict.get('version', 'N/A')
            uptime = int(stat_dict.get('uptime', 0))
            print(f"Versão: {version}")
            print(f"Uptime: {uptime//3600}h {(uptime%3600)//60}m")
            
            # Estatísticas de conexão
            curr_connections = int(stat_dict.get('curr_connections', 0))
            total_connections = int(stat_dict.get('total_connections', 0))
            print(f"Conexões atuais: {curr_connections}")
            print(f"Total de conexões: {total_connections:,}")
            
            # Estatísticas de itens
            curr_items = int(stat_dict.get('curr_items', 0))
            total_items = int(stat_dict.get('total_items', 0))
            print(f"Itens no cache: {curr_items:,}")
            print(f"Total de itens processados: {total_items:,}")
            
            # Estatísticas de performance
            get_hits = int(stat_dict.get('get_hits', 0))
            get_misses = int(stat_dict.get('get_misses', 0))
            total_gets = get_hits + get_misses
            
            print(f"\nPerformance:")
            print(f"  Hits: {get_hits:,}")
            print(f"  Misses: {get_misses:,}")
            print(f"  Total Gets: {total_gets:,}")
            
            if total_gets > 0:
                hit_rate = (get_hits / total_gets) * 100
                print(f"  Taxa de acerto: {hit_rate:.2f}%")
                
                if hit_rate >= 90:
                    print("  ✅ Excelente taxa de acerto!")
                elif hit_rate >= 75:
                    print("  ✅ Boa taxa de acerto")
                elif hit_rate >= 50:
                    print("  ⚠️ Taxa de acerto moderada")
                else:
                    print("  ❌ Taxa de acerto baixa")
            
            # Comandos executados
            cmd_get = int(stat_dict.get('cmd_get', 0))
            cmd_set = int(stat_dict.get('cmd_set', 0))
            print(f"  Comandos GET: {cmd_get:,}")
            print(f"  Comandos SET: {cmd_set:,}")
            
            # Uso de memória
            bytes_used = int(stat_dict.get('bytes', 0))
            limit_maxbytes = int(stat_dict.get('limit_maxbytes', 0))
            
            print(f"\nUso de Memória:")
            print(f"  Bytes utilizados: {bytes_used:,}")
            print(f"  Limite máximo: {limit_maxbytes:,}")
            
            if limit_maxbytes > 0:
                memory_usage = (bytes_used / limit_maxbytes) * 100
                print(f"  Uso percentual: {memory_usage:.2f}%")
                
                if memory_usage >= 90:
                    print("  ⚠️ Uso de memória alto!")
                elif memory_usage >= 75:
                    print("  ⚠️ Uso de memória moderado")
                else:
                    print("  ✅ Uso de memória OK")
            
            # Estatísticas de rede
            bytes_read = int(stat_dict.get('bytes_read', 0))
            bytes_written = int(stat_dict.get('bytes_written', 0))
            
            print(f"\nTráfego de Rede:")
            print(f"  Bytes lidos: {bytes_read:,}")
            print(f"  Bytes escritos: {bytes_written:,}")
            print(f"  Total transferido: {(bytes_read + bytes_written):,}")
            
            # Recomendações
            print(f"\n💡 Recomendações:")
            
            if total_gets > 0:
                if hit_rate < 75:
                    print("  - Considere aumentar o timeout do cache")
                    print("  - Verifique se as chaves estão sendo bem utilizadas")
                
                if memory_usage > 80:
                    print("  - Considere aumentar a memória disponível")
                    print("  - Revise o timeout dos itens no cache")
                
                if curr_connections > 50:
                    print("  - Monitore o número de conexões")
                    print("  - Considere connection pooling")
            
            print("  - Use prefixos nas chaves para organização")
            print("  - Monitore regularmente as estatísticas")
            print("  - Configure alertas para uso de memória > 85%")
            
    except ImportError:
        print("❌ python-memcached não instalado")
    except Exception as e:
        print(f"❌ Erro na análise: {e}")

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == 'monitor':
            monitor_cache_performance()
        elif sys.argv[1] == 'analysis':
            cache_analysis()
        else:
            print("Uso: python monitor_cache.py [monitor|analysis]")
    else:
        print("🧠 Mindly - Monitor de Cache")
        print("="*40)
        print("1. monitor  - Monitoramento em tempo real")
        print("2. analysis - Análise detalhada")
        print("\nEscolha uma opção ou execute:")
        print("python monitor_cache.py monitor")
        print("python monitor_cache.py analysis")

if __name__ == '__main__':
    main()
