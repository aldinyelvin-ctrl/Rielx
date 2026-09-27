from xrpl_adapter import XRPLAdapter


class PaymentEngine:
    def __init__(self, adapter):
        self.adapter = adapter

    def get_balance(self, address):
        return self.adapter.get_balance(address)

        print("Rielx Payment Engine iniciado")


if __name__ == "__main__":
    xrpl_adapter = XRPLAdapter()
    engine = PaymentEngine(xrpl_adapter)