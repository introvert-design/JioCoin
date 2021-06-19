from hashlib import sha256
from collections import OrderedDict
import json


def hash_block_data(block):
    """
    Creates a SHA-256 hash object of the block.
    :param block: The block to be hashed.
    :return: string - the encoded block in hexadecimal string format.
    """
    block_copy = block.__dict__.copy()
    del block_copy['hash']
    block_copy['transactions'] = ordered_dict(block_copy['transactions'])
    return sha256(str(block_copy).encode('utf-8')).hexdigest()


def is_json(string_elt):
    """
    Checks whether a string is valid json or not.
    :param string_elt: The string to be checked.
    :return: boolean - True: if the string is valid json
                       False: if the string is not valid json
    """
    try:
        json.loads(string_elt)
    except (ValueError, TypeError):
        return False
    return True


def ordered_dict(transactions):
    """
    Converts the dictionary object transactions to the ordered dictionary transactions.
    :param transactions: A list of dictionary object transactions
    :return: list of ordered dictionary - a list of ordered dictionary objects of transaction.
    """
    ordered_transactions = []
    for transaction in transactions:
        ordered_transaction = OrderedDict([('sender', transaction['sender']),
                                           ('recipient', transaction['recipient']),
                                           ('amount', transaction['amount']),
                                           ('signature', transaction['signature'])])
        ordered_transactions.append(ordered_transaction)
    return ordered_transactions
