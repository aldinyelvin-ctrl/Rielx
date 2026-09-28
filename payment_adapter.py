from abc import ABC, abstractmethod


class PaymentAdapter(ABC):

    @abstractmethod
    def get_balance(self, request):
        pass

    @abstractmethod
    def validate_destination(self, destination):
        pass

    @abstractmethod
    def validate_asset(self, asset):
        pass

    @abstractmethod
    def pay(self, request):
        pass