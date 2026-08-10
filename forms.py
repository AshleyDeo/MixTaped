from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError

class RegisterForm(FlaskForm):
	username = StringField('Username', validators=[DataRequired(), Length(min=2, max=100)])
	email = StringField('Email', validators=[DataRequired(), Email()])
	password = PasswordField('Password', validators=[DataRequired()])
	confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
	submit = SubmitField('Create Account')

class LoginForm(FlaskForm):
	email = StringField('Email', validators=[DataRequired(), Email()])
	password = PasswordField('Password', validators=[DataRequired()])
	submit = SubmitField('Login')

class AudioForm(FlaskForm):
	song = FileField('Audio File')
	submit = SubmitField('Submit')

class ReviewForm(FlaskForm):
	review = StringField('Comment', validators=[DataRequired()])
	submit = SubmitField('Submit')