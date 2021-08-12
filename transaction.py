class Transaction:
    """
    Initializes the instance attributes of a transaction  and returns the transaction as a string.
    """
    def __init__(self, index, sender, recipient, amount, signature):
        self.index = index
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.signature = signature

    def __repr__(self):
        """
        Returns a dictionary of the Transaction object's attributes in the string format
        :return: string - transaction attributes
        """
        return str(self.__dict__)
