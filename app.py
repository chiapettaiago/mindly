import os
import secrets
import time
import calendar as calendar_module
from datetime import datetime, timedelta

import pymysql
from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_caching import Cache
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError, generate_csrf
from sqlalchemy import inspect, or_, text
from werkzeug.security import check_password_hash, generate_password_hash

from forms import LoginForm, RegisterForm, ReminderForm
from models import Device, Note, Reminder, User, db
from reminder_parser import parse_reminder_text

load_dotenv()
pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'mudar-para-uma-chave-secreta')
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(hours=24)
app.config['APP_VERSION'] = os.environ.get('APP_VERSION', '0.1.0')
app.config['APP_MANUFACTURER'] = os.environ.get('APP_MANUFACTURER', 'Mindly')


def get_database_uri():
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        return database_url

    mysql_host = os.environ.get('MYSQL_HOST')
    mysql_port = os.environ.get('MYSQL_PORT', '3306')
    mysql_user = os.environ.get('MYSQL_USER')
    mysql_password = os.environ.get('MYSQL_PASSWORD')
    mysql_database = os.environ.get('MYSQL_DATABASE', 'mindly')

    if not all([mysql_host, mysql_user, mysql_password]):
        raise ValueError(
            'Configuração MySQL incompleta. Defina MYSQL_HOST, MYSQL_USER e MYSQL_PASSWORD, '
            'ou informe DATABASE_URL.'
        )

    return (
        f'mysql+pymysql://{mysql_user}:{mysql_password}'
        f'@{mysql_host}:{mysql_port}/{mysql_database}?charset=utf8mb4'
    )


app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
    'pool_timeout': 20,
    'max_overflow': 10,
}


def get_cache_config():
    memcached_servers = os.environ.get('MEMCACHED_SERVERS')
    if memcached_servers:
        try:
            import memcache

            test_client = memcache.Client([memcached_servers])
            test_key = f'mindly_health_check_{int(time.time())}'
            if test_client.set(test_key, 'ok', time=10):
                test_client.delete(test_key)
                print(f'Cache: usando Memcached remoto ({memcached_servers})')
                return {
                    'CACHE_TYPE': 'MemcachedCache',
                    'CACHE_MEMCACHED_SERVERS': [memcached_servers],
                    'CACHE_DEFAULT_TIMEOUT': 300,
                    'CACHE_KEY_PREFIX': 'mindly_',
                }
        except Exception as exc:
            print(f'Cache: Memcached indisponível ({exc}), usando fallback local')

    return {
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': 300,
        'CACHE_THRESHOLD': 1000,
        'CACHE_KEY_PREFIX': 'mindly_',
    }


for key, value in get_cache_config().items():
    app.config[key] = value

db.init_app(app)
csrf = CSRFProtect(app)
login = LoginManager(app)
login.login_view = 'login'
login.login_message = 'Faça login para acessar seus lembretes.'
login.login_message_category = 'info'
login.session_protection = 'basic'
cache = Cache(app)


def invalidate_user_cache(user_id):
    cache.delete(f'user_reminders_{user_id}')
    cache.delete(f'api_reminders_{user_id}')
    cache.delete(f'notifications_{user_id}')
    try:
        cache.set(f'notes_bust_{user_id}', int(time.time()), timeout=24 * 3600)
    except Exception:
        pass


@login.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def ensure_reminder_schema():
    inspector = inspect(db.engine)
    if 'reminder' not in inspector.get_table_names():
        return

    reminder_columns = {column['name'] for column in inspector.get_columns('reminder')}
    if 'reminder_text' not in reminder_columns:
        with db.engine.begin() as connection:
            connection.execute(text('ALTER TABLE reminder ADD COLUMN reminder_text VARCHAR(500) NULL'))


def initialize_database():
    db.create_all()
    ensure_reminder_schema()


with app.app_context():
    initialize_database()


@app.context_processor
def inject_globals():
    return {
        'app_version': app.config.get('APP_VERSION', 'dev'),
        'app_manufacturer': app.config.get('APP_MANUFACTURER', 'Mindly'),
        'csrf_token': lambda: generate_csrf(),
    }


@app.errorhandler(CSRFError)
def handle_csrf_error(_error):
    flash('Falha de segurança. Atualize a página e tente novamente.', 'danger')
    return redirect(request.referrer or url_for('index'))


def normalize_text(value):
    return ' '.join((value or '').strip().split())


def format_datetime_label(value):
    if not value:
        return None
    return value.strftime('%d/%m/%Y às %H:%M')


def compose_legacy_text(reminder, include_due=False):
    parts = [normalize_text(reminder.title)]
    if reminder.note:
        parts.append(normalize_text(reminder.note))
    base_text = ' - '.join(part for part in parts if part)

    if include_due and reminder.due:
        due_text = format_datetime_label(reminder.due)
        return normalize_text(f'{base_text} em {due_text}') if base_text else due_text

    return base_text


def reminder_input_value(reminder):
    return reminder.reminder_text or compose_legacy_text(reminder, include_due=True)


def reminder_display_text(reminder):
    title = normalize_text(reminder.title)
    if title:
        return title
    return compose_legacy_text(reminder, include_due=False)


def apply_reminder_text(reminder, raw_text):
    parsed = parse_reminder_text(raw_text, now=datetime.now())
    reminder.reminder_text = parsed['reminder_text']
    reminder.title = parsed['title'] or parsed['reminder_text'][:200]
    reminder.note = None
    reminder.due = parsed['due']
    return reminder


def serialize_reminder(reminder):
    return {
        'id': reminder.id,
        'display_text': reminder_display_text(reminder),
        'input_text': reminder_input_value(reminder),
        'title': reminder.title,
        'due': reminder.due.isoformat() if reminder.due else None,
        'due_label': format_datetime_label(reminder.due),
        'created': reminder.created.isoformat() if reminder.created else None,
        'created_label': format_datetime_label(reminder.created) if reminder.created else 'N/A',
        'done': reminder.done,
    }


class SimplePagination:
    def __init__(self, items, page, per_page, total):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = max((total + per_page - 1) // per_page, 1) if total else 0

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

    def iter_pages(self, left_edge=1, left_current=1, right_current=2, right_edge=1):
        last = 0
        for number in range(1, self.pages + 1):
            if (
                number <= left_edge
                or (self.page - left_current - 1 < number < self.page + right_current)
                or number > self.pages - right_edge
            ):
                if last + 1 != number:
                    yield None
                yield number
                last = number


def paginate_query(query, page, per_page):
    try:
        return db.paginate(query, page=page, per_page=per_page, error_out=False)
    except Exception:
        items = query.limit(per_page).offset((page - 1) * per_page).all()
        total = query.order_by(None).count()
        return SimplePagination(items, page, per_page, total)


def build_index_redirect():
    page = request.args.get('page', type=int)
    query = normalize_text(request.args.get('q', type=str, default=''))
    return redirect(url_for('index', page=page if page and page > 1 else None, q=query or None))


def build_reminder_redirect():
    if request.args.get('next') == 'calendar':
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        return redirect(url_for('calendar_view', year=year, month=month))
    return build_index_redirect()


def first_form_error(form):
    for errors in form.errors.values():
        if errors:
            return errors[0]
    return 'Verifique os dados enviados.'


def reminder_query_for_user(user_id, search_term=''):
    query = Reminder.query.filter_by(user_id=user_id)
    if search_term:
        like = f'%{search_term}%'
        query = query.filter(
            or_(
                Reminder.reminder_text.ilike(like),
                Reminder.title.ilike(like),
                Reminder.note.ilike(like),
            )
        )
    return query


@app.route('/sw.js')
def service_worker():
    response = send_from_directory(
        os.path.join(app.root_path, 'static'),
        'sw.js',
        mimetype='application/javascript',
    )
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/')
@login_required
def index():
    form = ReminderForm()
    page = request.args.get('page', type=int, default=1)
    query_text = normalize_text(request.args.get('q', type=str, default=''))
    per_page = 10

    reminders_query = reminder_query_for_user(current_user.id, query_text).order_by(
        Reminder.created.desc(),
        Reminder.id.desc(),
    )
    pagination = paginate_query(reminders_query, page, per_page)
    reminders = [serialize_reminder(reminder) for reminder in pagination.items]

    base_query = Reminder.query.filter_by(user_id=current_user.id)
    stats = {
        'total': base_query.count(),
        'pending': base_query.filter_by(done=False).count(),
        'scheduled': base_query.filter(Reminder.due.isnot(None), Reminder.done.is_(False)).count(),
    }

    return render_template(
        'index.html',
        form=form,
        reminders=reminders,
        pagination=pagination,
        q=query_text,
        stats=stats,
    )


@app.route('/calendar')
@login_required
def calendar_view():
    form = ReminderForm()
    today = datetime.now().date()
    requested_year = request.args.get('year', type=int, default=today.year)
    requested_month = request.args.get('month', type=int, default=today.month)

    if not 1 <= requested_month <= 12:
        requested_year = today.year
        requested_month = today.month

    month_start = datetime(requested_year, requested_month, 1)
    if requested_month == 12:
        next_month_start = datetime(requested_year + 1, 1, 1)
    else:
        next_month_start = datetime(requested_year, requested_month + 1, 1)
    month_end = next_month_start - timedelta(days=1)

    scheduled_reminders = (
        reminder_query_for_user(current_user.id)
        .filter(
            Reminder.due.isnot(None),
            Reminder.due >= month_start,
            Reminder.due < next_month_start,
        )
        .order_by(Reminder.due.asc(), Reminder.id.asc())
        .all()
    )

    reminders_by_date = {}
    for reminder in scheduled_reminders:
        reminder_date = reminder.due.date()
        reminders_by_date.setdefault(reminder_date, []).append(serialize_reminder(reminder))

    calendar_weeks = []
    calendar = calendar_module.Calendar(firstweekday=6)
    for week in calendar.monthdatescalendar(requested_year, requested_month):
        calendar_weeks.append(
            [
                {
                    'date': day,
                    'day': day.day,
                    'in_month': day.month == requested_month,
                    'is_today': day == today,
                    'count': len(reminders_by_date.get(day, [])),
                }
                for day in week
            ]
        )

    agenda_days = [
        {
            'date': day,
            'anchor': day.isoformat(),
            'label': day.strftime('%d/%m/%Y'),
            'weekday': day.strftime('%A'),
            'reminders': reminders,
        }
        for day, reminders in sorted(reminders_by_date.items())
    ]

    previous_month = month_start - timedelta(days=1)
    next_month = next_month_start
    unscheduled_count = (
        Reminder.query.filter(
            Reminder.user_id == current_user.id,
            Reminder.due.is_(None),
            Reminder.done.is_(False),
        ).count()
    )

    return render_template(
        'calendar.html',
        form=form,
        calendar_weeks=calendar_weeks,
        agenda_days=agenda_days,
        month_label=month_start.strftime('%m/%Y'),
        month_start=month_start,
        month_end=month_end,
        current_year=requested_year,
        current_month=requested_month,
        previous_month={'year': previous_month.year, 'month': previous_month.month},
        next_month={'year': next_month.year, 'month': next_month.month},
        today={'year': today.year, 'month': today.month},
        weekdays=['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'],
        scheduled_count=len(scheduled_reminders),
        unscheduled_count=unscheduled_count,
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Este email já está cadastrado.', 'danger')
            return redirect(url_for('register'))

        user = User(
            name=normalize_text(form.name.data),
            email=normalize_text(form.email.data).lower(),
            password=generate_password_hash(form.password.data),
        )
        db.session.add(user)
        db.session.commit()
        flash('Conta criada com sucesso. Faça login para continuar.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = normalize_text(form.email.data).lower()
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, form.password.data):
            remember = bool(form.remember.data)
            if remember:
                session.permanent = True

            login_user(user, remember=remember)

            response = redirect(url_for('index'))
            if remember:
                user_agent = (request.headers.get('User-Agent') or '')[:300]
                token = secrets.token_urlsafe(32)
                db.session.add(Device(user_id=user.id, token=token, user_agent=user_agent))
                db.session.commit()
                response.set_cookie('device_token', token, max_age=60 * 60 * 24 * 365, httponly=True)
            return response

        flash('Email ou senha inválidos.', 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão encerrada.', 'info')
    return redirect(url_for('login'))


@app.route('/logout_all', methods=['POST'])
@login_required
def logout_all():
    Device.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('Todos os dispositivos foram desconectados.', 'info')
    return redirect(url_for('index'))


@app.route('/add', methods=['POST'])
@login_required
def add_reminder():
    form = ReminderForm()
    if form.validate_on_submit():
        reminder = Reminder(user_id=current_user.id)
        apply_reminder_text(reminder, form.reminder_text.data)
        db.session.add(reminder)
        db.session.commit()
        invalidate_user_cache(current_user.id)
        flash('Lembrete criado.', 'success')
    else:
        flash(first_form_error(form), 'danger')
    return build_reminder_redirect()


@app.route('/update/<int:id>', methods=['POST'])
@login_required
def update_reminder(id):
    reminder = Reminder.query.get_or_404(id)
    if reminder.user_id != current_user.id:
        return 'Forbidden', 403

    raw_text = normalize_text(request.form.get('reminder_text', ''))
    if not raw_text:
        flash('Escreva o lembrete em um único campo antes de salvar.', 'danger')
        return build_index_redirect()
    if len(raw_text) > 500:
        flash('O lembrete pode ter no máximo 500 caracteres.', 'danger')
        return build_index_redirect()

    apply_reminder_text(reminder, raw_text)
    db.session.commit()
    invalidate_user_cache(current_user.id)
    flash('Lembrete atualizado.', 'success')
    return build_reminder_redirect()


@app.route('/toggle/<int:id>')
@login_required
def toggle_done(id):
    reminder = Reminder.query.get_or_404(id)
    if reminder.user_id != current_user.id:
        return 'Forbidden', 403

    reminder.done = not reminder.done
    db.session.commit()
    invalidate_user_cache(current_user.id)
    return build_reminder_redirect()


@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    reminder = Reminder.query.get_or_404(id)
    if reminder.user_id != current_user.id:
        return 'Forbidden', 403

    db.session.delete(reminder)
    db.session.commit()
    invalidate_user_cache(current_user.id)
    flash('Lembrete removido.', 'info')
    return build_reminder_redirect()


@app.route('/api/reminders')
@login_required
def api_reminders():
    cache_key = f'api_reminders_{current_user.id}'
    cached_reminders = cache.get(cache_key)
    if cached_reminders:
        return jsonify({'reminders': cached_reminders, 'cache_hit': True})

    reminders = reminder_query_for_user(current_user.id).order_by(
        Reminder.created.desc(),
        Reminder.id.desc(),
    ).all()
    reminders_data = [serialize_reminder(reminder) for reminder in reminders]
    cache.set(cache_key, reminders_data, timeout=30)
    return jsonify({'reminders': reminders_data, 'cache_hit': False})


@app.route('/api/notifications')
@login_required
def get_notifications():
    cache_key = f'notifications_{current_user.id}'
    cached_notifications = cache.get(cache_key)
    if cached_notifications:
        return jsonify(cached_notifications)

    now = datetime.now()
    upcoming = (
        Reminder.query.filter(
            Reminder.user_id == current_user.id,
            Reminder.done.is_(False),
            Reminder.due.isnot(None),
            Reminder.due <= now + timedelta(hours=24),
            Reminder.due >= now - timedelta(minutes=5),
        )
        .order_by(Reminder.due.asc())
        .all()
    )

    notifications = []
    for reminder in upcoming:
        seconds = (reminder.due - now).total_seconds()
        if seconds <= 3600:
            urgency = 'high'
        elif seconds <= 7200:
            urgency = 'medium'
        else:
            urgency = 'low'

        notifications.append(
            {
                'id': reminder.id,
                'title': reminder_display_text(reminder),
                'due': reminder.due.isoformat(),
                'urgency': urgency,
                'minutes_left': max(int(seconds / 60), 0),
            }
        )

    payload = {
        'notifications': notifications,
        'count': len(notifications),
        'timestamp': now.isoformat(),
    }
    cache.set(cache_key, payload, timeout=15)
    return jsonify(payload)


@app.route('/notes', methods=['GET', 'POST'])
@login_required
def notes():
    flash('As notas rápidas foram removidas. Use lembretes em texto livre.', 'info')
    return redirect(url_for('index'))


@app.route('/notes/update/<int:id>', methods=['POST'])
@login_required
def update_note(id):
    _note = Note.query.get_or_404(id)
    flash('As notas rápidas foram removidas. Use lembretes em texto livre.', 'info')
    return redirect(url_for('index'))


@app.route('/notes/delete/<int:id>', methods=['POST'])
@login_required
def delete_note(id):
    _note = Note.query.get_or_404(id)
    flash('As notas rápidas foram removidas. Use lembretes em texto livre.', 'info')
    return redirect(url_for('index'))


@app.after_request
def add_no_cache_headers(response):
    try:
        path = request.path or ''
        if (
            path in ('/', '/login', '/register', '/notes')
            or path == '/calendar'
            or path.startswith('/api/')
            or path.startswith('/delete/')
            or path.startswith('/toggle/')
            or path.startswith('/update/')
            or path.startswith('/notes/')
        ):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            vary = response.headers.get('Vary')
            response.headers['Vary'] = 'Cookie' if not vary else f'{vary}, Cookie'
    except Exception:
        pass
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000)
