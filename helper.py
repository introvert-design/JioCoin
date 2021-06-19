from hashlib import sha256
from collections import OrderedDict
import json


def hash_block_data(block):
    block_copy = block.__dict__.copy()
    del block_copy['hash']
    block_copy['transactions'] = ordered_dict(block_copy['transactions'])
    return sha256(str(block_copy).encode('utf-8')).hexdigest()


def is_json(myjson):
    try:
        json.loads(myjson)
    except (ValueError, TypeError):
        return False
    return True


def ordered_dict(transactions):
    ordered_transactions = []
    for transaction in transactions:
        ordered_transaction = OrderedDict([('sender', transaction['sender']),
                                           ('recipient', transaction['recipient']),
                                           ('amount', transaction['amount']),
                                           ('signature', transaction['signature'])])
        ordered_transactions.append(ordered_transaction)
    return ordered_transactions
