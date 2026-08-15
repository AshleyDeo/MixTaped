from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import IntegerField, SelectField, StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length, Email, EqualTo, NumberRange, ValidationError

class RegisterForm(FlaskForm):
	username = StringField('Username', validators=[DataRequired(), Length(min=2, max=100)])
	email = StringField('Email', validators=[DataRequired(), Email()])
	password = PasswordField('Password', validators=[DataRequired()])
	confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
	submit = SubmitField('Create Account')

class UpdateUsernameForm(FlaskForm):
	username = StringField('Username', validators=[DataRequired(), Length(min=2, max=100)])
	submit = SubmitField('Update Username')

class UpdateEmailForm(FlaskForm):
	email = StringField('Email', validators=[DataRequired(), Email()])
	submit = SubmitField('Update Email')

class UpdatePasswordForm(FlaskForm):
	password = PasswordField('Password', validators=[DataRequired()])
	confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
	submit = SubmitField('Update Password')

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

class PlaylistForm(FlaskForm):
	name = StringField('Playlist Name', validators=[DataRequired(), Length(min=2, max=100)])
	description = TextAreaField("Description", validators=[])
	submit = SubmitField('Create Playlist')

class PlaylistNameForm(FlaskForm):
	name = StringField('Playlist Name', validators=[DataRequired(), Length(min=2, max=100)])
	submit = SubmitField('Update')

class DescriptionForm(FlaskForm):
	description = TextAreaField("Description", validators=[])
	submit = SubmitField('Update Description')

class SelectPlaylistForm(FlaskForm):
	playlists = SelectField('Playlist', choices=[(0, '')],
    default=0, coerce=int, validate_choice=False)
	submit = SubmitField('Add to Playlist')