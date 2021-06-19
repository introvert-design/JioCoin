from time import time
from json import dumps, loads

from transaction import Transaction
from block import Block
from helper import hash_block_data, ordered_dict
from sql_util import Table
from wallet import Wallet

MINING_REWARD = 10.0


class Blockchain:
    def __init__(self, host, mysql, difficulty=4):
        self.difficulty = difficulty
        self.host = host
        self.mysql = mysql
        self.chain = []
        self.open_transactions = []
        self.load_data()

    def __repr__(self):
        return str(self.chain)

    def check_balance(self):
        balance = 0
        for block in self.chain:
            for transaction in (block.__dict__['transactions']):
                if transaction['recipient'] == self.host:
                    balance += transaction['amount']
                elif transaction['sender'] == self.host:
                    balance -= transaction['amount']
                else:
                    continue

        for transaction in self.open_transactions:
            if transaction['sender'] == self.host:
                balance -= transaction['amount']
            else:
                continue
        return balance

    def add_transactions(self, sender, recipient, amount, signature):
        transaction = Transaction(sender, recipient, amount, signature)
        if Wallet.verify_signature(transaction.__dict__, self.mysql):
            self.open_transactions.append(transaction.__dict__)
            self.save_data()
            return True
        else:
            return False

    def mine_block(self):
        if len(self.chain) > 0:
            if not self.is_valid():
                return False
        try:
            previous_hash = self.chain[-1].__dict__['hash']
        except IndexError:
            previous_hash = '0' * 62 + 'x0'
        for transaction in self.open_transactions:
            if not Wallet.verify_signature(transaction, self.mysql):
                self.delete_invalid_open_transaction(transaction)
        self.open_transactions.append(Transaction('Jiocoin', self.host, MINING_REWARD, '').__dict__)
        transactions = ordered_dict(self.open_transactions[:])
        block = Block(len(self.chain) + 1, previous_hash, str(time()), transactions)
        while not hash_block_data(block)[:self.difficulty] == '0' * self.difficulty:
            block.nonce += 1
            block.timestamp = str(time())
        else:
            block.hash = hash_block_data(block)
            self.chain.append(block)
            self.open_transactions = []
            self.save_data()
            return True

    def is_valid(self):
        for count, block in enumerate(self.chain):
            if count == 0:
                if hash_block_data(block)[:self.difficulty] != '0' * self.difficulty:
                    return False
                else:
                    continue
            if block.previous_hash != hash_block_data(self.chain[count - 1]) or \
                    hash_block_data(block)[:self.difficulty] != '0' * self.difficulty:
                return False
        return True

    def load_data(self):
        blockchain = []
        blockchain_db = Table("blockchain", self.mysql,
                              ("id", "INT", 100),
                              ("hash", "VARCHAR", 100),
                              ("previous_hash", "VARCHAR", 100),
                              ("nonce", "INT", 10),
                              ("timestamp", "VARCHAR", 20),
                              ("transactions", "JSON", ""))
        for row in blockchain_db.get_all_data():
            block = Block(row['id'],
                          row['previous_hash'],
                          row['timestamp'],
                          loads(row['transactions']),
                          row['hash'],
                          row['nonce'])
            blockchain.append(block)
            self.chain = blockchain

        transactions = []
        open_transactions_db = Table("open_transactions", self.mysql,
                                     ("sender", "VARCHAR", 50),
                                     ("recipient", "VARCHAR", 50),
                                     ("amount", "FLOAT", 20),
                                     ("signature", "VARCHAR", 2048))
        for tnx in open_transactions_db.get_all_data():
            transaction = Transaction(tnx['sender'],
                                      tnx['recipient'],
                                      tnx['amount'],
                                      tnx['signature'])
            transactions.append(transaction.__dict__)
        self.open_transactions = transactions

    def save_data(self):
        blockchain_db = Table("blockchain", self.mysql,
                              ("id", "INT", 100),
                              ("hash", "VARCHAR", 100),
                              ("previous_hash", "VARCHAR", 100),
                              ("nonce", "INT", 10),
                              ("timestamp", "VARCHAR", 20),
                              ("transactions", "JSON", ""))
        blockchain_db.delete_all_data()
        for block in self.chain:
            blockchain_db.insert_data(block.index,
                                      block.hash,
                                      block.previous_hash,
                                      block.nonce,
                                      block.timestamp,
                                      dumps(block.transactions))

        open_transactions_db = Table("open_transactions", self.mysql,
                                     ("sender", "VARCHAR", 50),
                                     ("recipient", "VARCHAR", 50),
                                     ("amount", "FLOAT", 20),
                                     ("signature", "VARCHAR", 2048))
        open_transactions_db.delete_all_data()
        for transaction in self.open_transactions:
            open_transactions_db.insert_data(transaction['sender'],
                                             transaction['recipient'],
                                             transaction['amount'],
                                             transaction['signature'])

    def delete_invalid_open_transaction(self, transaction):
        self.open_transactions.remove(transaction)
        open_transactions_db = Table("open_transactions", self.mysql,
                                     ("sender", "VARCHAR", 50),
                                     ("recipient", "VARCHAR", 50),
                                     ("amount", "FLOAT", 20),
                                     ("signature", "VARCHAR", 2048))
        open_transactions_db.delete_one("signature", transaction['signature'])
