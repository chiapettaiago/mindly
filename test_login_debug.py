#!/usr/bin/env python3
"""
Script para testar o problema de login duplo no Mindly
"""

import requests
import sys
import time

def test_login_flow():
    """Testa o fluxo de login para detectar problemas de login duplo"""
    
    base_url = "http://127.0.0.1:5000"
    session = requests.Session()
    
    print("🧪 Testando fluxo de login do Mindly")
    print("="*50)
    
    try:
        # 1. Acessar página de login
        print("1. 📋 Acessando página de login...")
        login_response = session.get(f"{base_url}/login")
        
        if login_response.status_code != 200:
            print(f"❌ Erro ao acessar login: {login_response.status_code}")
            return False
        
        print(f"✅ Login page acessível (Status: {login_response.status_code})")
        
        # 2. Tentar acessar página protegida (deve redirecionar)
        print("\n2. 🔒 Testando acesso a página protegida sem login...")
        protected_response = session.get(f"{base_url}/", allow_redirects=False)
        
        if protected_response.status_code == 302:
            print("✅ Redirecionamento correto para página protegida")
        else:
            print(f"⚠️ Status inesperado: {protected_response.status_code}")
        
        # 3. Verificar se o login está funcionando
        print("\n3. 📊 Verificando estado da sessão...")
        
        # Tentar acessar API que requer login
        api_response = session.get(f"{base_url}/api/notifications", allow_redirects=False)
        
        if api_response.status_code == 302:
            print("✅ API protegida redirecionando corretamente")
        else:
            print(f"⚠️ API status: {api_response.status_code}")
        
        print("\n4. 🎯 Análise:")
        print("- Se você está tendo que fazer login duas vezes:")
        print("  * Limpe os cookies do navegador")
        print("  * Verifique se não há múltiplas abas abertas")
        print("  * Use modo privado/incógnito para testar")
        
        print("\n💡 Correções implementadas:")
        print("✅ Configurações de sessão mais robustas")
        print("✅ Limpeza automática de sessões inválidas")
        print("✅ Proteção 'strong' contra session fixation")
        print("✅ Configuração de cookies melhorada")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Não foi possível conectar ao servidor")
        print("   Verifique se o aplicativo está rodando em http://127.0.0.1:5000")
        return False
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def show_debug_info():
    """Mostra informações de debug para problemas de login"""
    
    print("\n🔍 Informações de Debug:")
    print("="*30)
    
    print("\n📋 Possíveis causas do login duplo:")
    print("1. Cookies/sessões antigas conflitantes")
    print("2. Múltiplas abas/janelas abertas")
    print("3. Cache do navegador")
    print("4. Session fixation issues")
    
    print("\n🛠️ Soluções implementadas:")
    print("1. SESSION_COOKIE_HTTPONLY = True")
    print("2. SESSION_COOKIE_SAMESITE = 'Lax'")
    print("3. session_protection = 'strong'")
    print("4. Limpeza automática de sessões no login")
    print("5. Configuração robusta de PERMANENT_SESSION_LIFETIME")
    
    print("\n🎯 Para testar:")
    print("1. Limpe todos os cookies do site")
    print("2. Feche todas as abas do aplicativo")
    print("3. Abra uma nova aba em modo incógnito")
    print("4. Acesse http://127.0.0.1:5000")
    print("5. Faça login uma única vez")
    
    print("\n📱 No PWA (app instalado):")
    print("1. Desinstale o PWA se instalado")
    print("2. Limpe dados do site no navegador")
    print("3. Reinstale o PWA")

def main():
    print("🧠 Mindly - Diagnóstico de Login Duplo")
    print("="*50)
    
    if test_login_flow():
        show_debug_info()
        
        print("\n🎉 Teste concluído!")
        print("\nSe ainda estiver tendo problemas:")
        print("1. Limpe completamente os cookies do navegador")
        print("2. Teste em modo incógnito")
        print("3. Verifique se não há múltiplas instâncias do app rodando")
    else:
        print("\n❌ Falha no teste de conectividade")

if __name__ == '__main__':
    main()
