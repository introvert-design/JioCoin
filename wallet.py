from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import pss
import binascii

from sql_util import Table


class Wallet:
    """
    Creates, saves and loads RSA private-public key pair.
    Creates the transaction signature and validates the signature.
    """
    def __init__(self):
        self.private_key = None
        self.public_key = None

    def create_keys(self):
        """
        Creates a new RSA private-public key pair.
        :return: None.
        """
        key = RSA.generate(2048)
        self.public_key = key.publickey().export_key().decode('utf-8')
        self.private_key = key.export_key().decode('utf-8')

    def save_keys(self, mysql, email):
        """
        Saves the private key to a separate file and adds public key to the users table in mysql database.
        :param mysql: Bound MySQL connection object to connect to the server to update the users table.
        :param email: The email of the user used to identify the row to be modified.
        :return: boolean - True: if saves the key pair successfully.
                           False: if fails to save the key.
        """
        if self.private_key is not None and self.public_key is not None:
            try:
                with open('private.pem', mode='wb') as file_out:
                    file_out.write(self.private_key.encode('utf-8'))
                users = Table("users", mysql,
                              ("name", "VARCHAR", 50),
                              ("email", "VARCHAR", 50),
                              ("password", "VARCHAR", 100),
                              ("public_key", "VARCHAR", 2048),
                              ("has_wallet", "BOOL", ""))
                users.update_table(('email', email), ('public_key', self.public_key), ('has_wallet', 1))
                return True
            except (IOError, IndexError):
                return False

    def load_keys(self):
        """
        Loads the private key from the local file and generates the public key from the private key.
        :return: boolean - True: if loads the key pair successfully.
                           False: if fails to load the key.
        """
        try:
            with open('private.pem', mode='r') as file_in:
                key = RSA.import_key(file_in.read())
            self.private_key = key.export_key().decode('utf-8')
            self.public_key = key.publickey().export_key().decode('utf-8')
            return True
        except (IOError, IndexError):
            return False

    def sign_transaction(self, sender, recipient, amount):
        """
        Creates the signature of a transaction.
        :param sender: The sender of the transaction.
        :param recipient: The recipient of the transaction.
        :param amount: The amount of the transaction.
        :return: string - the signature decoded as a hexadecimal string.
        """
        hash_transaction = SHA256.new((str(sender) + str(recipient) + str(amount)).encode('utf-8'))
        signature = pss.new(RSA.import_key(self.private_key.encode('utf-8'))).sign(hash_transaction)
        return binascii.hexlify(signature).decode('ascii')

    @staticmethod
    def verify_signature(transaction, mysql):
        """
        Checks if the signature over a transaction is valid.
        :param transaction: The transaction whose signature has to be validated.
        :param mysql: Bound MySQL connection object to connect to the server to access the public key of the sender.
        :return: boolean - True: if the signature is valid.
                           False: if the signature is not valid.
        """
        users = Table("users", mysql,
                      ("name", "VARCHAR", 50),
                      ("email", "VARCHAR", 50),
                      ("password", "VARCHAR", 100),
                      ("public_key", "VARCHAR", 2048),
                      ("has_wallet", "BOOL", ""))
        user = users.get_one("email", transaction['sender'])
        public_key = user['public_key']
        hash_transaction = SHA256.new((str(transaction['sender']) +
                                       str(transaction['recipient']) +
                                       str(transaction['amount']))
                                      .encode('utf-8'))
        verifier = pss.new(RSA.import_key(public_key.encode('utf-8')))
        try:
            verifier.verify(hash_transaction, binascii.unhexlify(transaction['signature']))
            return True
        except (ValueError, TypeError):
            return False
