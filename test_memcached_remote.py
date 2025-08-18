#!/usr/bin/env python3
"""
Script de teste e configuração do Memcached remoto para o Mindly
Testa conectividade e performance do cache remoto
"""

import os
import time
import sys
from dotenv import load_dotenv

def test_remote_memcached():
    """Testa conexão com Memcached remoto"""
    try:
        import memcache
        import socket
        
        load_dotenv()
        servers = os.environ.get('MEMCACHED_SERVERS', 'localhost:11211')
        
        print(f"🔍 Testando conexão com Memcached remoto: {servers}")
        
        # Teste de conectividade de rede primeiro
        server_parts = servers.split(':')
        host = server_parts[0]
        port = int(server_parts[1]) if len(server_parts) > 1 else 11211
        
        print(f"🌐 Testando conectividade de rede para {host}:{port}...")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5 segundos de timeout
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result != 0:
                print(f"❌ Não é possível conectar via TCP para {host}:{port}")
                print(f"   Código de erro: {result}")
                print("   Verificações necessárias:")
                print("   - O servidor Memcached está rodando?")
                print("   - A porta 11211 está aberta no firewall?")
                print("   - Há conectividade de rede?")
                return False
            else:
                print(f"✅ TCP conectividade OK para {host}:{port}")
        except Exception as e:
            print(f"❌ Erro de conectividade de rede: {e}")
            return False
        
        # Agora testa o Memcached
        mc = memcache.Client([servers], debug=1)  # Debug ativado
        
        # Teste básico de conectividade
        test_key = 'mindly_connection_test'
        test_value = f'test_{int(time.time())}'
        
        print("📝 Testando operação SET...")
        start_time = time.time()
        result_set = mc.set(test_key, test_value, time=60)
        set_time = (time.time() - start_time) * 1000
        
        if not result_set:
            print("❌ Falha na operação SET")
            print("   Possíveis causas:")
            print("   - Memcached não está aceitando conexões")
            print("   - Limite de memória atingido")
            print("   - Problemas de autenticação/permissões")
            return False
        
        print(f"✅ SET executado em {set_time:.2f}ms")
        
        # Teste de leitura
        print("📖 Testando operação GET...")
        start_time = time.time()
        result_get = mc.get(test_key)
        get_time = (time.time() - start_time) * 1000
        
        if result_get != test_value:
            print(f"❌ Falha na operação GET. Esperado: {test_value}, Recebido: {result_get}")
            return False
        
        print(f"✅ GET executado em {get_time:.2f}ms")
        
        # Teste de performance com múltiplas operações
        print("⚡ Testando performance com 10 operações...")
        start_time = time.time()
        
        for i in range(10):
            key = f'mindly_perf_test_{i}'
            value = f'performance_test_value_{i}_{int(time.time())}'
            mc.set(key, value, time=30)
            retrieved = mc.get(key)
            if retrieved != value:
                print(f"❌ Falha no teste de performance na iteração {i}")
                return False
        
        total_time = (time.time() - start_time) * 1000
        avg_time = total_time / 20  # 10 sets + 10 gets
        
        print(f"✅ Performance: {avg_time:.2f}ms por operação")
        
        # Limpeza
        print("🧹 Limpando dados de teste...")
        mc.delete(test_key)
        for i in range(10):
            mc.delete(f'mindly_perf_test_{i}')
        
        print("🎉 Memcached remoto funcionando perfeitamente!")
        return True
        
    except ImportError:
        print("❌ python-memcached não instalado")
        print("Execute: pip install python-memcached")
        return False
    except Exception as e:
        print(f"❌ Erro ao conectar com Memcached remoto: {e}")
        return False

def get_memcached_stats():
    """Obtém estatísticas detalhadas do Memcached remoto"""
    try:
        import memcache
        
        load_dotenv()
        servers = os.environ.get('MEMCACHED_SERVERS', 'localhost:11211')
        
        mc = memcache.Client([servers])
        stats = mc.get_stats()
        
        if not stats:
            print("❌ Não foi possível obter estatísticas")
            return False
        
        print("\n📊 Estatísticas do Memcached Remoto:")
        print("="*50)
        
        for server, stat_dict in stats:
            print(f"\n🖥️ Servidor: {server}")
            print(f"   Versão: {stat_dict.get('version', 'N/A')}")
            
            uptime = int(stat_dict.get('uptime', 0))
            hours = uptime // 3600
            minutes = (uptime % 3600) // 60
            print(f"   Uptime: {hours}h {minutes}m")
            
            print(f"   Conexões atuais: {stat_dict.get('curr_connections', 'N/A')}")
            print(f"   Conexões totais: {stat_dict.get('total_connections', 'N/A')}")
            print(f"   Itens no cache: {stat_dict.get('curr_items', 'N/A')}")
            
            # Estatísticas de performance
            hits = int(stat_dict.get('get_hits', 0))
            misses = int(stat_dict.get('get_misses', 0))
            total_gets = hits + misses
            
            print(f"   Hits: {hits:,}")
            print(f"   Misses: {misses:,}")
            
            if total_gets > 0:
                hit_rate = (hits / total_gets) * 100
                print(f"   Taxa de acerto: {hit_rate:.1f}%")
            
            # Uso de memória
            bytes_used = int(stat_dict.get('bytes', 0))
            limit_maxbytes = int(stat_dict.get('limit_maxbytes', 0))
            
            if limit_maxbytes > 0:
                memory_usage = (bytes_used / limit_maxbytes) * 100
                print(f"   Uso de memória: {bytes_used:,} bytes ({memory_usage:.1f}%)")
                print(f"   Limite de memória: {limit_maxbytes:,} bytes")
            
            # Estatísticas de rede
            bytes_read = int(stat_dict.get('bytes_read', 0))
            bytes_written = int(stat_dict.get('bytes_written', 0))
            print(f"   Bytes lidos: {bytes_read:,}")
            print(f"   Bytes escritos: {bytes_written:,}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {e}")
        return False

def benchmark_memcached():
    """Executa benchmark detalhado do Memcached remoto"""
    try:
        import memcache
        
        load_dotenv()
        servers = os.environ.get('MEMCACHED_SERVERS', 'localhost:11211')
        
        print(f"\n🏃 Executando benchmark do Memcached: {servers}")
        print("="*60)
        
        mc = memcache.Client([servers])
        
        # Teste de latência com diferentes tamanhos de dados
        test_sizes = [100, 1000, 10000, 100000]  # bytes
        
        for size in test_sizes:
            print(f"\n📏 Testando com dados de {size} bytes...")
            
            # Gerar dados de teste
            test_data = 'x' * size
            key = f'benchmark_test_{size}'
            
            # Benchmark SET
            set_times = []
            for i in range(5):
                start = time.time()
                mc.set(f"{key}_{i}", test_data, time=60)
                set_times.append((time.time() - start) * 1000)
            
            avg_set = sum(set_times) / len(set_times)
            
            # Benchmark GET
            get_times = []
            for i in range(5):
                start = time.time()
                mc.get(f"{key}_{i}")
                get_times.append((time.time() - start) * 1000)
            
            avg_get = sum(get_times) / len(get_times)
            
            print(f"   SET médio: {avg_set:.2f}ms")
            print(f"   GET médio: {avg_get:.2f}ms")
            
            # Limpeza
            for i in range(5):
                mc.delete(f"{key}_{i}")
        
        # Teste de throughput
        print(f"\n🚀 Teste de throughput (100 operações simultâneas)...")
        start_time = time.time()
        
        # 50 SETs + 50 GETs
        test_data = "throughput_test_data_" * 10
        for i in range(50):
            mc.set(f"throughput_{i}", test_data, time=60)
        
        for i in range(50):
            mc.get(f"throughput_{i}")
        
        total_time = time.time() - start_time
        ops_per_second = 100 / total_time
        
        print(f"   Operações por segundo: {ops_per_second:.1f}")
        print(f"   Tempo total: {total_time:.2f}s")
        
        # Limpeza
        for i in range(50):
            mc.delete(f"throughput_{i}")
        
        print("\n✅ Benchmark concluído!")
        
    except Exception as e:
        print(f"❌ Erro no benchmark: {e}")

def show_remote_cache_config():
    """Mostra configuração atual do cache remoto"""
    load_dotenv()
    
    print("\n⚙️ Configuração atual do Cache:")
    print("="*40)
    
    servers = os.environ.get('MEMCACHED_SERVERS', 'localhost:11211')
    print(f"Servidores: {servers}")
    
    # Verificar se é realmente remoto
    if 'localhost' in servers or '127.0.0.1' in servers:
        print("⚠️ Configuração aponta para localhost")
    else:
        print("✅ Configuração para servidor remoto")
    
    print("\n💡 Para produção, considere:")
    print("- Multiple servers: server1:11211,server2:11211")
    print("- SSL/TLS para conexões seguras")
    print("- Monitoramento de performance")

def main():
    print("🧠 Mindly - Teste Memcached Remoto")
    print("="*50)
    
    # Verificar dependências
    try:
        import memcache
        print("✅ python-memcached disponível")
    except ImportError:
        print("❌ python-memcached não instalado")
        print("Execute: pip install python-memcached")
        return
    
    # Verificar configuração
    load_dotenv()
    if not os.environ.get('MEMCACHED_SERVERS'):
        print("❌ MEMCACHED_SERVERS não configurado no .env")
        return
    
    show_remote_cache_config()
    
    # Teste de conectividade
    if test_remote_memcached():
        # Estatísticas
        get_memcached_stats()
        
        # Perguntar se quer fazer benchmark
        response = input("\n🏃 Deseja executar benchmark de performance? (sim/não): ").lower().strip()
        if response in ['sim', 's', 'yes', 'y']:
            benchmark_memcached()
        
        print("\n🎉 Memcached remoto configurado e funcionando!")
        print("\n📋 O aplicativo agora usará cache remoto automaticamente")
        
    else:
        print("\n❌ Falha na configuração do Memcached remoto")
        print("Verifique:")
        print("- Conectividade de rede")
        print("- Firewall/portas abertas")
        print("- Configuração do servidor Memcached")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'stats':
            get_memcached_stats()
        elif sys.argv[1] == 'benchmark':
            benchmark_memcached()
        elif sys.argv[1] == 'test':
            test_remote_memcached()
    else:
        main()
