Lembrete - App de lembretes com Flask e SQLite

Estrutura:
- app.py: aplicação Flask
- models.py: modelos SQLAlchemy
- forms.py: formulários WTForms
- templates/: templates Jinja2
- static/: assets (CSS, JS, ícones)

Instalação:
1. python -m venv venv
2. venv\Scripts\activate
3. pip install -r requirements.txt
4. set FLASK_APP=app.py; set FLASK_ENV=development; flask run
