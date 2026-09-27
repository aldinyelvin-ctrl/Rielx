class PaymentAdapter:
    def get_balance(self, address):
        raise NotImplementedError

    def pay(self, amount, asset, destination):
        raise NotImplementedError