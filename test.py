from blockchain import Blockchain
from app import mysql


def main():
    blockchain = Blockchain('Geo', mysql)
    blockchain.mine_block()
    blockchain.add_transactions('Geo', 'Maria', 2.4)
    blockchain.add_transactions('Geo', 'Jeff', 5.8)
    blockchain.mine_block()

    print(blockchain)

    # blockchain.chain[2].data = "Manipulated Data"
    print(blockchain.is_valid())


if __name__ == '__main__':
    main()
