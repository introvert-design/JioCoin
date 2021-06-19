from time import time
from json import dumps, loads

from transaction import Transaction
from block import Block
from helper import hash_block_data, ordered_dict
from sql_util import Table
from wallet import Wallet

MINING_REWARD = 10.0


class Blockchain:
    """
    Verifies and creates the chain of blocks and list of open transactions.
    """
    def __init__(self, host, mysql, difficulty=4):
        self.difficulty = difficulty
        self.host = host
        self.mysql = mysql
        self.chain = []
        self.open_transactions = []
        self.load_data()

    def __repr__(self):
        """
        Returns the list of blocks (blockchain) as a string.
        :return: string - blockchain
        """
        return str(self.chain)

    def calculate_balance(self):
        """
        Calculates the balance of the host or user account.
        :return: float - balance of the host or user account.
        """
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
        """
        Creates a new transaction, validates the signature of the transaction and
        adds the transaction to the open transactions list.
        :param sender: The sender of the transaction.
        :param recipient: The recipient of the transaction.
        :param amount: The amount of the transaction.
        :param signature: The signature of the transaction.
        :return: boolean - True: if the transaction is successfully added to the open transactions list.
                           False: if the validation of the transaction signature fails.
        """
        transaction = Transaction(sender, recipient, amount, signature)
        if Wallet.verify_signature(transaction.__dict__, self.mysql):
            self.open_transactions.append(transaction.__dict__)
            self.save_data()
            return True
        else:
            return False

    def mine_block(self):
        """
        Verifies the transactions in the open transactions list, creates a new block
        and adds the block to the blockchain.
        :return: None.
        """
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

    def is_valid(self):
        """
        Checks the validity of the blocks in the blockchain.
        :return: boolean - True: if all the blocks in the blockchain are valid.
                           False: if any of the block in the blockchain is corrupted.
        """
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
        """
        Loads the blockchain and open transactions from the MySQL database.
        :return: None.
        """
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
        """
        Saves the blockchain and open transactions to the MySQL database.
        :return: None.
        """
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
        """
        Deletes a transaction with invalid signature from the open transactions list and from the open_transactions
        table in the MySQL database.
        :param transaction: The corrupted transaction with invalid signature.
        :return: None.
        """
        self.open_transactions.remove(transaction)
        open_transactions_db = Table("open_transactions", self.mysql,
                                     ("sender", "VARCHAR", 50),
                                     ("recipient", "VARCHAR", 50),
                                     ("amount", "FLOAT", 20),
                                     ("signature", "VARCHAR", 2048))
        open_transactions_db.delete_one("signature", transaction['signature'])
