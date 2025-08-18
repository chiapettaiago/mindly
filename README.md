# 🧠 Mindly

App de lembretes simples, rápido e offline‑friendly, feito com Flask + MySQL e UI moderna.

<p align="left">
  <img src="static/icons/icon-192.svg" alt="Mindly" width="48" height="48" />
</p>

<p>
  <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white"></a>
  <a href="https://flask.palletsprojects.com/"><img alt="Flask" src="https://img.shields.io/badge/Flask-2.x-000000?logo=flask&logoColor=white"></a>
  <a href="https://www.mysql.com/"><img alt="MySQL" src="https://img.shields.io/badge/MySQL-8.x-4479A1?logo=mysql&logoColor=white"></a>
  <a href="#pwa"><img alt="PWA" src="https://img.shields.io/badge/PWA-enabled-5A0FC8?logo=pwa&logoColor=white"></a>
</p>

---

## ✨ Recursos

- Lembretes com título, observações e prazo
- Notas rápidas com busca e paginação
- Login com “lembrar de mim” e gerenciamento de dispositivos
- Notificações em tempo real (polling) e badge de alertas
- Texto‑para‑fala (TTS) em pt‑BR com voz mais natural
- PWA: atalho na tela inicial, funciona bem em mobile
- Cache com Memcached (opcional) e fallback em memória

## 🧱 Stack

- Backend: Flask, Flask‑Login, Flask‑WTF, SQLAlchemy
- Banco de dados: MySQL (PyMySQL)
- Cache: Memcached (python‑memcached) ou SimpleCache
- UI: HTML + CSS puro + JS leve (sem build)

## 📁 Estrutura do projeto

- `app.py` — aplicação Flask e rotas
- `models.py` — modelos SQLAlchemy (User, Reminder, Note, Device)
- `forms.py` — formulários WTForms
- `templates/` — páginas Jinja2
- `static/` — CSS, JS, ícones e Service Worker (PWA)
- `setup_mysql.py`, `migrate_to_mysql.py` — utilitários de banco de dados

## ✅ Pré‑requisitos

- Python 3.10+
- MySQL 5.7+/8.x acessível (local ou remoto)
- Opcional: Memcached (para cache compartilhado)

## 🚀 Começando (Windows / PowerShell)

1) Crie o ambiente e instale dependências:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Configure o `.env` (exemplo mínimo):

```env
SECRET_KEY=sua_chave_secreta
APP_VERSION=1.0.0
APP_MANUFACTURER=Mindly

MYSQL_HOST=seu_host
MYSQL_PORT=3306
MYSQL_USER=seu_usuario
MYSQL_PASSWORD=sua_senha
MYSQL_DATABASE=mindly

# opcional
MEMCACHED_SERVERS=host:11211
```

3) Inicie o app em modo desenvolvimento:

```powershell
$env:FLASK_ENV = "development"
python app.py
# ou
# $env:FLASK_APP = "app.py"; flask run
```

O app ficará disponível em http://127.0.0.1:5000

## 🗄️ Banco de dados

- As tabelas são criadas automaticamente na primeira execução.
- Para preparar/migrar um banco MySQL remoto, veja:
  - `setup_mysql.py` — valida e ajuda a criar o banco
  - `migrate_to_mysql.py` — migração a partir de SQLite (quando aplicável)

## ⚡ Cache

- Defina `MEMCACHED_SERVERS=host:11211` no `.env` para usar Memcached.
- Sem Memcached, o app usa `SimpleCache` em memória (processo local).

## 📱 PWA

- O app registra um Service Worker e manifesto.
- Em desktops, use “Instalar app” no navegador; em iOS, “Adicionar à Tela de Início”.

Dicas de atualização do SW:
- DevTools → Application → Service Workers → Update/Unregister → recarregue.

## 🔊 Texto‑para‑fala (TTS)

- Clicar no ícone de áudio lê o lembrete com voz pt‑BR.
- Se possível, instale vozes de Português (Brasil) no sistema para uma voz mais humana.

## 🧩 Endpoints principais

- `GET /` — Lembretes
- `POST /add` — Criar lembrete
- `GET /notes` — Notas
- `POST /notes/update/<id>` — Atualizar nota
- `POST /notes/delete/<id>` — Excluir nota
- `GET /api/reminders` — API de lembretes (cacheada por usuário)
- `GET /api/notifications` — API de notificações (curto prazo)

## 🧪 Testes rápidos

```powershell
# Teste de cache (serialização)
python .\test_cache_fix.py

# Teste de login e sessão
python .\test_login_debug.py

# Teste Memcached remoto
python .\test_memcached_remote.py
```

## 🐞 Troubleshooting

- “Preciso clicar duas vezes para atualizar”: limpe cache do navegador e Service Worker. Certifique‑se de que `/sw.js` foi atualizado e que cabeçalhos `Cache‑Control: no-store` estão chegando nas rotas dinâmicas.
- “Erro ao conectar MySQL”: valide `.env` e rode `python setup_mysql.py`.
- “Voz robótica no TTS”: instale uma voz pt‑BR nativa (Windows/Mac) ou use Chrome com vozes Google.

## 🤝 Contribuindo

- Issues e PRs são bem‑vindos! Siga um padrão simples de commits e abra PRs pequenos.

## 📜 Licença

Este repositório não define uma licença explícita. Avalie antes de uso em produção.
