from functools import wraps
from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
import secrets
import json
import paho.mqtt.client as mqtt
import requests
app = Flask(__name__)
from flask import jsonify

myarticles = Articles()

#config mysql

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'yassine'
app.config['MYSQL_PASSWORD'] = 'yassine123'
app.config['MYSQL_DB'] = 'registerdb'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MYSQL
mysql = MySQL(app)

# ThingSpeak API configuration
thingspeak_api_url = "https://api.thingspeak.com/channels/2234598/feeds.json?api_key=3E4FN9GKKNWYIHB1&results=2"

# # MQTT configuration
# mqtt_broker = "mqtt3.thingspeak.com"
# mqtt_port = 1883
# client_id = "FA4zCh0gExASCCczPCs6IAs"
# mqtt_username = "FA4zCh0gExASCCczPCs6IAs"
# mqtt_password = "mM43aGbvv2h7c2v3t5JVI8Pa"
# channel_id = "2234598"
# mqtt_topic = "channels/" + channel_id + "/subscribe"

@app.route("/")
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/history')
def articles():
    return render_template('history.html')


class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


@app.route('/register', methods = ['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.hash(str(form.password.data))

        app.logger.info("Register success")
        # Create cursor
        cur = mysql.connection.cursor()

        # Execute query
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()
        flash('You are now registered and can log in', 'success')
        #return redirect(url_for('index'))
        return redirect(url_for('login'))
    else:
        app.logger.info('Register failed')
    return render_template('register.html', form=form)

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username
                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid Password'
                return render_template('login.html', error=error)
            # Close connection
            cur.close()

        else:
            error = 'Username not found'
            return render_template('login.html', error=error)
    return render_template('login.html')

def is_logged_in(f):
    @wraps(f)
    def wrap (*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('unauthorized , please login', 'danger')
            return redirect(url_for('login'))
    return wrap



@app.route('/dashboard')
@is_logged_in
def dashboard():
    try:
        response = requests.get(thingspeak_api_url)
        data = response.json()
        if data["feeds"]:
            temperature = data["feeds"][0]["field1"]
            humidity = data["feeds"][0]["field2"] 
        else:
            temperature = "N/A"
    except Exception as e:
        print("error", e)
        temperature = "N/A"    
    return render_template("dashboard.html", temperature=temperature, humidity=humidity)

@app.route('/update_data')
@is_logged_in
def update_data():
    try:
        response = requests.get(thingspeak_api_url)
        data = response.json()
        if data["feeds"]:
            temperature = data["feeds"][0]["field1"]
            humidity = data["feeds"][0]["field2"]
        else:
            temperature = "N/A"
            humidity = "N/A"
    except Exception as e:
        print("error", e)
        temperature = "N/A"
        humidity = "N/A"

    return jsonify(temperature=temperature, humidity=humidity)

@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

@app.route('/profile')
@is_logged_in
def profile():
    return render_template('profile.html')



if __name__ == '__main__':
    app.secret_key = secrets.token_hex(16)
    app.debug = "true"
    app.run()


