#!/usr/bin/env python3
"""
Script de migração do SQLite para MySQL
Executa a migração dos dados existentes do SQLite para o novo banco MySQL
"""

import os
import sys
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Importar após carregar .env para garantir configuração correta
import pymysql
pymysql.install_as_MySQLdb()

from app import app, db
from models import User, Reminder, Device, Note

def migrate_sqlite_to_mysql():
    """Migra dados do SQLite para MySQL"""
    
    print("🔄 Iniciando migração do SQLite para MySQL...")
    
    # Verificar se o arquivo SQLite existe
    sqlite_path = '/instance/lembretes.db'
    if not os.path.exists(sqlite_path):
        print("❌ Arquivo SQLite não encontrado. Nada para migrar.")
        return
    
    # Conectar ao SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    cursor = sqlite_conn.cursor()
    
    try:
        with app.app_context():
            # Criar tabelas no MySQL
            print("📋 Criando tabelas no MySQL...")
            db.create_all()
            
            # Migrar usuários
            print("👥 Migrando usuários...")
            cursor.execute("SELECT * FROM user")
            users = cursor.fetchall()
            
            user_mapping = {}  # Para mapear IDs antigos para novos
            
            for user_row in users:
                # Verificar se usuário já existe
                existing_user = User.query.filter_by(email=user_row['email']).first()
                if existing_user:
                    user_mapping[user_row['id']] = existing_user.id
                    print(f"  ↪️ Usuário {user_row['email']} já existe, usando ID {existing_user.id}")
                    continue
                
                user = User(
                    name=user_row['name'],
                    email=user_row['email'],
                    password=user_row['password']
                )
                db.session.add(user)
                db.session.flush()  # Para obter o ID
                user_mapping[user_row['id']] = user.id
                print(f"  ✅ Usuário {user_row['email']} migrado (ID: {user_row['id']} → {user.id})")
            
            # Migrar lembretes
            print("📝 Migrando lembretes...")
            cursor.execute("SELECT * FROM reminder")
            reminders = cursor.fetchall()
            
            for reminder_row in reminders:
                if reminder_row['user_id'] not in user_mapping:
                    print(f"  ⚠️ Lembrete ignorado: usuário {reminder_row['user_id']} não encontrado")
                    continue
                
                # Converter data se necessário
                due_date = None
                if reminder_row['due']:
                    try:
                        due_date = datetime.fromisoformat(reminder_row['due'].replace('Z', '+00:00'))
                    except:
                        due_date = None
                
                reminder = Reminder(
                    title=reminder_row['title'],
                    note=reminder_row['note'] or '',
                    due=due_date,
                    done=bool(reminder_row['done']),
                    user_id=user_mapping[reminder_row['user_id']]
                )
                db.session.add(reminder)
                print(f"  ✅ Lembrete '{reminder_row['title']}' migrado")
            
            # Migrar dispositivos
            print("📱 Migrando dispositivos...")
            try:
                cursor.execute("SELECT * FROM device")
                devices = cursor.fetchall()
                
                for device_row in devices:
                    if device_row['user_id'] not in user_mapping:
                        continue
                    
                    device = Device(
                        user_id=user_mapping[device_row['user_id']],
                        token=device_row['token'],
                        user_agent=device_row['user_agent'] or '',
                        created_at=datetime.fromisoformat(device_row['created_at']) if device_row.get('created_at') else datetime.now()
                    )
                    db.session.add(device)
                    print(f"  ✅ Dispositivo migrado para usuário {device_row['user_id']}")
            except sqlite3.OperationalError:
                print("  ℹ️ Tabela 'device' não existe no SQLite, pulando...")
            
            # Migrar notas
            print("📄 Migrando notas...")
            try:
                cursor.execute("SELECT * FROM note")
                notes = cursor.fetchall()
                
                for note_row in notes:
                    if note_row['user_id'] not in user_mapping:
                        continue
                    
                    note = Note(
                        user_id=user_mapping[note_row['user_id']],
                        content=note_row['content'],
                        created_at=datetime.fromisoformat(note_row['created_at']) if note_row.get('created_at') else datetime.now(),
                        updated_at=datetime.fromisoformat(note_row['updated_at']) if note_row.get('updated_at') else datetime.now()
                    )
                    db.session.add(note)
                    print(f"  ✅ Nota migrada para usuário {note_row['user_id']}")
            except sqlite3.OperationalError:
                print("  ℹ️ Tabela 'note' não existe no SQLite, pulando...")
            
            # Salvar todas as mudanças
            db.session.commit()
            print("💾 Todas as mudanças foram salvas!")
            
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro durante a migração: {e}")
        raise
    finally:
        sqlite_conn.close()
    
    print("🎉 Migração concluída com sucesso!")
    print("\n📋 Próximos passos:")
    print("1. Verifique se todos os dados foram migrados corretamente")
    print("2. Teste o aplicativo com o novo banco MySQL")
    print("3. Faça backup do arquivo SQLite antes de removê-lo")
    print("4. Considere renomear 'lembretes.db' para 'lembretes.db.backup'")

def test_mysql_connection():
    """Testa a conexão com MySQL"""
    print("🔍 Testando conexão com MySQL...")
    
    try:
        with app.app_context():
            # Tentar executar uma query simples
            result = db.session.execute(db.text("SELECT 1 as test"))
            test_value = result.scalar()
            if test_value == 1:
                print("✅ Conexão com MySQL funcionando!")
                return True
            else:
                print("❌ Conexão com MySQL com problemas")
                return False
    except Exception as e:
        print(f"❌ Erro ao conectar com MySQL: {e}")
        return False

if __name__ == '__main__':
    print("🧠 Mindly - Migração SQLite → MySQL")
    print("=" * 50)
    
    # Verificar se as variáveis MySQL estão configuradas
    required_vars = ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        print("Configure essas variáveis no arquivo .env antes de executar a migração.")
        sys.exit(1)
    
    # Testar conexão MySQL
    if not test_mysql_connection():
        sys.exit(1)
    
    # Confirmar migração
    print("\n⚠️ ATENÇÃO: Esta operação irá migrar dados do SQLite para MySQL.")
    print("Certifique-se de ter feito backup dos seus dados antes de continuar.")
    
    response = input("\nDeseja continuar? (sim/não): ").lower().strip()
    if response not in ['sim', 's', 'yes', 'y']:
        print("Migração cancelada.")
        sys.exit(0)
    
    # Executar migração
    migrate_sqlite_to_mysql()
