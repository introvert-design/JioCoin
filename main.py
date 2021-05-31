import hashlib
from time import time


def hash_block_data(block):
    block_copy = block.__dict__.copy()
    del block_copy['hash']
    return hashlib.sha256(str(block_copy).encode('utf-8')).hexdigest()


class Block:
    def __init__(self, index, data, previous_hash, timestamp):
        self.index = index
        self.hash = None
        self.previous_hash = previous_hash
        self.nonce = 0
        self.timestamp = timestamp
        self.data = data

    def __repr__(self):
        return f'Index: {self.index}\nHash: {self.hash}\nPrevious: {self.previous_hash}\nNonce: {self.nonce}\n' \
               f'Time: {self.timestamp}\nData: {self.data}\n'


class Blockchain:
    def __init__(self, chain=None, difficulty=4):
        if chain is None:
            chain = []
        self.chain = chain
        self.difficulty = difficulty

    def add_block(self, block):
        self.chain.append(block)

    def mine_block(self, data):
        index = len(self.chain) + 1
        try:
            previous_hash = self.chain[-1].__dict__['hash']
        except IndexError:
            previous_hash = '0' * 62 + 'x0'
        timestamp = time()
        block = Block(index, data, previous_hash, timestamp)
        calculated_hash = hash_block_data(block)
        while not calculated_hash[:self.difficulty] == '0' * self.difficulty:
            block.nonce += 1
            block.timestamp = time()
            calculated_hash = hash_block_data(block)
        else:
            block.hash = calculated_hash
            self.add_block(block)

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


def main():
    blockchain = Blockchain()
    database = ['Test Data 1', 'Test Data 2', 'Test Data 3', 'Test Data 4']
    for data in database:
        blockchain.mine_block(data)

    for block in blockchain.chain:
        print(block)

    blockchain.chain[2].data = "Manipulated Data"
    print(blockchain.is_valid())


if __name__ == '__main__':
    main()
