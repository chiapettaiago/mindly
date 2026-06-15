from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class RegisterForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired(), Length(max=120)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Repita a senha', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Cadastrar')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember = BooleanField('Lembrar')
    submit = SubmitField('Entrar')

class ReminderForm(FlaskForm):
    reminder_text = StringField('Lembrete', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Salvar lembrete')

class NoteForm(FlaskForm):
    content = StringField('Nota', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Adicionar')
