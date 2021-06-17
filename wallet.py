from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15

from sql_util import Table


class Wallet:
    def __init__(self):
        self.private_key = None
        self.public_key = None

    def create_keys(self):
        key = RSA.generate(2048)
        self.public_key = key.publickey().export_key().decode('utf-8')
        self.private_key = key.export_key().decode('utf-8')

    def save_keys(self, mysql, email):
        if self.private_key is not None and self.public_key is not None:
            try:
                with open('private.pem', mode='wb') as file_out:
                    file_out.write(self.private_key.encode('utf-8'))
                users = Table("users", mysql, ("name", "VARCHAR", 50), ("email", "VARCHAR", 50),
                              ("password", "VARCHAR", 100), ("public_key", "VARCHAR", 2048), ("has_wallet", "BOOL", ""))
                users.update_table(('email', email), ('public_key', self.public_key.encode('utf-8')), ('has_wallet', 1))
                return True
            except (IOError, IndexError):
                return False

    def load_keys(self):
        try:
            with open('private.pem', mode='r') as file_in:
                key = RSA.import_key(file_in.read())
            self.private_key = key.export_key().decode('utf-8')
            self.public_key = key.publickey().export_key().decode('utf-8')
            return True
        except (IOError, IndexError):
            return False
    # def sign_transaction(self, transaction):
    #     hash_transaction = SHA256.new(transaction)
    #     signature = pkcs1_15.new(self.private_key).sign(hash_transaction)
    #
    # def verify_signature(self):
    #     key = RSA.import_key(open('public_key.der').read())
    #     h = SHA256.new(message)
    #     try:
    #         pkcs1_15.new(key).verify(h, signature)
    #     except (ValueError, TypeError):
    #         print("The signature is not valid.")
