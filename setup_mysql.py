#!/usr/bin/env python3
"""
Script de configuração do MySQL para o Mindly
Auxilia na configuração inicial do banco de dados MySQL
"""

import os
import sys
from dotenv import load_dotenv

def create_mysql_database():
    """Cria o banco de dados MySQL se não existir"""
    try:
        import pymysql
        
        # Carregar configurações
        load_dotenv()
        
        host = os.environ.get('MYSQL_HOST', 'localhost')
        port = int(os.environ.get('MYSQL_PORT', '3306'))
        user = os.environ.get('MYSQL_USER', 'root')
        password = os.environ.get('MYSQL_PASSWORD', '')
        database = os.environ.get('MYSQL_DATABASE', 'mindly')
        
        print(f"🔍 Conectando ao MySQL em {host}:{port}...")
        
        # Conectar sem especificar database
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Verificar se database existe
            cursor.execute("SHOW DATABASES LIKE %s", (database,))
            result = cursor.fetchone()
            
            if result:
                print(f"✅ Database '{database}' já existe!")
            else:
                # Criar database
                cursor.execute(f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                print(f"✅ Database '{database}' criado com sucesso!")
        
        connection.commit()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao configurar MySQL: {e}")
        return False

def check_mysql_requirements():
    """Verifica se todas as dependências estão instaladas"""
    print("📋 Verificando dependências...")
    
    try:
        import pymysql
        print("✅ PyMySQL instalado")
    except ImportError:
        print("❌ PyMySQL não instalado. Execute: pip install PyMySQL")
        return False
    
    try:
        import cryptography
        print("✅ Cryptography instalado")
    except ImportError:
        print("❌ Cryptography não instalado. Execute: pip install cryptography")
        return False
    
    return True

def validate_env_config():
    """Valida configurações do arquivo .env"""
    print("🔧 Validando configurações...")
    
    load_dotenv()
    
    required_vars = ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
        else:
            # Mascarar senha na saída
            display_value = value if var != 'MYSQL_PASSWORD' else '*' * len(value)
            print(f"  ✅ {var}: {display_value}")
    
    if missing_vars:
        print(f"❌ Variáveis faltando: {', '.join(missing_vars)}")
        print("\nConfigure essas variáveis no arquivo .env:")
        for var in missing_vars:
            print(f"  {var}=seu_valor_aqui")
        return False
    
    return True

def show_mysql_setup_guide():
    """Mostra guia de configuração para diferentes provedores MySQL"""
    print("\n" + "="*60)
    print("📖 GUIA DE CONFIGURAÇÃO MYSQL")
    print("="*60)
    
    print("\n🏠 MySQL Local (XAMPP/WAMP/MAMP):")
    print("""
    MYSQL_HOST=localhost
    MYSQL_PORT=3306
    MYSQL_USER=root
    MYSQL_PASSWORD=sua_senha_local
    MYSQL_DATABASE=mindly
    """)
    
    print("\n☁️ PlanetScale (Recomendado para produção):")
    print("""
    1. Acesse https://planetscale.com/
    2. Crie uma conta gratuita
    3. Crie um novo database
    4. Obtenha as credenciais de conexão
    
    MYSQL_HOST=your-db.psdb.cloud
    MYSQL_PORT=3306
    MYSQL_USER=your-username
    MYSQL_PASSWORD=your-password
    MYSQL_DATABASE=your-database-name
    """)
    
    print("\n🚂 Railway MySQL:")
    print("""
    1. Acesse https://railway.app/
    2. Crie um projeto
    3. Adicione MySQL service
    4. Copie as credenciais
    
    MYSQL_HOST=containers-us-west-xxx.railway.app
    MYSQL_PORT=xxxx
    MYSQL_USER=root
    MYSQL_PASSWORD=xxxxxxxxxx
    MYSQL_DATABASE=railway
    """)
    
    print("\n☁️ AWS RDS:")
    print("""
    1. Acesse AWS RDS Console
    2. Crie uma instância MySQL
    3. Configure security groups
    4. Obtenha endpoint e credenciais
    
    MYSQL_HOST=your-instance.xxxxx.us-east-1.rds.amazonaws.com
    MYSQL_PORT=3306
    MYSQL_USER=admin
    MYSQL_PASSWORD=your-password
    MYSQL_DATABASE=mindly
    """)

def main():
    print("🧠 Mindly - Configuração MySQL")
    print("="*50)
    
    # Verificar dependências
    if not check_mysql_requirements():
        print("\n💡 Para instalar as dependências:")
        print("pip install PyMySQL cryptography")
        return
    
    # Verificar arquivo .env
    if not os.path.exists('.env'):
        print("\n📁 Arquivo .env não encontrado!")
        print("1. Copie .env.example para .env:")
        print("   cp .env.example .env")
        print("2. Edite o arquivo .env com suas configurações MySQL")
        show_mysql_setup_guide()
        return
    
    # Validar configurações
    if not validate_env_config():
        print("\n💡 Configure as variáveis faltando no arquivo .env")
        show_mysql_setup_guide()
        return
    
    # Tentar criar database
    print("\n🏗️ Configurando banco de dados...")
    if create_mysql_database():
        print("\n🎉 Configuração MySQL concluída!")
        print("\n📋 Próximos passos:")
        print("1. Execute o script de migração se tiver dados SQLite:")
        print("   python migrate_to_mysql.py")
        print("2. Ou inicie o aplicativo normalmente:")
        print("   python app.py")
    else:
        print("\n❌ Falha na configuração. Verifique suas credenciais.")
        show_mysql_setup_guide()

if __name__ == '__main__':
    main()
