from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from flask_bootstrap import Bootstrap
from passlib.hash import sha256_crypt
from functools import wraps

from config import _mysql_user, _mysql_password, _secret_key
from sql_util import *
from forms import RegistrationForm, LoginForm

app = Flask(__name__)

app.config['SECRET_KEY'] = _secret_key

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = _mysql_user
app.config['MYSQL_PASSWORD'] = _mysql_password
app.config['MYSQL_DB'] = 'jiocoin'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

Bootstrap(app)
mysql = MySQL(app)


def is_loggedin(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return func(*args, **kwargs)
        else:
            if func.__name__ == 'dashboard':
                flash('Please login to access the dashboard !', 'warning')
            return redirect(url_for('login'))
    return wrap


def login_user(email, users):
    user = users.get_one('email', email)

    session['logged_in'] = True
    session['name'] = user['name']
    session['email'] = user['email']


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    users = Table("users", ("name", 50), ("email", 50), ("password", 100))

    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data

        if users.is_new_user(email):
            password = sha256_crypt.encrypt(form.password.data)
            users.insert_data(name, email, password)
            flash('User account created successfully. You are now logged in !', 'success')
            login_user(email, users)
            return redirect(url_for('dashboard'))
        else:
            flash('User account already exists !', 'danger')
            return redirect(url_for('register'))

    return render_template('registration.html', form=form)


@app.route('/dashboard')
@is_loggedin
def dashboard():
    return render_template('dashboard.html', session=session)


@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)

    if form.validate_on_submit():
        email = form.email.data
        input_password = form.password.data

        users = Table("users", ("name", 50), ("email", 50), ("password", 100))
        user = users.get_one('email', email)
        if user is None:
            flash('User account not found. Create an account today !', 'warning')
            return redirect(url_for('login'))
        elif sha256_crypt.verify(input_password, user['password']):
            login_user(email, users)
            flash('User successfully logged in !', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid password. Try again !', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html', form=form)


@app.route('/logout')
@is_loggedin
def logout():
    session.clear()
    flash('User successfully logged out !', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(host='localhost', port=8000, debug=True)
