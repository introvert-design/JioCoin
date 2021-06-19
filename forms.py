from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField, PasswordField, validators


class RegistrationForm(FlaskForm):
    """
    Creates a registration form with user name, email, and password as input.
    """
    name = StringField('Full Name', [
        validators.DataRequired(),
        validators.Length(max=30, message=f'Name must not be longer than 30 characters.')
    ])
    email = StringField('Email Address', [
        validators.DataRequired(),
        validators.Length(max=50, message=f'Email address must not be longer than 50 characters.'),
        validators.Email()
    ])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.Length(min=8, max=20, message=f'Password must be between 8 and 20 characters long.'),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Confirm Password', [
        validators.DataRequired()
    ])
    submit = SubmitField('Create Account')


class LoginForm(FlaskForm):
    """
    Creates a login form with user email and password as input.
    """
    email = StringField('Email Address', [
        validators.DataRequired(),
        validators.Email()
    ])
    password = PasswordField('Password', [
        validators.DataRequired(),
    ])
    submit = SubmitField('Login')


class TransactionForm(FlaskForm):
    """
    Creates a form for transaction with recipient email and amount as inputs.
    """
    email = StringField('Recipient Email Address', [
        validators.DataRequired(),
        validators.Email()
    ])
    amount = FloatField('Amount', [
        validators.NumberRange(min=0.00, message='Invalid input. Enter a valid amount !'),
        validators.DataRequired(message='Invalid input. Enter a valid amount !')
    ])
    submit = SubmitField('Send')
