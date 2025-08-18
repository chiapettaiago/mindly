import os
import secrets
import time
from datetime import datetime, timedelta
import pymysql

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

# Configurar PyMySQL como driver MySQL padrão
pymysql.install_as_MySQLdb()

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf, CSRFError
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_caching import Cache
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegisterForm, LoginForm, ReminderForm, NoteForm
from models import db, User, Reminder, Device, Note
from flask import send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegisterForm, LoginForm, ReminderForm, NoteForm
from models import db, User, Reminder, Device, Note
from flask import send_from_directory

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'mudar-para-uma-chave-secreta')

# Configurações de sessão mais robustas
app.config['SESSION_COOKIE_SECURE'] = False  # True apenas em HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # Aumentar para 24 horas

# Configuração do MySQL
def get_database_uri():
    """Constrói a URI do banco de dados MySQL a partir das variáveis de ambiente"""
    mysql_host = os.environ.get('MYSQL_HOST')
    mysql_port = os.environ.get('MYSQL_PORT', '3306')
    mysql_user = os.environ.get('MYSQL_USER')
    mysql_password = os.environ.get('MYSQL_PASSWORD')
    mysql_database = os.environ.get('MYSQL_DATABASE', 'mindly')
    
    # Verificar se todas as variáveis necessárias estão configuradas
    if not all([mysql_host, mysql_user, mysql_password]):
        raise ValueError(
            "Configuração MySQL incompleta. As seguintes variáveis de ambiente são obrigatórias:\n"
            "- MYSQL_HOST\n"
            "- MYSQL_USER\n" 
            "- MYSQL_PASSWORD\n"
            "- MYSQL_DATABASE (opcional, padrão: 'mindly')\n\n"
            "Configure essas variáveis no arquivo .env antes de executar o aplicativo."
        )
    
    return f'mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}?charset=utf8mb4'

app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
    'pool_timeout': 20,
    'max_overflow': 10
}
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(hours=24)  # Diminuir para 24 horas para testes
app.config['APP_VERSION'] = os.environ.get('APP_VERSION', '0.1.0')
app.config['APP_MANUFACTURER'] = os.environ.get('APP_MANUFACTURER', 'Mindly')

# Configuração do Cache (Memcached)
def invalidate_user_cache(user_id):
    """Invalida todos os caches relacionados a um usuário"""
    cache.delete(f'user_reminders_{user_id}')
    cache.delete(f'api_reminders_{user_id}')
    cache.delete(f'notifications_{user_id}')
    # Bump de versão do cache de notas para evitar chaves antigas
    try:
        cache.set(f'notes_bust_{user_id}', int(time.time()), timeout=24*3600)
    except Exception:
        pass

def get_cache_config():
    """Configura cache com fallback inteligente"""
    memcached_servers = os.environ.get('MEMCACHED_SERVERS')
    
    if memcached_servers:
        # Tenta configurar Memcached remoto
        try:
            import memcache
            
            # Teste rápido de conectividade
            test_client = memcache.Client([memcached_servers])
            test_key = f'mindly_health_check_{int(time.time())}'
            
            # Tenta uma operação simples com timeout curto
            if test_client.set(test_key, 'ok', time=10):
                test_client.delete(test_key)
                print(f"✅ Cache: Usando Memcached remoto ({memcached_servers})")
                
                return {
                    'CACHE_TYPE': 'MemcachedCache',
                    'CACHE_MEMCACHED_SERVERS': [memcached_servers],
                    'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutos
                    'CACHE_KEY_PREFIX': 'mindly_'
                }
            else:
                print(f"⚠️ Cache: Memcached remoto não responde, usando fallback")
                
        except ImportError:
            print("⚠️ Cache: python-memcached não disponível, usando fallback")
        except Exception as e:
            print(f"⚠️ Cache: Erro ao conectar Memcached remoto ({e}), usando fallback")
    
    # Fallback para SimpleCache (em memória)
    print("📝 Cache: Usando SimpleCache (em memória)")
    return {
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutos
        'CACHE_THRESHOLD': 1000,  # Máximo 1000 itens
        'CACHE_KEY_PREFIX': 'mindly_'
    }

# Aplicar configuração de cache
cache_config = get_cache_config()
for key, value in cache_config.items():
    app.config[key] = value

db.init_app(app)
csrf = CSRFProtect(app)
login = LoginManager(app)
login.login_view = 'login'
login.login_message = 'Por favor, faça login para acessar esta página.'
login.login_message_category = 'info'
login.session_protection = 'basic'  # Mudar de 'strong' para 'basic' para reduzir problemas

# Inicializar Cache
cache = Cache(app)

# Funções helper para cache
def invalidate_user_cache(user_id):
    """Invalida todos os caches relacionados a um usuário"""
    cache.delete(f'user_reminders_{user_id}')
    cache.delete(f'api_reminders_{user_id}')
    cache.delete(f'notifications_{user_id}')
    # Bump de versão do cache de notas para evitar chaves antigas
    try:
        cache.set(f'notes_bust_{user_id}', int(time.time()), timeout=24*3600)
    except Exception:
        pass

@login.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        return None

# Cria tabelas de forma compatível com diferentes versões do Flask
try:
    _ = app.before_first_request
except AttributeError:
    # versões mais recentes do Flask podem não expor before_first_request;
    # então criamos as tabelas imediatamente no contexto da aplicação
    with app.app_context():
        db.create_all()
else:
    @app.before_first_request
    def create_tables():
        db.create_all()

@app.context_processor
def inject_globals():
    return {
    'app_version': app.config.get('APP_VERSION', 'dev'),
    'app_manufacturer': app.config.get('APP_MANUFACTURER', 'Mindly'),
    'csrf_token': lambda: generate_csrf(),
    'range': range
    }

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash('Falha de segurança (CSRF). Atualize a página e tente novamente.', 'danger')
    return redirect(request.referrer or url_for('index'))

@app.route('/sw.js')
def service_worker():
    # Servir o service worker da raiz para ter escopo em todo o app
    resp = send_from_directory(os.path.join(app.root_path, 'static'), 'sw.js', mimetype='application/javascript')
    try:
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
    except Exception:
        pass
    return resp

@app.route('/')
@login_required
def index():
    """Página principal com cache inteligente"""
    form = ReminderForm()  # Adicionar o form necessário para o template
    user_id = current_user.id
    cache_key = f'user_reminders_{user_id}'
    
    # Tenta buscar do cache primeiro
    cached_data = cache.get(cache_key)
    if cached_data:
        return render_template('index.html', 
                             form=form,
                             reminders=cached_data, 
                             cache_hit=True)
    
    # Se não está no cache, busca do banco
    reminders = Reminder.query.filter_by(user_id=user_id).all()
    
    # Serializa os dados para cache (apenas dicionários/listas básicas)
    serializable_reminders = []
    for reminder in reminders:
        serializable_reminders.append({
            'id': reminder.id,
            'title': reminder.title,
            'note': reminder.note,
            'due': reminder.due.isoformat() if reminder.due else None,
            'created': reminder.created.isoformat() if reminder.created else None,
            'done': reminder.done,
            'user_id': reminder.user_id
        })
    
    # Salva no cache
    cache.set(cache_key, serializable_reminders, timeout=60)
    
    return render_template('index.html', 
                         form=form,
                         reminders=serializable_reminders, 
                         cache_hit=False)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email já cadastrado', 'danger')
            return redirect(url_for('register'))
        user = User(name=form.name.data, email=form.email.data,
                    password=generate_password_hash(form.password.data))
        db.session.add(user)
        db.session.commit()
        flash('Conta criada! Faça login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            remember = bool(form.remember.data)
            
            # Configurar sessão permanente se remember estiver marcado
            if remember:
                session.permanent = True
            
            login_user(user, remember=remember)

            # registrar dispositivo se o usuário pediu para ser lembrado
            if remember:
                token = secrets.token_urlsafe(32)
                ua = request.headers.get('User-Agent')[:300]
                device = Device(user_id=user.id, token=token, user_agent=ua)
                db.session.add(device)
                db.session.commit()
                # armazenar token no cookie para identificar dispositivo (opcional)
                resp = redirect(url_for('index'))
                resp.set_cookie('device_token', token, max_age=60*60*24*365)
                return resp

            return redirect(url_for('index'))
        flash('Credenciais inválidas', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/logout_all', methods=['POST'])
@login_required
def logout_all():
    # remove todos os dispositivos associados ao usuário
    Device.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('Logout em todos os dispositivos realizado', 'info')
    return redirect(url_for('index'))

@app.route('/add', methods=['POST'])
@login_required
def add_reminder():
    form = ReminderForm()
    if form.validate_on_submit():
        due = form.due.data or None
        r = Reminder(title=form.title.data, note=form.note.data, due=due, user_id=current_user.id)
        db.session.add(r)
        db.session.commit()
        
        # Invalidar cache do usuário
        invalidate_user_cache(current_user.id)
        
        flash('Lembrete adicionado', 'success')
    else:
        flash('Erro ao adicionar lembrete', 'danger')
    return redirect(url_for('index'))

@app.route('/toggle/<int:id>')
@login_required
def toggle_done(id):
    r = Reminder.query.get_or_404(id)
    if r.user_id != current_user.id:
        return 'Forbidden', 403
    r.done = not r.done
    db.session.commit()
    
    # Invalidar cache do usuário
    invalidate_user_cache(current_user.id)
    
    return redirect(url_for('index'))

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    r = Reminder.query.get_or_404(id)
    if r.user_id != current_user.id:
        return 'Forbidden', 403
    db.session.delete(r)
    db.session.commit()
    
    # Invalidar cache do usuário
    invalidate_user_cache(current_user.id)
    
    flash('Lembrete removido', 'info')
    return redirect(url_for('index'))

@app.route('/api/reminders')
@login_required
def api_reminders():
    """API de lembretes com cache por usuário"""
    user_id = current_user.id
    cache_key = f'api_reminders_{user_id}'
    
    # Busca do cache primeiro
    cached_reminders = cache.get(cache_key)
    if cached_reminders:
        return jsonify({
            'reminders': cached_reminders,
            'cache_hit': True
        })
    
    # Busca do banco se não está no cache
    reminders = Reminder.query.filter_by(user_id=user_id).all()
    
    # Serializa para JSON
    reminders_data = []
    for reminder in reminders:
        reminders_data.append({
            'id': reminder.id,
            'title': reminder.title,
            'note': reminder.note,
            'due': reminder.due.isoformat() if reminder.due else None,
            'created': reminder.created.isoformat() if reminder.created else None,
            'done': reminder.done
        })
    
    # Salva no cache
    cache.set(cache_key, reminders_data, timeout=30)
    
    return jsonify({
        'reminders': reminders_data,
        'cache_hit': False
    })

@app.route('/api/notifications')
@login_required
def get_notifications():
    """API de notificações com cache manual"""
    user_id = current_user.id
    cache_key = f'notifications_{user_id}'
    
    # Busca do cache
    cached_notifications = cache.get(cache_key)
    if cached_notifications:
        return jsonify(cached_notifications)
    
    # Usa horário local para casar com o valor salvo (datetime-local do formulário)
    now = datetime.now()
    # Busca lembretes no intervalo [-5min, +24h] não concluídos
    upcoming = Reminder.query.filter(
        Reminder.user_id == current_user.id,
        Reminder.done == False,
        Reminder.due != None,
        Reminder.due <= now + timedelta(hours=24),
        Reminder.due >= now - timedelta(minutes=5)
    ).order_by(Reminder.due.asc()).all()
    
    notifications = []
    for r in upcoming:
        time_diff = r.due - now
        seconds = time_diff.total_seconds()
        # Define urgência, tratando vencidos como alta urgência
        if seconds <= 0 or seconds <= 3600:  # vencido ou próxima hora
            urgency = 'high'
        elif seconds <= 7200:  # próximas 2 horas
            urgency = 'medium'
        else:
            urgency = 'low'
        
        minutes_left = int(seconds / 60)
        if minutes_left < 0:
            minutes_left = 0  # normaliza para não negativo
            
        notifications.append({
            'id': r.id,
            'title': r.title,
            'due': r.due.isoformat(),
            'urgency': urgency,
            'minutes_left': minutes_left
        })
    
    # Prepara dados para cache
    notification_data = {
        'notifications': notifications,
        'count': len(notifications),
        'timestamp': now.isoformat()
    }
    
    # Salva no cache por 15 segundos
    cache.set(cache_key, notification_data, timeout=15)
    
    return jsonify(notification_data)

@app.route('/notes', methods=['GET', 'POST'])
@login_required
def notes():
    form = NoteForm()
    if form.validate_on_submit():
        n = Note(user_id=current_user.id, content=form.content.data)
        db.session.add(n)
        db.session.commit()
        
        # Invalidar cache do usuário
        invalidate_user_cache(current_user.id)
        
        flash('Nota adicionada', 'success')
        return redirect(url_for('notes', t=int(time.time())), code=303)
    
    # Sem cache: sempre buscar do banco para evitar inconsistências
    q = request.args.get('q', type=str, default='')
    page = request.args.get('page', type=int, default=1)
    per_page = 50
    query = Note.query.filter_by(user_id=current_user.id)
    if q:
        like = f"%{q}%"
        query = query.filter(Note.content.ilike(like))
    query = query.order_by(Note.updated_at.desc())
    try:
        pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
        items = pagination.items
    except Exception:
        # Fallback simples caso paginate não esteja disponível
        items = query.limit(per_page).offset((page - 1) * per_page).all()
        class SimplePagination:
            def __init__(self, items, page, per_page, total):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = (total + per_page - 1) // per_page if per_page else 1
            @property
            def has_prev(self):
                return self.page > 1
            @property
            def has_next(self):
                return self.page < self.pages
            @property
            def prev_num(self):
                return self.page - 1
            @property
            def next_num(self):
                return self.page + 1
        total = query.count()
        pagination = SimplePagination(items, page, per_page, total)

    # Serializar para o template (mantém compatibilidade)
    serialized_items = []
    for note in items:
        serialized_items.append({
            'id': note.id,
            'user_id': note.user_id,
            'content': note.content,
            'created_at': note.created_at.isoformat() if note.created_at else None,
            'updated_at': note.updated_at.isoformat() if note.updated_at else None
        })

    pagination_info = {
        'page': pagination.page,
        'pages': pagination.pages,
        'has_prev': pagination.has_prev,
        'has_next': pagination.has_next,
        'prev_num': (pagination.prev_num if getattr(pagination, 'has_prev', False) else None),
        'next_num': (pagination.next_num if getattr(pagination, 'has_next', False) else None)
    }

    return render_template('notes.html', form=form, notes=serialized_items, 
                         q=q, pagination=pagination_info)

@app.route('/notes/update/<int:id>', methods=['POST'])
@login_required
def update_note(id):
    n = Note.query.get_or_404(id)
    if n.user_id != current_user.id:
        return 'Forbidden', 403
    content = request.form.get('content', '').strip()
    if not content:
        flash('A nota não pode ficar vazia.', 'danger')
        return redirect(url_for('notes'), code=303)
    if len(content) > 500:
        flash('A nota deve ter no máximo 500 caracteres.', 'danger')
        return redirect(url_for('notes'), code=303)
    n.content = content
    db.session.commit()
    
    # Invalidar cache do usuário
    invalidate_user_cache(current_user.id)
    
    flash('Nota atualizada', 'success')
    return redirect(url_for('notes', t=int(time.time())), code=303)

@app.route('/notes/delete/<int:id>', methods=['POST'])
@login_required
def delete_note(id):
    n = Note.query.get_or_404(id)
    if n.user_id != current_user.id:
        return 'Forbidden', 403
    db.session.delete(n)
    db.session.commit()
    
    # Invalidar cache do usuário
    invalidate_user_cache(current_user.id)
    
    flash('Nota removida', 'info')
    return redirect(url_for('notes', t=int(time.time())), code=303)

# Após inicializar app, configurar política de cache para rotas dinâmicas
@app.after_request
def add_no_cache_headers(response):
    try:
        path = request.path or ''
        # Desabilitar cache para páginas HTML e APIs
        if path in ('/', '/login', '/register', '/notes') or \
           path.startswith('/api/') or \
           path.startswith('/notes/') or \
           path.startswith('/delete/') or \
           path.startswith('/toggle/'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            # garantir variação por cookie/sessão
            existing_vary = response.headers.get('Vary')
            response.headers['Vary'] = 'Cookie' if not existing_vary else (existing_vary + ', Cookie')
    except Exception:
        pass
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
