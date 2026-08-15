import datetime as dt
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import re
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, request, render_template, session, url_for
#from flask_bcrypt import Bcrypt
from forms import DescriptionForm, PlaylistForm, PlaylistNameForm, SelectPlaylistForm, RegisterForm, LoginForm, AudioForm, ReviewForm, UpdateEmailForm, UpdatePasswordForm, UpdateUsernameForm
from tinytag import TinyTag
from werkzeug.utils import secure_filename

### SQL - CREATE TABLE
CREATE_TABLE_USERS = '''CREATE TABLE IF NOT EXISTS users (
	user_id SERIAL PRIMARY KEY, 
	username VARCHAR(25) NOT NULL UNIQUE, 
	password VARCHAR(30) NOT NULL, 
	email VARCHAR(100) NOT NULL
);'''
CREATE_TABLE_ARTISTS = '''CREATE TABLE IF NOT EXISTS artists (
	artist_id SERIAL PRIMARY KEY, 
	name VARCHAR(50) NOT NULL, 
	description TEXT
);'''
CREATE_TABLE_ALBUMS = '''CREATE TABLE IF NOT EXISTS albums (
	album_id SERIAL PRIMARY KEY, 
	album_title VARCHAR(50) NOT NULL, 
	artist_id integer REFERENCES artists ON DELETE CASCADE, 
	released date NOT NULL DEFAULT now(), 
	UNIQUE (album_id, album_title)
);'''
CREATE_TABLE_SONGS = '''CREATE TABLE IF NOT EXISTS songs (
	song_id SERIAL PRIMARY KEY, 
	song_title VARCHAR(50) NOT NULL, 
	album_id integer REFERENCES albums ON DELETE CASCADE, 
	length integer  DEFAULT 0 NOT NULL, 
	track_number integer DEFAULT 0 NOT NULL
);'''
CREATE_TABLE_GENRES = '''CREATE TABLE IF NOT EXISTS genres (genre_id SERIAL PRIMARY KEY, genre VARCHAR(25) NOT NULL UNIQUE);'''
CREATE_TABLE_PLAYLISTS = '''CREATE TABLE IF NOT EXISTS playlists(
playlist_id SERIAL NOT NULL PRIMARY KEY, 
playlist_name varchar(100), 
description text, 
date_created timestamp DEFAULT now(), 
user_id integer NOT NULL REFERENCES users ON DELETE CASCADE);'''
CREATE_ALBUM_REVIEWS = '''CREATE TABLE IF NOT EXISTS album_reviews (
	album_review_id SERIAL, 
	user_id integer NOT NULL REFERENCES users (user_id) ON DELETE CASCADE, 
	album_id integer NOT NULL REFERENCES albums (album_id) ON DELETE CASCADE, 
	rating integer, 
	review text, 
	review_date timestamp DEFAULT now(),
	PRIMARY KEY (album_review_id, user_id, album_id)
);'''
CREATE_SONG_REVIEWS = '''CREATE TABLE IF NOT EXISTS song_reviews (
	song_review_id SERIAL, 
	user_id integer REFERENCES users (user_id) ON DELETE CASCADE, 
	song_id integer REFERENCES songs (song_id) ON DELETE CASCADE, 
	rating integer, 
	review text, 
	review_date timestamp DEFAULT now(),
	PRIMARY KEY (song_review_id, user_id, song_id)
);''' 
CREATE_ARTIST_GENRES = '''CREATE TABLE IF NOT EXISTS artist_genres (
    artist_id integer REFERENCES artists ON DELETE CASCADE,
    genre_id integer REFERENCES genres ON DELETE CASCADE, 
	PRIMARY KEY (artist_id, genre_id)
);'''
CREATE_SONG_GENRES = '''CREATE TABLE IF NOT EXISTS song_genres (
    song_id integer REFERENCES songs ON DELETE CASCADE,
    genre_id integer REFERENCES genres ON DELETE CASCADE, 
	PRIMARY KEY (song_id, genre_id)
);'''
CREATE_TABLE_FILES = '''CREATE TABLE IF NOT EXISTS files (id SERIAL PRIMARY KEY, filename VARCHAR(10), file_url TEXT);'''
CREATE_PLAYLIST_SONGS = '''CREATE TABLE IF NOT EXISTS playlist_songs (
    playlist_id integer REFERENCES playlists ON DELETE CASCADE,
    song_id integer REFERENCES songs ON DELETE CASCADE,
	playlist_position integer DEFAULT 1,
	date_added timestamp DEFAULT now() NOT NULL, 
	PRIMARY KEY (playlist_id, song_id)
);'''

### SQL - SELECT
SELECT_USERS = '''SELECT * FROM users;'''
SELECT_USERNAME = '''SELECT user_id FROM users WHERE username=%s;'''
SELECT_EMAIL = '''SELECT user_id FROM users WHERE email =%s;'''
SELECT_ARTISTS = '''SELECT * FROM artists;'''
SELECT_ALBUMS = '''SELECT * FROM albums;'''
SELECT_SONGS = '''SELECT * FROM songs;'''
SELECT_GENRES = '''SELECT * FROM genres;'''
SELECT_SONG_GENRES = '''SELECT * FROM song_genres;'''
SELECT_ARTIST_GENRES = '''SELECT * FROM artist_genres;'''
SELECT_SONG_REVIEWS = '''SELECT * FROM song_reviews WHERE song_id=%s;'''
SELECT_ALBUM_REVIEWS = '''SELECT * FROM album_reviews WHERE album_id=%s;'''
SELECT_USER_PLAYLISTS = '''SELECT playlists.*, 
(SELECT COUNT(*) FROM playlist_songs WHERE playlist_songs.playlist_id=playlists.playlist_id)
FROM playlists WHERE user_id=%s
ORDER BY playlist_name ASC;'''
SELECT_USER_PLAYLIST_IDS = '''SELECT playlist_id, playlist_name FROM playlists WHERE user_id=%s ORDER BY playlist_name;'''
SELECT_PLAYLIST_SONGS_TABLE ='''SELECT * FROM playlist_songs'''

### SELECT WHERE
SELECT_USER_LOGIN = '''SELECT * FROM users WHERE email = %s AND password = %s;'''
SELECT_GENRE = '''SELECT * FROM genres WHERE genre = %s;'''
SELECT_ARTIST = '''SELECT * FROM artists WHERE name=%s;'''
SELECT_ALBUM = '''SELECT * FROM albums WHERE album_title=%s AND artist_id=%s AND released=%s;'''
SELECT_SONG = '''SELECT * FROM songs WHERE song_title=%s AND album_id=%s;'''
SELECT_SONG_BY_ID = '''SELECT * FROM songs JOIN albums ON songs.album_id=albums.album_id JOIN artists ON albums.artist_id=artists.artist_id  WHERE song_id=%s;'''
SELECT_SONGS_BY_ALBUM_ID = '''SELECT * FROM songs WHERE album_id=%s ORDER BY track_number ASC;'''
SELECT_SONG_NAME = '''SELECT * FROM songs WHERE song_title ILIKE %s;'''
INSERT_ARTIST_GENRE = '''INSERT INTO artist_genres (artist_id, genre_id) VALUES (%s,%s) RETURNING *;'''
SELECT_REVIEWS_BY_SONGID = '''SELECT song_reviews.*, users.username FROM song_reviews 
JOIN users ON song_reviews.user_id=users.user_id
WHERE song_id=%s;'''
SELECT_ALBUM_BY_ID = '''SELECT * FROM albums JOIN artists ON albums.artist_id=artists.artist_id  WHERE album_id=%s;'''
SELECT_REVIEWS_BY_ALBUMID = '''SELECT album_reviews.*, users.username FROM album_reviews 
JOIN users ON album_reviews.user_id=users.user_id
WHERE album_id=%s;'''
SELECT_GENRES_BY_SONG_ID = '''SELECT genres.* FROM song_genres JOIN genres ON song_genres.genre_id=genres.genre_id WHERE song_id=%s;'''
SELECT_GENRES_BY_ALBUM_ID = '''SELECT genres.* FROM songs JOIN song_genres ON songs.song_id=song_genres.song_id JOIN genres ON song_genres.genre_id=genres.genre_id WHERE album_id=%s;'''
SELECT_SONG_GENRE = '''SELECT * FROM song_genres WHERE genre_id=%s AND song_id=%s;'''
SELECT_ARTIST_GENRE = '''SELECT * FROM artist_genres WHERE genre_id=%s AND artist_id=%s;'''
SELECT_ARTIST_BY_ID = '''SELECT * FROM artists WHERE artist_id=%s;'''
SELECT_GENRE_BY_ID = '''SELECT * FROM genres WHERE genre_id=%s;'''
SELECT_ALBUMS_BY_ARTIST_ID = '''SELECT * FROM albums WHERE artist_id=%s ORDER BY released DESC;'''
SELECT_GENRES_BY_ARTIST_ID = '''SELECT DISTINCT genres.* FROM artist_genres JOIN genres ON artist_genres.genre_id=genres.genre_id WHERE artist_id=%s GROUP BY genres.genre_id;'''
SELECT_GENRES_BY_ALBUM_ID = '''SELECT DISTINCT genres.* FROM songs
JOIN song_genres ON songs.song_id=song_genres.song_id
JOIN genres ON song_genres.genre_id=genres.genre_id 
WHERE songs.album_id=%s GROUP BY genres.genre_id;'''
SELECT_ARTISTS_BY_GENRE_ID = '''SELECT artists.* FROM artist_genres JOIN artists ON artist_genres.artist_id=artists.artist_id WHERE genre_id=%s;'''
SELECT_SONGS_BY_GENRE_ID = '''SELECT songs.*, artists.artist_id, artists.name FROM song_genres 
JOIN songs ON song_genres.song_id=songs.song_id 
JOIN albums ON songs.album_id=albums.album_id 
JOIN artists ON albums.artist_id=artists.artist_id 
WHERE genre_id=%s;'''
SELECT_ALBUM_REVIEW = '''SELECT * FROM album_reviews WHERE album_id=%s AND user_id=%s;'''
SELECT_SONG_REVIEW = '''SELECT * FROM song_reviews WHERE song_id=%s AND user_id=%s;'''
SELECT_PLAYLIST = '''SELECT playlists.*, users.user_id, users.username FROM playlists
JOIN users ON playlists.user_id=users.user_id
WHERE playlist_id=%s;'''
SELECT_PLAYLIST_SONGS = '''SELECT * FROM playlist_songs
JOIN songs ON playlist_songs.song_id=songs.song_id
WHERE playlist_id=%s ORDER BY playlist_songs.playlist_position ASC, playlist_songs.date_added DESC;''' 
SELECT_PLAYLIST_SONG = '''SELECT * FROM playlist_songs WHERE playlist_id=%s AND song_id=%s;'''
SELECT_ADDED_SONG_INFO = '''SELECT songs.song_title, playlists.playlist_name FROM playlist_songs
JOIN songs ON playlist_songs.song_id=songs.song_id
JOIN playlists ON playlist_songs.playlist_id=playlists.playlist_id
WHERE playlist_songs.playlist_id=%s AND playlist_songs.song_id=%s;'''
CHECK_PLAYLIST_ALBUM = '''SELECT song_id, songs.song_title FROM songs WHERE album_id=%s AND song_id NOT IN
(SELECT song_id FROM playlist_songs WHERE  playlist_songs.playlist_id=%s);'''

### SQL - INSERT
INSERT_USER = '''INSERT INTO users (username, password, email) VALUES (%s, %s, %s) RETURNING *;'''
INSERT_GENRE = '''INSERT INTO genres (genre) VALUES (%s) RETURNING *;'''
INSERT_ARTIST = '''INSERT INTO artists (name) VALUES (%s) RETURNING *;'''
INSERT_ARTIST_GENRE = '''INSERT INTO artist_genres (artist_id, genre_id) VALUES (%s,%s) RETURNING *;'''
INSERT_ALBUM = '''INSERT INTO albums (album_title, artist_id, released) VALUES (%s,%s,%s) RETURNING *;'''
INSERT_SONG = '''INSERT INTO songs (song_title, length, track_number, album_id) VALUES (%s,%s,%s,%s) RETURNING *;'''
INSERT_SONG_REVIEW = '''INSERT INTO song_reviews (song_id, user_id, rating, review) VALUES (%s,%s,%s,%s) RETURNING *;'''
INSERT_ALBUM_REVIEW = '''INSERT INTO album_reviews (album_id, user_id, rating, review) VALUES (%s,%s,%s,%s) RETURNING *;'''
INSERT_ARTIST_GENRE = '''INSERT INTO artist_genres (genre_id, artist_id) VALUES (%s,%s) RETURNING *;'''
INSERT_SONG_GENRE = '''INSERT INTO song_genres (genre_id,song_id) VALUES (%s,%s) RETURNING *;'''
INSERT_SONG_REVIEW = '''INSERT INTO song_reviews (user_id, song_id, rating, review) VALUES (%s,%s,%s,%s) RETURNING *;'''
INSERT_ALBUM_REVIEW = '''INSERT INTO album_reviews (user_id, album_id, rating, review) VALUES (%s,%s,%s,%s) RETURNING *;'''
INSERT_PLAYLIST = '''INSERT INTO playlists (user_id, playlist_name, description) VALUES (%s,%s,%s) RETURNING *;'''
INSERT_PLAYLIST_SONG = '''INSERT INTO playlist_songs (playlist_id, song_id) VALUES (%s,%s) RETURNING *;'''
INSERT_PLAYLIST_ALBUM = '''INSERT INTO playlist_songs (playlist_id, song_id) VALUES (%s, SELECT song_id FROM songs WHERE album_id = %s) RETURNING *;'''

#UPDATE
UPDATE_ALBUM_REVIEW = '''UPDATE album_reviews SET rating=%s, review=%s, review_date=now() WHERE album_id=%s AND user_id=%s RETURNING *'''
UPDATE_SONG_REVIEW = '''UPDATE song_reviews SET rating=%s, review=%s, review_date=now() WHERE song_id=%s AND user_id=%s  RETURNING *'''
UPDATE_USERNAME = '''UPDATE users SET username=%s WHERE user_id =%s RETURNING *;'''
UPDATE_EMAIL = '''UPDATE users SET email=%s WHERE user_id =%s RETURNING *;'''
UPDATE_PASSWORD = '''UPDATE users SET password=%s WHERE user_id =%s RETURNING *;'''
UPDATE_ARTIST_DESC = '''UPDATE artists SET description=%s WHERE artist_id=%s RETURNING *;'''
UPDATE_PLAYLIST_NAME = '''UPDATE playlists SET playlist_name=%s WHERE playlist_id=%s RETURNING *;'''
UPDATE_PLAYLIST_DESC = '''UPDATE playlists SET description=%s WHERE playlist_id=%s RETURNING *;'''

#DELETE
DELETE_USER = '''DELETE FROM users WHERE user_id=%s RETURNING *;'''
DELETE_PLAYLIST = '''DELETE FROM playlists WHERE playlist_id=%s RETURNING *;'''
DELETE_PLAYLIST_SONG = '''DELETE FROM playlist_songs WHERE playlist_id=%s AND song_id=%s RETURNING *;'''

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
app.config['ALLOWED_EXTENSIONS'] = {'mp3', 'flac', 'jpeg', 'png'}
app.config['AUDIO_EXTENSIONS'] = ['.mp3', '.flac']
app.config['UPLOAD_AUDIO_PATH'] = 'uploads/music'

connection = psycopg2.connect(database=os.environ.get("DB_NAME"), user=os.environ.get("DB_USER"), password=os.environ.get("DB_PASSWORD"), host=os.environ.get("DB_HOST"), port=os.environ.get("DB_PORT"))

def parseAudioData(file, file_ext):
	data = TinyTag.get(file)
	print(data.artist) 
	print(data.other.get('artist'))
	## data.year: 2017-06-17 -- datetime.strptime('2014-12-04', '%Y-%m-%d').date()
	genres = []
	if data.genre is not None:
		genres = re.split(r'[;,/]+', data.genre)
	genre_ids = []
	artist_ids = []
	with connection:
		with connection.cursor() as cursor:
			for g in genres:
				if type(g) is not None:
					g = g.strip()
					#print(g)
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
			artist_ids.append(artist[0])

			if data.other.get('artist'):
				#print(data.other.get('artist'))
				for a in data.other.get('artist'):
					#print(f'TEST: {a}')
					if type(a) is not None:
						# print(type(a))
						cursor.execute(SELECT_ARTIST, (a,))
						artist = cursor.fetchone()
						if artist is None:
							cursor.execute(INSERT_ARTIST, (a,))
							artist = cursor.fetchone()
						artist_ids.append(artist[0])

			release_date = dt.datetime.strptime(data.year, '%Y-%m-%d').date()
			cursor.execute(SELECT_ALBUM, (data.album, artist[0], release_date))		
			album = cursor.fetchone()
			if album is None:
				cursor.execute(INSERT_ALBUM, (data.album, artist[0], release_date))			
				album = cursor.fetchone()

			print(type(album[0]))
			cursor.execute(SELECT_SONG, (data.title, album[0])) 
			song = cursor.fetchone()
			if song is None:
				cursor.execute(INSERT_SONG, (data.title, data.duration, data.track, album[0]))
				song = cursor.fetchone()

			for id in genre_ids:
				if id is not None:
					# print(type(g))
					cursor.execute(SELECT_SONG_GENRE, (id,song[0]))
					genre = cursor.fetchone()
					if genre is None:
						cursor.execute(INSERT_SONG_GENRE, (id,song[0]))
						genre = cursor.fetchone()

				for a_id in artist_ids:
					if id is not None:
						# print(type(g))
						cursor.execute(SELECT_ARTIST_GENRE, (id,a_id))
						genre = cursor.fetchone()
						if genre is None:
							cursor.execute(INSERT_ARTIST_GENRE, (id,a_id))
							genre = cursor.fetchone()
	return None

@app.route('/')
def index():
	with connection:
		with connection.cursor() as cursor:
			cursor.execute(CREATE_TABLE_USERS)
			cursor.execute(CREATE_TABLE_GENRES)
			cursor.execute(CREATE_TABLE_ARTISTS)
			cursor.execute(CREATE_TABLE_ALBUMS)
			cursor.execute(CREATE_TABLE_SONGS)
			cursor.execute(CREATE_TABLE_PLAYLISTS)
			cursor.execute(CREATE_ALBUM_REVIEWS)
			cursor.execute(CREATE_SONG_REVIEWS)
			cursor.execute(CREATE_ARTIST_GENRES)
			cursor.execute(CREATE_SONG_GENRES)
			cursor.execute(CREATE_PLAYLIST_SONGS)
			#cursor.execute(CREATE_TABLE_FILES)
			print("Tables created!!")
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
			cursor.execute(SELECT_SONG_GENRES)
			data_6 = cursor.fetchall()
			cursor.execute(SELECT_ARTIST_GENRES)
			data_7 = cursor.fetchall()
			cursor.execute(SELECT_PLAYLIST_SONGS_TABLE)
			data_8 = cursor.fetchall()
	
	return render_template('index.html', tables=[data_1, data_2, data_3, data_4, data_5, data_6, data_7, data_8])

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
		if form.validate() == False:
			flash('All Fields are required.')
			return  redirect(url_for('register'))
		with connection:
			with connection.cursor() as cursor:
				cursor.execute(CREATE_TABLE_USERS)
				cursor.execute(SELECT_USERNAME, (form.username.data,))
				users = cursor.fetchone()
				if users:
					flash("Username already taken!!")
					return redirect(url_for('register'))
				cursor.execute(SELECT_EMAIL, (form.email.data,))
				users = cursor.fetchone()
				if users:
					flash("Email already in use!!")
					return redirect(url_for('register'))
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

@app.route('/settings', methods=['GET','POST'])
def settings():
	form1 = UpdateUsernameForm()
	form2 = UpdateEmailForm()
	form3 = UpdatePasswordForm()

	if form1.validate_on_submit():
		with connection:
			with connection.cursor() as cursor:
				cursor.execute(SELECT_USERNAME, (form1.username.data,))
				users = cursor.fetchone()
				if users is None:
					cursor.execute(UPDATE_USERNAME, (form1.username.data, session['user_id']))
					session['username'] = form1.username.data
				else:
					flash("Username already taken!")
				return redirect(url_for('settings'))

	if form2.validate_on_submit():
		with connection:
			with connection.cursor() as cursor:
				cursor.execute(SELECT_EMAIL, (form2.email.data,))
				users = cursor.fetchone()
				if users is None:
					cursor.execute(UPDATE_EMAIL, (form2.email.data, session['user_id']))
				else:
					flash("Email already in use!")
				return redirect(url_for('settings'))

	if form3.validate_on_submit():
		with connection:
			with connection.cursor() as cursor:
				cursor.execute(UPDATE_PASSWORD, (form3.password.data, session['user_id']))
				flash("Password has been updated!")
				return redirect(url_for('settings'))
	return render_template('settings.html', forms=[form1, form2, form3], id=session['user_id'])

@app.route('/delete/user/<id>', methods=['GET'])
def delete_user(id=None):
	with connection: 
		with connection.cursor() as cursor:
			cursor.execute(DELETE_USER, (id,))
			user = cursor.fetchall()
			flash('Account has been deleted!', 'success')
			if session['user_id']:
				return redirect(url_for('logout'))
			return redirect(url_for('index'))
	flash('Account deletion unsuccessful!', 'error')
	return render_template('settings.html') 

@app.route('/delete/playlist_song/<pid>/<sid>', methods=['GET'])
def delete_playlist_song(pid=None, sid=None):
	with connection: 
		with connection.cursor() as cursor:
			cursor.execute(DELETE_PLAYLIST_SONG, (pid,sid))
			song = cursor.fetchall()
			print(song)
			if song:
				flash('Song removed from playlist!', 'success')
			return redirect(url_for('playlistInfo', id=pid))
	flash('Could not remove from playlist!', 'error')
	return redirect(url_for('playlistInfo', id=pid)) 

@app.route('/delete/playlist/<id>', methods=['GET'])
def delete_playlist(id=None):
	with connection: 
		with connection.cursor() as cursor:
			cursor.execute(DELETE_PLAYLIST, (id,))
			playlist = cursor.fetchall()
			print(playlist)
			if playlist:
				flash('Playlist deleted!!', 'success')
			return redirect(url_for('dashboard'))
	flash('Could not delete playlist!', 'error')
	return redirect(url_for('dashboard')) 

@app.route('/dashboard', methods=['GET','POST'])
def dashboard():
	form=PlaylistForm()
	if 'user_id' not in session:
		return redirect(url_for('login'))
	
	if form.validate_on_submit():
		with connection:
			with connection.cursor() as cursor:
				cursor.execute(INSERT_PLAYLIST, (session['user_id'], form.name.data, form.description.data))
				return(redirect(url_for('dashboard')))
	with connection:
		with connection.cursor() as cursor:
			cursor.execute(SELECT_USER_PLAYLISTS, (session['user_id'],))
			playlists = cursor.fetchall()
	return render_template("dashboard.html", form=form, playlists=playlists)

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
			parseAudioData(filepath, file_ext) 
			flash(f'Upload successful: {filename}')
		return redirect(url_for('upload'))
	return render_template('upload.html', form=form)

@app.rout('/search', methods=['GET','POST'])
def search():
	
	return render_template('search.html', )

@app.route('/song/<id>', methods=['GET', 'POST'])
def songInfo(id = None):
	form=ReviewForm()
	form2=SelectPlaylistForm()
	if form.validate_on_submit():
		with connection:
			with connection.cursor() as cursor:
				cursor.execute(CREATE_SONG_REVIEWS)
				cursor.execute(SELECT_SONG_REVIEW, (id, session["user_id"]))
				review = cursor.fetchone()
				if review is None:
					cursor.execute(CREATE_SONG_REVIEWS)
					cursor.execute(INSERT_SONG_REVIEW, (session["user_id"], id, form.rating.data, form.review.data))
					rating = cursor.fetchone()[0]
				else: 
					cursor.execute(UPDATE_SONG_REVIEW, (form.rating.data, form.review.data, id, session["user_id"]))
					rating = cursor.fetchone()[0]
				return redirect(url_for('songInfo', id=id))
	
	if form2.validate_on_submit():
		print("*** Validated ***")
		with connection:
			with connection.cursor() as cursor:
				#print(f'**CHOICE***: {form2.playlists.data}')
				if form2.playlists.data != 0:
					cursor.execute(SELECT_PLAYLIST_SONG, (form2.playlists.data, id))
					song = cursor.fetchone()
					if song:
						flash("Song already in playlist")
					else:
						cursor.execute(INSERT_PLAYLIST_SONG, (form2.playlists.data, id))
						added_song = cursor.fetchone()
						cursor.execute(SELECT_ADDED_SONG_INFO, (form2.playlists.data, id))
						info = cursor.fetchone()
						print(info)
						flash(f"{info[0]} added to {info[1]}")
				return redirect(url_for('songInfo', id=id))
	with connection:
		with connection.cursor() as cursor:
			cursor.execute(SELECT_SONG_BY_ID, (id,))
			song = cursor.fetchone()
			cursor.execute(SELECT_REVIEWS_BY_SONGID, (id,))
			reviews = cursor.fetchall()
			cursor.execute(SELECT_GENRES_BY_SONG_ID, (id,))
			genres = cursor.fetchall()
			cursor.execute(SELECT_USER_PLAYLIST_IDS, (session['user_id'],))
			playlists = cursor.fetchall()
			if playlists:
				print(type(playlists[0][0]))
				form2.playlists.choices = playlists
				print(f'**Playlists***: {form2.playlists.choices}') 
			return render_template('song_review.html', form=form, form2=form2, song=song, genres=genres, reviews=reviews, playlists=playlists)
	return redirect(url_for('index'))

@app.route('/album/<id>', methods=['GET', 'POST'])
def albumInfo(id = None):
	form=ReviewForm()
	form2=SelectPlaylistForm()
	if form.validate_on_submit():
		with connection:
			with connection.cursor() as cursor:
				cursor.execute(CREATE_ALBUM_REVIEWS)
				cursor.execute(SELECT_ALBUM_REVIEW, (id, session["user_id"]))
				review = cursor.fetchone()
				if review is None:
					cursor.execute(INSERT_ALBUM_REVIEW, (session["user_id"], id, form.rating.data, form.review.data))
					rating = cursor.fetchone()[0]
				else: 
					cursor.execute(UPDATE_ALBUM_REVIEW, (form.rating.data, form.review.data, id, session["user_id"]))
					rating = cursor.fetchone()[0]
				print(rating)
				return redirect(url_for('albumInfo', id=id))
	
	if form2.playlists.data and form2.validate_on_submit():
		with connection:
			with connection.cursor() as cursor:
				if form2.playlists.data != 0:
					cursor.execute(CHECK_PLAYLIST_ALBUM, ( id,form2.playlists.data,))
					songs = cursor.fetchall()
					print(songs)
					if songs is None:
						flash("Album already in playlist")
					else:
						for s in songs:
							cursor.execute(INSERT_PLAYLIST_SONG, (form2.playlists.data, s[0]))
						
						cursor.execute(SELECT_PLAYLIST, (form2.playlists.data,))
						info = cursor.fetchone()
						flash(f"{len(songs)} song(s) added to {info[1]}")
				return redirect(url_for('albumInfo', id=id))

	with connection:
		with connection.cursor() as cursor:
			cursor.execute(SELECT_ALBUM_BY_ID, (id,))
			album = cursor.fetchone()
			#print(album)
			cursor.execute(SELECT_SONGS_BY_ALBUM_ID, (id,))
			songs = cursor.fetchall()
			cursor.execute(SELECT_REVIEWS_BY_ALBUMID, (id,))
			reviews = cursor.fetchall()
			cursor.execute(SELECT_GENRES_BY_ALBUM_ID, (id,))
			genres = cursor.fetchall()
			cursor.execute(SELECT_USER_PLAYLIST_IDS, (session['user_id'],))
			playlists = cursor.fetchall()
			if playlists:
				form2.playlists.choices = playlists
				print(playlists)
			#print(reviews)
			return render_template('album_review.html', id=id, form=form, form2=form2, songs=songs, genres=genres, album=album, reviews=reviews, playlists=playlists)
	return redirect(url_for('index'))

@app.route('/artist/<id>', methods=['GET', 'POST'])
def artistInfo(id = None):
	form = DescriptionForm()
	if form.validate_on_submit():
		with connection:
			with connection.cursor() as cursor:
				cursor.execute(UPDATE_ARTIST_DESC, (form.description.data, id))
				return redirect(url_for('artistInfo', id=id))
	with connection:
		with connection.cursor() as cursor:
			cursor.execute(SELECT_ARTIST_BY_ID, (id,))
			artist = cursor.fetchone()
			#print(album)
			cursor.execute(SELECT_ALBUMS_BY_ARTIST_ID, (id,))
			albums = cursor.fetchall()
			cursor.execute(SELECT_GENRES_BY_ARTIST_ID, (id,))
			genres = cursor.fetchall()
			return render_template('artist.html', form=form, artist=artist, genres=genres, albums=albums,)
	return redirect(url_for('index'))

@app.route('/genre/<id>', methods=['GET', 'POST'])
def genre(id = None):
	with connection:
		with connection.cursor() as cursor:
			cursor.execute(SELECT_GENRE_BY_ID, (id,))
			genre = cursor.fetchone()
			#print(album)
			cursor.execute(SELECT_ARTISTS_BY_GENRE_ID, (id,))
			artists = cursor.fetchall()
			cursor.execute(SELECT_SONGS_BY_GENRE_ID, (id,))
			songs = cursor.fetchall()
			return render_template('genre.html', genre=genre, artists=artists, songs=songs,)

	return redirect(url_for('index'))

@app.route('/user/<id>', methods=['GET', 'POST'])
def user(id = None):
	if session['user_id'] == id:
		return redirect(url_for('dashboard'))
	return redirect(url_for('index'))

@app.route('/playlist/<id>', methods=['GET', 'POST'])
def playlistInfo(id = None):
	form1 = PlaylistNameForm()
	form2 = DescriptionForm()
	if form1.validate_on_submit():
		with connection:
			with connection.cursor() as cursor:
				cursor.execute(UPDATE_PLAYLIST_NAME, (form1.name.data,id))
				cursor.fetchone()
				redirect(url_for('playlistInfo', id=id))
	if form2.validate_on_submit():
		with connection:
			with connection.cursor() as cursor:
				cursor.execute(UPDATE_PLAYLIST_DESC, (form2.description.data,id)) 
				cursor.fetchone()
				redirect(url_for('playlistInfo', id=id))
	with connection:
		with connection.cursor() as cursor:
			cursor.execute(SELECT_PLAYLIST, (id,))
			playlist = cursor.fetchone() 
			cursor.execute(SELECT_PLAYLIST_SONGS, (id,))
			songs = cursor.fetchall() 
			return render_template('playlist.html', form1=form1, form2=form2, playlist=playlist, songs=songs)
	return redirect(url_for('index'))

@app.route('/search', methods=['GET'])
def search():
    q = request.args.get("q")

    if q:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(SELECT_SONG_NAME, ("%" + q + "%",))
        result = cursor.fetchall()
    else:
        result = []

    if request.headers.get("HX-Request"):
        return render_template("search_results.html", result=result)

    return render_template("search.html", result=result)


if __name__ == '__main__':
	app.run(debug=True)