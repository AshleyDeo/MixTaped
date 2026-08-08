import datetime as dt
import os 
import psycopg2
import re
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, request, render_template, session, url_for
#from flask_bcrypt import Bcrypt
from forms import RegisterForm, LoginForm, AudioForm
from tinytag import TinyTag
from werkzeug.utils import secure_filename

### SQL - CREATE TABLE
CREATE_TABLE_USERS = '''CREATE TABLE IF NOT EXISTS users (user_id SERIAL PRIMARY KEY, username VARCHAR(25) NOT NULL UNIQUE, password VARCHAR(30) NOT NULL, email VARCHAR(100) NOT NULL);'''

CREATE_TABLE_ARTISTS = '''CREATE TABLE IF NOT EXISTS artists (artist_id SERIAL PRIMARY KEY, name VARCHAR(50) NOT NULL, description TEXT);'''

CREATE_TABLE_ALBUMS = '''CREATE TABLE IF NOT EXISTS albums (album_id SERIAL PRIMARY KEY, album_title VARCHAR(25) NOT NULL, released varchar(6) DEFAULT "2026", UNIQUE (album_id, album_title));'''

CREATE_TABLE_SONGS = '''CREATE TABLE IF NOT EXISTS songs (song_id SERIAL, song_title VARCHAR(25) NOT NULL, album_id integer REFERENCES albums on delete cascade, length integer  DEFAULT 0 NOT NULL, track_number integer DEFAULT 0 NOT NULL, fileType VARCHAR(10), PRIMARY KEY (song_id, song_title, album_id));'''

CREATE_TABLE_GENRES = '''CREATE TABLE IF NOT EXISTS genres (genre_id SERIAL PRIMARY KEY, genre VARCHAR(25) NOT NULL UNIQUE);'''

CREATE_TABLE_PLAYLISTS = '''CREATE TABLE IF NOT EXISTS genres (playlist_id SERIAL PRIMARY KEY, user_id integer REFERENCES users on delete cascade, playlist_name VARCHAR(25) NOT NULL UNIQUE);'''

CREATE_TABLE_FILES = '''CREATE TABLE IF NOT EXISTS files (id SERIAL PRIMARY KEY, filename VARCHAR(255), file_url TEXT
);'''

### SQL - INSERT
INSERT_USER = '''INSERT INTO users (username, password, email) VALUES (%s, %s, %s) RETURNING *;'''
INSERT_GENRE = '''INSERT INTO genres (genre) VALUES (%s) RETURNING *;'''
INSERT_ARTIST = '''INSERT INTO artists (name) VALUES (%s) RETURNING *;'''
INSERT_ALBUM = '''INSERT INTO albums (album_title, released) VALUES (%s,%s) RETURNING *;'''
INSERT_SONG = '''INSERT INTO songs (song_title, length, track_number, album_id) VALUES (%s,%s,%s,%s) RETURNING *;'''

### SQL - SELECT
SELECT_USERS = '''SELECT * FROM users;'''
SELECT_ARTISTS = '''SELECT * FROM artists;'''
SELECT_ALBUMS = '''SELECT * FROM albums;'''
SELECT_SONGS = '''SELECT * FROM songs;'''
SELECT_GENRES = '''SELECT * FROM genres;'''

### SELECT WHERE
SELECT_USER_LOGIN = '''SELECT * FROM users WHERE email = %s AND password = %s;'''
SELECT_GENRE = '''SELECT * FROM genres WHERE genre = %s;'''
SELECT_ARTIST = '''SELECT * FROM artists WHERE name=%s;'''
SELECT_ALBUM = '''SELECT * FROM albums WHERE album_title=%s AND released=%s;'''
SELECT_SONG = '''SELECT * FROM songs WHERE song_title=%s AND album_id=%s '''

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
app.config['ALLOWED_EXTENSIONS'] = {'mp3', 'flac', 'jpeg', 'png'}
app.config['AUDIO_EXTENSIONS'] = ['.mp3', '.flac']
app.config['UPLOAD_AUDIO_PATH'] = 'uploads/music'

connection = psycopg2.connect(database=os.environ.get("DB_NAME"), user=os.environ.get("DB_USER"), password=os.environ.get("DB_PASSWORD"), host=os.environ.get("DB_HOST"), port=os.environ.get("DB_PORT"))

def parseAudioData(file):
	data = TinyTag.get(file)
	print(data.artist) 
	print(data.other.get('artist'))
	## data.year: 2017-06-17 -- datetime.strptime('2014-12-04', '%Y-%m-%d').date()
	genre_ids = []
	artist_ids = []
	with connection:
		with connection.cursor() as cursor:
			for g in re.split(r'[;,/]+', data.genre):
				g = g.strip()
				print(g)
				if type(g) is not None:
					# print(type(g))
					cursor.execute(SELECT_GENRE, (g,))
					genre = cursor.fetchone()
					if genre is None:
						cursor.execute(INSERT_GENRE, (g,))
						genre = cursor.fetchone()
					genre_ids.append(genre[0])

			cursor.execute(SELECT_ARTIST, (data.artist,))
			artist = cursor.fetchone()
			if artist is None:
				cursor.execute(INSERT_ARTIST, (data.artist,))
				artist = cursor.fetchone()
			artist_ids.append(genre[0])

			if data.other.get('artist'):
				for a in re.split(r'[;,/]+', data.other.get('artist')):
					print(a)
					if type(a) is not None:
						# print(type(a))
						cursor.execute(SELECT_ARTIST, (a,))
						artist = cursor.fetchone()
						if artist is None:
							cursor.execute(INSERT_ARTIST, (a,))
							artist = cursor.fetchone()
						artist_ids.append(artist[0])
			cursor.execute(SELECT_ALBUM, (data.album, dt.datetime.strptime(data.year, '%Y-%m-%d').date()))			
			album = cursor.fetchone()
			if album is None:
				cursor.execute(INSERT_ALBUM, (data.album, dt.datetime.strptime(data.year, '%Y-%m-%d').date()))			
				album = cursor.fetchone()

			print(type(album[0]))
			cursor.execute(SELECT_SONG, (data.title, album[0])) 
			song = cursor.fetchone()
			if song is None:
				cursor.execute(INSERT_SONG, (data.title, data.duration, data.track, album[0]))
				song = cursor.fetchone()

	return None

@app.route('/')
def index():
	with connection:
		with connection.cursor() as cursor:
			cursor.execute(CREATE_TABLE_FILES)
			cursor.execute(CREATE_TABLE_USERS)
			cursor.execute(CREATE_TABLE_ARTISTS)
			cursor.execute(CREATE_TABLE_ALBUMS)
			cursor.execute(CREATE_TABLE_SONGS)
			cursor.execute(CREATE_TABLE_GENRES)
			cursor.execute(SELECT_USERS)
			data_1 = cursor.fetchall()
			cursor.execute(SELECT_ARTISTS)
			data_2 = cursor.fetchall()
			cursor.execute(SELECT_ALBUMS)
			data_3 = cursor.fetchall()
			cursor.execute(SELECT_SONGS)
			data_4 = cursor.fetchall()
			cursor.execute(SELECT_GENRES)
			data_5 = cursor.fetchall()
	
	return render_template('index.html', tables=[data_1, data_2, data_3, data_4, data_5])

@app.route('/login', methods=['GET', 'POST'])
def login():
	form = LoginForm()
	
	if form.validate_on_submit():
		with connection:
			with connection.cursor() as cursor:
				cursor.execute(CREATE_TABLE_USERS)
				cursor.execute(SELECT_USER_LOGIN, (form.email.data, form.password.data))
				user = cursor.fetchone()
				print(f'{user} has logged in!!')
				if user is None:
					print("User not found!!")
					flash('Login Failed!! Please check email or password.', 'danger')
					return redirect(url_for('login'))
				else:
					session['user_id'] = user[0]
					session['username'] = user[1]
					flash('Your have been logged in!!', 'success')
					return redirect(url_for('dashboard'))
	return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
	form = RegisterForm()
	if form.validate_on_submit():
		with connection:
			with connection.cursor() as cursor:
				cursor.execute(CREATE_TABLE_USERS)
				cursor.execute(INSERT_USER, (form.username.data, form.password.data, form.email.data))
				user = cursor.fetchone()[0]
				print(f'New User: {user}')
				flash('Your account has been created!!', 'success')
				return redirect(url_for('login'))
      
	return render_template('register.html', form=form)

@app.route('/logout', methods=['GET'])
def logout():
	session.pop('user_id')
	session.pop('username')
	flash('You have been logged out!', 'success')
	return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET'])
def dashboard():
	if 'user_id' not in session:
		return redirect(url_for('login'))
	return render_template("dashboard.html")

@app.route('/upload', methods=['GET','POST'])
def upload():
	form = AudioForm()
	if form.validate_on_submit():
		file = form.song.data
		filename = secure_filename(file.filename)
		if filename != '':
			file_ext = os.path.splitext(filename)[1]
			print(file_ext)
			if file_ext not in app.config['AUDIO_EXTENSIONS']:
				flash(f'Wrong File Type!! Use mp3 or flac')
				abort(400)
			filepath = os.path.join(app.config['UPLOAD_AUDIO_PATH'], filename)
			file.save(filepath)
			parseAudioData(filepath) 
			flash(f'Upload successful: {filename}')
		return redirect(url_for('upload'))
	return render_template('upload.html', form=form)

if __name__ == '__main__':
	app.run(debug=True)