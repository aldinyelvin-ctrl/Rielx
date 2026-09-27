from abc import ABC, abstractmethod


class PaymentAdapter(ABC):

    @abstractmethod
    def get_balance(self, address):
        pass

    @abstractmethod
    def validate_destination(self, destination):
        pass

    @abstractmethod
    def pay(self, amount, asset, destination):
        pass