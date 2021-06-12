from hashlib import sha256
import json


def hash_block_data(block):
    block_copy = block.__dict__.copy()
    del block_copy['hash']
    return sha256(str(block_copy).encode('utf-8')).hexdigest()


def is_json(myjson):
    try:
        json.loads(myjson)
    except (ValueError, TypeError):
        return False
    return True
