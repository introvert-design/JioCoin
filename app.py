from flask import Flask, render_template
from flask_mysqldb import MySQL
from config import _mysql_user, _mysql_password

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = _mysql_user
app.config['MYSQL_PASSWORD'] = _mysql_password
app.config['MYSQL_DB'] = 'jiocoin'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)


@app.route('/')
def home():
    return render_template('index.html')


if __name__ == '__main__':
    app.secret_key = 'xyz123'
    app.run(host='localhost', port=8000, debug=True)
