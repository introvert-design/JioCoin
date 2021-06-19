from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from flask_bootstrap import Bootstrap
from passlib.hash import sha256_crypt
from functools import wraps

from config import _mysql_user, _mysql_password, _secret_key
from sql_util import *
from forms import RegistrationForm, LoginForm, TransactionForm
from blockchain import Blockchain
from wallet import Wallet


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
            elif func.__name__ == 'transaction':
                flash('Please login to access the transaction page !', 'warning')
            else:
                flash('Unauthorized !', 'warning')
            return redirect(url_for('login'))
    return wrap


def login_user(email, users, url):
    user = users.get_one('email', email)

    session['logged_in'] = True
    session['name'] = user['name']
    session['email'] = user['email']
    session['public_key'] = user['public_key']
    session['has_wallet'] = user['has_wallet']
    session['url'] = url


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)

    users = Table("users", mysql,
                  ("name", "VARCHAR", 50),
                  ("email", "VARCHAR", 50),
                  ("password", "VARCHAR", 100),
                  ("public_key", "VARCHAR", 2048),
                  ("has_wallet", "BOOL", "")
                  )

    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data

        if users.is_new_user(email):
            password = sha256_crypt.encrypt(form.password.data)
            users.insert_data(name, email, password, 'NULL', 0)
            flash('User account created successfully. You are now logged in !', 'success')
            login_user(email, users, url_for('register'))
            return redirect(url_for('dashboard'))
        else:
            flash('User account already exists !', 'danger')
            return redirect(url_for('register'))

    return render_template('registration.html', form=form)


@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)

    if form.validate_on_submit():
        email = form.email.data
        input_password = form.password.data

        users = Table("users", mysql,
                      ("name", "VARCHAR", 50),
                      ("email", "VARCHAR", 50),
                      ("password", "VARCHAR", 100),
                      ("public_key", "VARCHAR", 2048),
                      ("has_wallet", "BOOL", "")
                      )

        user = users.get_one('email', email)
        if user is None:
            flash('User account not found. Create an account today !', 'warning')
            return redirect(url_for('login'))
        elif sha256_crypt.verify(input_password, user['password']):
            login_user(email, users, url_for('login'))
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


@app.route('/dashboard', methods=['GET'])
@is_loggedin
def dashboard():
    blockchain = Blockchain(session['email'], mysql)
    balance = blockchain.check_balance()

    return render_template('dashboard.html',
                           session=session,
                           balance=balance,
                           chain=blockchain.chain,
                           open_transactions=blockchain.open_transactions)


@app.route('/transaction', methods=['GET', 'POST'])
@is_loggedin
def transaction():
    session['url'] = url_for('transaction')
    form = TransactionForm(request.form)

    sender = session['email']

    blockchain = Blockchain(sender, mysql)
    balance = blockchain.check_balance()

    if form.validate_on_submit():
        recipient = form.email.data
        amount = form.amount.data

        users = Table("users", mysql,
                      ("name", "VARCHAR", 50),
                      ("email", "VARCHAR", 50),
                      ("password", "VARCHAR", 100),
                      ("public_key", "VARCHAR", 2048),
                      ("has_wallet", "BOOL", "")
                      )

        user = users.get_one('email', sender)
        if user['has_wallet'] == 0:
            flash('Wallet not found. Create wallet to send money!', 'danger')
        elif sender == recipient:
            flash('Invalid transaction !', 'danger')
        elif users.is_new_user(recipient):
            flash('Recipient user account does not exists !', 'danger')
        elif balance < amount:
            flash('Insufficient funds !', 'danger')
        else:
            wallet = Wallet()
            wallet.load_keys()
            signature = wallet.sign_transaction(sender, recipient, amount)
            if blockchain.add_transactions(sender, recipient, amount, signature):
                flash('Transaction successfully added for mining !', 'success')
            else:
                flash('Transaction failed. Signature could not be verified', 'danger')

        return redirect(url_for('transaction'))

    return render_template('transaction.html', form=form, balance=balance)


@app.route('/mine', methods=['POST'])
@is_loggedin
def mine():
    blockchain = Blockchain(session['email'], mysql)
    if blockchain.mine_block():
        flash('Block successfully mined', 'success')
    else:
        flash('Mining failed.', 'danger')
    return redirect(url_for('dashboard'))


@app.route('/new_wallet', methods=['GET'])
@is_loggedin
def new_wallet():
    if session['has_wallet'] == 1:
        return redirect(url_for('load_wallet'))

    return render_template('new_wallet.html')


@app.route('/create_wallet', methods=['GET', 'POST'])
@is_loggedin
def create_wallet():
    if session['has_wallet'] == 0:
        wallet = Wallet()
        wallet.create_keys()

        email = session['email']

        if wallet.save_keys(mysql, email):
            users = Table("users", mysql,
                          ("name", "VARCHAR", 50),
                          ("email", "VARCHAR", 50),
                          ("password", "VARCHAR", 100),
                          ("public_key", "VARCHAR", 2048),
                          ("has_wallet", "BOOL", "")
                          )
            login_user(email, users, url_for('create_wallet'))
            flash('Wallet created and successfully saved.', 'success')
            return redirect(url_for('load_wallet'))
        else:
            flash('Saving wallet failed !', 'danger')
            session['has_wallet'] = 0
            return redirect(url_for('new_wallet'))
    else:
        flash('Wallet already exists !', 'warning')
        return redirect(url_for('load_wallet'))


@app.route('/wallet', methods=['GET'])
@is_loggedin
def load_wallet():
    if session['has_wallet'] == 1:
        wallet = Wallet()
        if not wallet.load_keys():
            flash('Loading wallet failed !', 'danger')

        return render_template('wallet.html', wallet=wallet)
    else:
        flash('Wallet not found. Create wallet !', 'danger')
        return redirect(url_for('new_wallet'))


if __name__ == '__main__':
    app.run(host='localhost', port=8000, debug=True)
