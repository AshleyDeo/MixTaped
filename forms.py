from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import IntegerField, StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length, Email, EqualTo, NumberRange, ValidationError

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
	rating = IntegerField("Rating", validators=[DataRequired(), NumberRange(min=0, max=10)])
	review = TextAreaField("Comment", validators=[DataRequired()])
	submit = SubmitField('Submit')