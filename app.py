import os
import secrets
from datetime import datetime, timedelta

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegisterForm, LoginForm, ReminderForm, NoteForm
from models import db, User, Reminder, Device, Note

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'mudar-para-uma-chave-secreta')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lembretes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=365)

db.init_app(app)
login = LoginManager(app)
login.login_view = 'login'

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

@app.route('/')
@login_required
def index():
    form = ReminderForm()
    q = request.args.get('q', type=str, default='')
    query = Reminder.query.filter_by(user_id=current_user.id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Reminder.title.ilike(like)) | 
            (Reminder.note.ilike(like))
        )
    reminders = query.order_by(Reminder.due.asc()).all()
    return render_template('index.html', reminders=reminders, form=form, q=q)

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
    return redirect(url_for('index'))

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    r = Reminder.query.get_or_404(id)
    if r.user_id != current_user.id:
        return 'Forbidden', 403
    db.session.delete(r)
    db.session.commit()
    flash('Lembrete removido', 'info')
    return redirect(url_for('index'))

@app.route('/api/reminders')
@login_required
def api_reminders():
    reminders = Reminder.query.filter_by(user_id=current_user.id).all()
    data = [r.to_dict() for r in reminders]
    return jsonify(data)

@app.route('/api/notifications')
@login_required
def get_notifications():
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
    
    return jsonify(notifications)

@app.route('/notes', methods=['GET', 'POST'])
@login_required
def notes():
    form = NoteForm()
    if form.validate_on_submit():
        n = Note(user_id=current_user.id, content=form.content.data)
        db.session.add(n)
        db.session.commit()
        flash('Nota adicionada', 'success')
        return redirect(url_for('notes'))
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
    return render_template('notes.html', form=form, notes=items, q=q, pagination=pagination)

@app.route('/notes/update/<int:id>', methods=['POST'])
@login_required
def update_note(id):
    n = Note.query.get_or_404(id)
    if n.user_id != current_user.id:
        return 'Forbidden', 403
    content = request.form.get('content', '').strip()
    if not content:
        flash('A nota não pode ficar vazia.', 'danger')
        return redirect(url_for('notes'))
    if len(content) > 500:
        flash('A nota deve ter no máximo 500 caracteres.', 'danger')
        return redirect(url_for('notes'))
    n.content = content
    db.session.commit()
    flash('Nota atualizada', 'success')
    return redirect(url_for('notes'))

@app.route('/notes/delete/<int:id>', methods=['POST'])
@login_required
def delete_note(id):
    n = Note.query.get_or_404(id)
    if n.user_id != current_user.id:
        return 'Forbidden', 403
    db.session.delete(n)
    db.session.commit()
    flash('Nota removida', 'info')
    return redirect(url_for('notes'))

if __name__ == '__main__':
    app.run(debug=True)
