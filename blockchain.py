from time import time
from json import dumps, loads
import requests

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

    def __init__(self, host, mysql, conn, difficulty=4):
        self.difficulty = difficulty
        self.host = host
        self.mysql = mysql
        self.conn = conn
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

    def add_transactions(self, sender, recipient, amount, signature, node_list=None, broadcast=False):
        """
        Creates a new transaction, validates the signature of the transaction and
        adds the transaction to the open transactions list.
        :param sender: The sender of the transaction.
        :param recipient: The recipient of the transaction.
        :param amount: The amount of the transaction.
        :param signature: The signature of the transaction.
        :param node_list: The list of nodes to which the transaction should broadcast.
        :param broadcast: Determines whether to broadcast or not.
        :return: boolean - True: if the transaction is successfully added to the open transactions list.
                           False: if the validation of the transaction signature fails.
        """
        transaction = Transaction(len(self.open_transactions) + 1, sender, recipient, amount, signature)
        if Wallet.verify_signature(transaction.__dict__, self.mysql):
            self.open_transactions.append(transaction.__dict__)
            self.save_data()
            if broadcast:
                tnx_dict = transaction.__dict__.copy()
                for node in node_list:
                    url = f'{node}/broadcast-tnx'
                    try:
                        response = requests.post(url, json={'transaction': tnx_dict, 'node': node})
                        if response.status_code == 400 or response.status_code == 500:
                            return False
                    except requests.exceptions.ConnectionError:
                        continue
            return True
        return False

    def mine_block(self, node_list):
        """
        Verifies the transactions in the open transactions list, creates a new block
        and adds the block to the blockchain.
        :param node_list: The list of nodes to which the transaction should broadcast.
        :return: None.
        """
        try:
            previous_hash = self.chain[-1].__dict__['hash']
        except IndexError:
            previous_hash = '0' * 62 + 'x0'
        for transaction in self.open_transactions:
            if not Wallet.verify_signature(transaction, self.mysql):
                self.delete_invalid_open_transaction(transaction)
        self.open_transactions.append(Transaction(len(self.open_transactions) + 1,
                                                  'Jiocoin',
                                                  self.host,
                                                  MINING_REWARD,
                                                  '').__dict__)
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
            block = block.__dict__.copy()
            block['transactions'] = transactions
            count = 0
            for node in node_list:
                url = f'{node}/broadcast-block'
                try:
                    response = requests.post(url, json={'block': block, 'node': node})
                    if response.status_code == 409:
                        count += 1
                except requests.exceptions.ConnectionError:
                    continue
            if count >= len(node_list)/2:
                return True

        return False

    def add_block(self, block):
        """
        Add a block which was received via broadcasting to the local blockchain.
        :param block: The block to be added to the local blockchain.
        :return boolean - True: if the block is successfully added to the local chain.
                          False: if the block fails.
        """
        block_obj = Block(block['index'],
                          block['previous_hash'],
                          block['timestamp'],
                          block['transactions'],
                          block['hash'],
                          block['nonce'])
        if block['index'] == 1:
            if not self.is_valid_block(block_obj):
                return False
        else:
            if not self.is_valid_block(block_obj, self.chain[- 1]):
                return False
        self.chain.append(block_obj)
        for in_tnx in block['transactions']:
            for tnx in self.open_transactions:
                if tnx['index'] == in_tnx['index'] \
                        and tnx['sender'] == in_tnx['sender'] \
                        and tnx['recipient'] == in_tnx['recipient'] \
                        and tnx['amount'] == in_tnx['amount'] \
                        and tnx['signature'] == in_tnx['signature']:
                    try:
                        self.open_transactions.remove(tnx)
                    except ValueError:
                        print('Item was already removed')
        self.save_data()
        return True

    def resolve(self, node_list):
        """
        Checks all peer nodes' blockchains and replaces the local one with longer valid ones.
        """
        updated = False
        for node in node_list:
            url = f'{node}/chain'
            try:
                response = requests.get(url, json={'node': node})
                node_chain = response.json()

                node_chain = [Block(block['index'],
                                    block['previous_hash'],
                                    block['timestamp'],
                                    ordered_dict(block['transactions']),
                                    block['hash'],
                                    block['nonce'])
                              for block in node_chain]
                node_chain_length = len(node_chain)
                local_chain_length = len(self.chain)
                if node_chain_length > local_chain_length and self.is_valid_chain(node_chain, False):
                    self.chain = node_chain
                    updated = True
            except requests.exceptions.ConnectionError:
                continue

        if updated:
            self.open_transactions = []
            self.save_data()
        return updated

    def is_valid_chain(self, peer_chain=None, validate_local=True):
        """
        Checks the validity of the blockchain.
        :return: boolean - True: if all the blocks in the blockchain are valid.
                 False: if any of the block in the blockchain is corrupted.
        """
        valid_list = []
        if validate_local:
            chain_to_be_validated = self.chain
        else:
            chain_to_be_validated = peer_chain

        for count, block in enumerate(chain_to_be_validated):
            if count == 0:
                valid_list.append(self.is_valid_block(block))
            else:
                valid_list.append(self.is_valid_block(block, chain_to_be_validated[count - 1]))

        if all(valid_list):
            return True
        return False

    def is_valid_block(self, block, prev_block=None):
        """
        Checks the validity of a block in the blockchain.
        :return: boolean - True: if a block in the blockchain is valid.
                           False: if a block in the blockchain is corrupted.
        """
        if prev_block is None:
            if hash_block_data(block)[:self.difficulty] != '0' * self.difficulty:
                return False
        elif block.previous_hash != hash_block_data(prev_block) or \
                hash_block_data(block)[:self.difficulty] != '0' * self.difficulty:
            return False
        return True

    def load_data(self):
        """
        Loads the blockchain and open transactions from the MySQL database.
        :return: None.
        """
        blockchain = []
        blockchain_db = Table("blockchain", self.conn,
                              ("id", "INT", 100, ""),
                              ("hash", "VARCHAR", 100, "UNIQUE"),
                              ("previous_hash", "VARCHAR", 100, "UNIQUE"),
                              ("nonce", "INT", 10, ""),
                              ("timestamp", "VARCHAR", 20, ""),
                              ("transactions", "JSON", "", ""))
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
        open_transactions_db = Table("open_transactions", self.conn,
                                     ("id", "INT", 100, ""),
                                     ("sender", "VARCHAR", 50, ""),
                                     ("recipient", "VARCHAR", 50, ""),
                                     ("amount", "FLOAT", 20, ""),
                                     ("signature", "VARCHAR", 2048, ""))
        for tnx in open_transactions_db.get_all_data():
            transaction = Transaction(tnx['id'],
                                      tnx['sender'],
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
        blockchain_db = Table("blockchain", self.conn,
                              ("id", "INT", 100, ""),
                              ("hash", "VARCHAR", 100, "UNIQUE"),
                              ("previous_hash", "VARCHAR", 100, "UNIQUE"),
                              ("nonce", "INT", 10, ""),
                              ("timestamp", "VARCHAR", 20, ""),
                              ("transactions", "JSON", "", ""))
        blockchain_db.delete_all_data()
        for block in self.chain:
            blockchain_db.insert_data(block.index,
                                      block.hash,
                                      block.previous_hash,
                                      block.nonce,
                                      block.timestamp,
                                      dumps(block.transactions))

        open_transactions_db = Table("open_transactions", self.conn,
                                     ("id", "INT", 100, ""),
                                     ("sender", "VARCHAR", 50, ""),
                                     ("recipient", "VARCHAR", 50, ""),
                                     ("amount", "FLOAT", 20, ""),
                                     ("signature", "VARCHAR", 2048, ""))
        open_transactions_db.delete_all_data()
        for transaction in self.open_transactions:
            open_transactions_db.insert_data(transaction['index'],
                                             transaction['sender'],
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
        open_transactions_db = Table("open_transactions", self.conn,
                                     ("id", "INT", 100, ""),
                                     ("sender", "VARCHAR", 50, ""),
                                     ("recipient", "VARCHAR", 50, ""),
                                     ("amount", "FLOAT", 20, ""),
                                     ("signature", "VARCHAR", 2048, ""))
        open_transactions_db.delete_one("signature", transaction['signature'])
