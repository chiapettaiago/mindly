#!/usr/bin/env python3
"""
Script de configuração do Memcached para o Mindly
Auxilia na instalação e configuração do cache
"""

import os
import subprocess
import sys
from dotenv import load_dotenv

def check_memcached_installed():
    """Verifica se o Memcached está instalado"""
    try:
        result = subprocess.run(['memcached', '-h'], capture_output=True, text=True)
        return True
    except FileNotFoundError:
        return False

def install_memcached_ubuntu():
    """Instala Memcached no Ubuntu/Debian"""
    try:
        print("📦 Instalando Memcached...")
        subprocess.run(['sudo', 'apt', 'update'], check=True)
        subprocess.run(['sudo', 'apt', 'install', '-y', 'memcached'], check=True)
        print("✅ Memcached instalado com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar Memcached: {e}")
        return False

def start_memcached():
    """Inicia o serviço Memcached"""
    try:
        # Verificar se já está rodando
        result = subprocess.run(['pgrep', 'memcached'], capture_output=True)
        if result.returncode == 0:
            print("✅ Memcached já está rodando")
            return True
        
        # Tentar iniciar
        subprocess.run(['sudo', 'systemctl', 'start', 'memcached'], check=True)
        subprocess.run(['sudo', 'systemctl', 'enable', 'memcached'], check=True)
        print("✅ Memcached iniciado e habilitado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao iniciar Memcached: {e}")
        return False

def test_memcached_connection():
    """Testa conexão com Memcached"""
    try:
        import memcache
        
        load_dotenv()
        servers = os.environ.get('MEMCACHED_SERVERS', 'localhost:11211')
        
        mc = memcache.Client([servers])
        test_key = 'mindly_test'
        test_value = 'connection_test'
        
        # Testar set/get
        mc.set(test_key, test_value, time=10)
        result = mc.get(test_key)
        
        if result == test_value:
            print(f"✅ Conexão Memcached funcionando em: {servers}")
            mc.delete(test_key)
            return True
        else:
            print("❌ Falha no teste de conexão Memcached")
            return False
            
    except ImportError:
        print("❌ python-memcached não instalado")
        return False
    except Exception as e:
        print(f"❌ Erro ao testar Memcached: {e}")
        return False

def show_memcached_status():
    """Mostra status e estatísticas do Memcached"""
    try:
        import memcache
        
        load_dotenv()
        servers = os.environ.get('MEMCACHED_SERVERS', 'localhost:11211')
        
        mc = memcache.Client([servers])
        stats = mc.get_stats()
        
        if stats:
            print("\n📊 Estatísticas do Memcached:")
            for server, stat_dict in stats:
                print(f"\n🖥️ Servidor: {server}")
                print(f"  Versão: {stat_dict.get('version', 'N/A')}")
                print(f"  Uptime: {int(stat_dict.get('uptime', 0)) // 3600}h {(int(stat_dict.get('uptime', 0)) % 3600) // 60}m")
                print(f"  Conexões atuais: {stat_dict.get('curr_connections', 'N/A')}")
                print(f"  Itens no cache: {stat_dict.get('curr_items', 'N/A')}")
                print(f"  Hits: {stat_dict.get('get_hits', 'N/A')}")
                print(f"  Misses: {stat_dict.get('get_misses', 'N/A')}")
                
                hits = int(stat_dict.get('get_hits', 0))
                misses = int(stat_dict.get('get_misses', 0))
                total = hits + misses
                if total > 0:
                    hit_rate = (hits / total) * 100
                    print(f"  Taxa de acerto: {hit_rate:.1f}%")
        else:
            print("❌ Não foi possível obter estatísticas")
            
    except Exception as e:
        print(f"❌ Erro ao obter status: {e}")

def show_installation_guide():
    """Mostra guia de instalação para diferentes sistemas"""
    print("\n" + "="*60)
    print("📖 GUIA DE INSTALAÇÃO MEMCACHED")
    print("="*60)
    
    print("\n🐧 Ubuntu/Debian:")
    print("sudo apt update")
    print("sudo apt install memcached")
    print("sudo systemctl start memcached")
    print("sudo systemctl enable memcached")
    
    print("\n🎩 CentOS/RHEL/Fedora:")
    print("sudo yum install memcached  # ou dnf install memcached")
    print("sudo systemctl start memcached")
    print("sudo systemctl enable memcached")
    
    print("\n🍎 macOS (Homebrew):")
    print("brew install memcached")
    print("brew services start memcached")
    
    print("\n🐳 Docker:")
    print("docker run -d -p 11211:11211 --name memcached memcached:latest")
    
    print("\n☁️ Produção (Railway/Heroku):")
    print("- Railway: Adicione Memcached service no dashboard")
    print("- Heroku: heroku addons:create memcachier:dev")
    print("- Configure MEMCACHED_SERVERS com o endpoint fornecido")

def main():
    print("🧠 Mindly - Configuração Memcached")
    print("="*50)
    
    # Verificar dependências Python
    try:
        import memcache
        print("✅ python-memcached instalado")
    except ImportError:
        print("❌ python-memcached não instalado")
        print("Execute: pip install python-memcached")
        return
    
    # Verificar se Memcached está instalado
    if not check_memcached_installed():
        print("❌ Memcached não encontrado no sistema")
        
        # Detectar sistema operacional
        if sys.platform.startswith('linux'):
            response = input("\nDeseja instalar Memcached automaticamente? (sim/não): ").lower().strip()
            if response in ['sim', 's', 'yes', 'y']:
                if install_memcached_ubuntu():
                    start_memcached()
                else:
                    show_installation_guide()
                    return
            else:
                show_installation_guide()
                return
        else:
            show_installation_guide()
            return
    
    # Verificar se está rodando
    if not start_memcached():
        print("⚠️ Memcached pode não estar rodando corretamente")
    
    # Testar conexão
    print("\n🔍 Testando conexão...")
    if test_memcached_connection():
        print("\n🎉 Memcached configurado com sucesso!")
        
        # Mostrar status
        show_memcached_status()
        
        print("\n📋 Próximos passos:")
        print("1. O aplicativo automaticamente usará Memcached")
        print("2. Monitor performance com 'python setup_memcached.py status'")
        print("3. Para produção, configure MEMCACHED_SERVERS no .env")
        
    else:
        print("\n❌ Falha na configuração do Memcached")
        print("Verifique os logs do sistema: sudo journalctl -u memcached")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        show_memcached_status()
    else:
        main()
