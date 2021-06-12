class Block:
    def __init__(self, index, previous_hash, timestamp, transactions, block_hash=None, nonce=0):
        self.index = index
        self.hash = block_hash
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.timestamp = timestamp
        self.transactions = transactions

    def __repr__(self):
        return str(self.__dict__)
