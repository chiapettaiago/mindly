#!/usr/bin/env python3
"""
Teste simples para verificar se o erro de serialização foi resolvido
"""

import os
import sys
from dotenv import load_dotenv

# Adicionar o diretório atual ao path para importar o app
sys.path.insert(0, '/home/iago/Documentos/mindly')

def test_cache_serialization():
    """Testa se o cache está funcionando sem erros de serialização"""
    try:
        # Configurar ambiente
        load_dotenv()
        
        # Importar e configurar o app
        from app import app, db, cache
        
        with app.app_context():
            print("🧪 Testando serialização do cache...")
            
            # Testar cache de uma string simples
            test_key = 'test_cache_key'
            test_data = {'message': 'Hello, cache!', 'number': 42}
            
            print("1. Testando operação SET...")
            cache.set(test_key, test_data, timeout=60)
            
            print("2. Testando operação GET...")
            result = cache.get(test_key)
            
            if result == test_data:
                print("✅ Cache funcionando corretamente!")
                print(f"   Dados recuperados: {result}")
            else:
                print("❌ Problema no cache")
                print(f"   Esperado: {test_data}")
                print(f"   Recebido: {result}")
                return False
            
            # Limpeza
            cache.delete(test_key)
            
            return True
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def main():
    print("🧠 Mindly - Teste de Serialização do Cache")
    print("="*50)
    
    if test_cache_serialization():
        print("\n🎉 Cache funcionando sem problemas de serialização!")
    else:
        print("\n❌ Problemas detectados no cache")

if __name__ == '__main__':
    main()
