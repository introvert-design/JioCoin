from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
from flask_bootstrap import Bootstrap
from passlib.hash import bcrypt
from functools import wraps
import mysql.connector as sql

from config import _mysql_user, _mysql_password, _secret_key
from sql_util import Table, nodes
from forms import RegistrationForm, LoginForm, TransactionForm
from blockchain import Blockchain
from wallet import Wallet


app = Flask(__name__)

app.config['SECRET_KEY'] = _secret_key

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = _mysql_user
app.config['MYSQL_PASSWORD'] = _mysql_password
app.config['MYSQL_DB'] = 'jiocoin_users'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['BOOTSTRAP_SERVE_LOCAL'] = True

Bootstrap(app)
mysql = MySQL(app)


def get_blockchain(email):
    """
    Creates the instance of Blockchain class.
    :param email: The email of the user.
    :return: Blockchain object
    """
    conn = sql.connect(
        host='localhost',
        user=_mysql_user,
        password=_mysql_password,
        database='jiocoin_' + str(port)
    )
    blockchain = Blockchain(email, mysql, conn)
    return blockchain


def get_balance(email):
    """
    Gets the balance of the user account from the Blockchain class.
    :param email: The email of the user.
    :return: Balance of the user account.
    """
    blockchain = get_blockchain(email)
    balance = blockchain.calculate_balance()
    return balance


def broadcast_block_helper(block, blockchain, peer_chain_index):
    """
    Helper function for the broadcast_block function
    :param block: The block to be added.
    :param blockchain: The peer node blockchain copy.
    :param peer_chain_index: The index of the last block in the peer chain copy.
    :return: Adds the block to the peer's chain if the chain is in sync
    otherwise respond with appropriate message.
    """

    if block['index'] == peer_chain_index + 1:
        if blockchain.add_block(block):
            return '', 200
        else:
            response = {'msg': 'Block validation failed !'}
            return jsonify(response), 409
    else:
        response = {'msg': 'Blockchains not in sync !'}
        return jsonify(response), 409


def is_loggedin(func):
    """
    Checks whether the user is logged in or not.
    :param func: The function which is wrapped.
    :return: Returns the function if the user is logged in, otherwise redirected to the login page.
    """
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
    """
    Assigns the session values from the database when the user is logged in.
    :param email: The email of the user to identify the related data from the database.
    :param users: The instance of the table class to access the user data.
    :param url: The url of the page from where the user was redirected.
    :return: None.
    """
    user = users.get_one('email', email)

    session['logged_in'] = True
    session['name'] = user['name']
    session['email'] = user['email']
    session['public_key'] = user['public_key']
    session['has_wallet'] = user['has_wallet']
    session['db_created'] = user['db_created']
    session['has_conflict'] = False
    session['url'] = url


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Renders the registration page and validates the input data.
    Saves the user data to the database and the user is logged in.
    :return: Returns the registration page. If the user is successfully signed up, the dashboard page is returned
    otherwise redirected to the registration form.
    """
    form = RegistrationForm(request.form)

    users = Table("users", mysql,
                  ("email", "VARCHAR", 50, "UNIQUE"),
                  ("name", "VARCHAR", 50, ""),
                  ("node", "VARCHAR", 80, "UNIQUE"),
                  ("password", "VARCHAR", 100, ""),
                  ("public_key", "VARCHAR", 2048, ""),
                  ("has_wallet", "BOOL", "", ""),
                  ("db_created", "BOOL", "", "")
                  )

    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        node = form.node.data

        if users.is_new_user(email):
            password = bcrypt.hash(form.password.data)
            is_db_created = Table.create_db("jiocoin_" + str(port))
            try:
                users.insert_data(email, name, node, password, 'NULL', 0, is_db_created)
            except Exception as e:
                if e.args[0] == 1062:
                    flash('User node already exists !', 'danger')
                    return redirect(url_for('register'))
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
    """
    Renders the login page and validates the input data.
    Verifies the password and the user is logged in.
    :return: Returns the login page. If the user is successfully logged in, the dashboard page is returned
    otherwise redirected to the login form.
    """
    form = LoginForm(request.form)

    if form.validate_on_submit():
        email = form.email.data
        input_password = form.password.data

        users = Table("users", mysql,
                      ("email", "VARCHAR", 50, "UNIQUE"),
                      ("name", "VARCHAR", 50, ""),
                      ("node", "VARCHAR", 80, "UNIQUE"),
                      ("password", "VARCHAR", 100, ""),
                      ("public_key", "VARCHAR", 2048, ""),
                      ("has_wallet", "BOOL", "", ""),
                      ("db_created", "BOOL", "", "")
                      )

        user = users.get_one('email', email)
        if user is None:
            flash('User account not found. Create an account today !', 'warning')
            return redirect(url_for('login'))
        elif bcrypt.verify(input_password, user['password']):
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
    """
    Logs out the user and clears out the session.
    :return: Redirected to the login page.
    """
    session.clear()
    flash('User successfully logged out !', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard', methods=['GET'])
@is_loggedin
def dashboard():
    """
    Renders the dashboard with information from the blockchain and open transactions.
    :return: Returns the dashboard page.
    """
    email = session['email']
    blockchain = get_blockchain(email)
    balance = get_balance(email)

    return render_template('dashboard.html',
                           session=session,
                           balance=balance,
                           chain=blockchain.chain,
                           open_transactions=blockchain.open_transactions)


@app.route('/transaction', methods=['GET', 'POST'])
@is_loggedin
def transaction():
    """
    Renders the transaction page and validates the transaction data. Calls the function to add
    the transaction to the open transactions list.
    :return: Returns the transaction page.
    """
    session['url'] = url_for('transaction')
    form = TransactionForm(request.form)

    sender = session['email']

    blockchain = get_blockchain(sender)
    balance = get_balance(sender)

    if form.validate_on_submit():
        recipient = form.email.data
        amount = form.amount.data

        users = Table("users", mysql,
                      ("email", "VARCHAR", 50, "UNIQUE"),
                      ("name", "VARCHAR", 50, ""),
                      ("node", "VARCHAR", 80, "UNIQUE"),
                      ("password", "VARCHAR", 100, ""),
                      ("public_key", "VARCHAR", 2048, ""),
                      ("has_wallet", "BOOL", "", ""),
                      ("db_created", "BOOL", "", "")
                      )

        if session['has_conflict']:
            flash('Blockchain out of sync. Resolve conflict !', 'danger')
        elif session['has_wallet'] == 0:
            flash('Wallet not found. Create wallet to send money!', 'danger')
        elif sender == recipient:
            flash('Invalid transaction !', 'danger')
        elif users.is_new_user(recipient):
            flash('Recipient user account does not exists !', 'danger')
        elif balance < amount:
            flash('Insufficient funds !', 'danger')
        else:
            wallet = Wallet()
            wallet.load_keys(port)
            signature = wallet.sign_transaction(sender, recipient, amount)
            node_list = nodes(mysql, sender)
            if blockchain.add_transactions(sender, recipient, amount, signature, node_list, True):
                flash('Transaction successfully added for mining !', 'success')
            else:
                flash('Transaction failed. Signature could not be verified', 'danger')

        return redirect(url_for('transaction'))

    return render_template('transaction.html', form=form, balance=balance)


@app.route('/mine', methods=['POST'])
@is_loggedin
def mine():
    """
    Calls the mining function.
    :return: Redirect to the dashboard page.
    """
    if not session['has_conflict']:
        email = session['email']
        blockchain = get_blockchain(email)
        node_list = nodes(mysql, email)
        session['has_conflict'] = blockchain.mine_block(node_list)
        return '''
                    <div class="alert alert-success">
                        <button type="button" class="close" data-dismiss="alert">&times;</button>
                        <h5>New block mined successfully!<h5>      
                    </div>
                '''

    return '''
                <div class="alert alert-danger">
                    <button type="button" class="close" data-dismiss="alert">&times;</button>
                    <h5>Mining failed ! Blockchain out of sync. Need resolving.<h5>      
                </div>
            '''


@app.route('/broadcast-block', methods=['POST'])
def broadcast_block():
    """
    Broadcasts the newly mined block to the peer nodes.
    :return: Response to the request.
    """
    values = request.get_json()

    if not values:
        response = {'msg': 'No data found !'}
        return jsonify(response), 400

    reqs = ['block', 'node']
    if not all(req in values for req in reqs):
        response = {'msg': 'Data missing !'}
        return jsonify(response), 400

    users = Table("users", mysql,
                  ("email", "VARCHAR", 50, "UNIQUE"),
                  ("name", "VARCHAR", 50, ""),
                  ("node", "VARCHAR", 80, "UNIQUE"),
                  ("password", "VARCHAR", 100, ""),
                  ("public_key", "VARCHAR", 2048, ""),
                  ("has_wallet", "BOOL", "", ""),
                  ("db_created", "BOOL", "", "")
                  )

    user = users.get_one('node', values['node'])

    blockchain = get_blockchain(user['email'])

    block = values['block']

    try:
        return broadcast_block_helper(block, blockchain, blockchain.chain[-1].index)
    except IndexError:
        return broadcast_block_helper(block, blockchain, 0)


@app.route('/broadcast-tnx', methods=['POST'])
def broadcast_tnx():
    """
    Broadcasts the new transactions to the peer nodes.
    :return: Response to the request.
    """

    values = request.get_json()
    if not values:
        response = {'msg': 'No data found !'}
        return jsonify(response), 400

    reqs = ['transaction', 'node']
    if not all(req in values for req in reqs):
        response = {'msg': 'Data missing !'}
        return jsonify(response), 400

    users = Table("users", mysql,
                  ("email", "VARCHAR", 50, "UNIQUE"),
                  ("name", "VARCHAR", 50, ""),
                  ("node", "VARCHAR", 80, "UNIQUE"),
                  ("password", "VARCHAR", 100, ""),
                  ("public_key", "VARCHAR", 2048, ""),
                  ("has_wallet", "BOOL", "", ""),
                  ("db_created", "BOOL", "", "")
                  )

    user = users.get_one('node', values['node'])

    blockchain = get_blockchain(user['email'])

    tnx = values['transaction']
    success = blockchain.add_transactions(tnx['sender'],
                                          tnx['recipient'],
                                          tnx['amount'],
                                          tnx['signature'])
    if success:
        return '', 200
    else:
        response = {'msg': 'Transaction cannot be added !'}
        return jsonify(response), 400


@app.route('/chain', methods=['GET'])
def get_chain():
    """
    Gets the blockchain of the peer nodes.
    :return: Response to the request.
    """
    values = request.get_json()

    if not values:
        response = {'msg': 'No data found !'}
        return jsonify(response), 400

    if 'node' not in values:
        response = {'msg': 'Data missing !'}
        return jsonify(response), 400

    users = Table("users", mysql,
                  ("email", "VARCHAR", 50, "UNIQUE"),
                  ("name", "VARCHAR", 50, ""),
                  ("node", "VARCHAR", 80, "UNIQUE"),
                  ("password", "VARCHAR", 100, ""),
                  ("public_key", "VARCHAR", 2048, ""),
                  ("has_wallet", "BOOL", "", ""),
                  ("db_created", "BOOL", "", "")
                  )

    user = users.get_one('node', values['node'])

    blockchain = get_blockchain(user['email'])
    chain = blockchain.chain
    dict_chain = [block.__dict__.copy() for block in chain]
    return jsonify(dict_chain), 200


@app.route('/resolve-conflicts', methods=['POST'])
@is_loggedin
def resolve_conflicts():
    """
    Resolves the conflict between the blockchain copies of the peer nodes.
    :return: Returns the dashboard. If the local blockchain is shorter,
    local copy is updated otherwise local copy is kept unchanged.
    """
    email = session['email']
    blockchain = get_blockchain(email)
    node_list = nodes(mysql, email)
    if blockchain.resolve(node_list):
        session['has_conflict'] = False
        return '''
                    <div class="alert alert-success">
                        <button type="button" class="close" data-dismiss="alert">&times;</button>
                        <h5>Blockchain updated !<h5>      
                    </div>
                '''
    session['has_conflict'] = False
    return '''
                <div class="alert alert-success">
                    <button type="button" class="close" data-dismiss="alert">&times;</button>
                    <h5>Blockchain is up-to-date. No changes required !<h5>      
                </div>
            '''


@app.route('/new_wallet', methods=['GET'])
@is_loggedin
def new_wallet():
    """
    Renders the new wallet page if user does not have a wallet.
    :return: Returns the new wallet page if the user does not have a wallet,
    otherwise redirects user to the wallet page.
    """
    if session['has_wallet'] == 1:
        return redirect(url_for('load_wallet'))

    return render_template('new_wallet.html')


@app.route('/create_wallet', methods=['GET', 'POST'])
@is_loggedin
def create_wallet():
    """
    Calls the function to create the keys, and to save them to the file.
    :return: Redirected to the wallet page if the keys are successfully created,
    otherwise user is redirected to the new wallet page.
    """
    if session['has_wallet'] == 0:
        wallet = Wallet()
        public_key = wallet.create_keys()

        email = session['email']

        if wallet.save_keys(mysql, email, port):
            session['has_wallet'] = 1
            session['url'] = url_for('create_wallet')
            session['public_key'] = public_key
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
    """
    Renders the wallet page and calls the function to load the keys from the file.
    :return: Returns the wallet page if the keys are successfully loaded, otherwise renders the new wallet page.
    """
    if session['has_wallet'] == 1:
        wallet = Wallet()
        if not wallet.load_keys(port):
            flash('Loading wallet failed !', 'danger')

        return render_template('wallet.html', wallet=wallet)
    else:
        flash('Wallet not found. Create wallet !', 'danger')
        return redirect(url_for('new_wallet'))


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=5000)
    port = parser.parse_args().port
    app.run(host='localhost', port=port, debug=True)
