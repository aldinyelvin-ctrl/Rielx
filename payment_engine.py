from xrpl_adapter import XRPLAdapter


class PaymentEngine:
    def __init__(self, adapter):
        self.adapter = adapter

        print("Rielx Payment Engine iniciado")

    def get_balance(self, address):
        return self.adapter.get_balance(address)

    def pay(self, amount, asset, destination):
        return self.adapter.pay(
            amount=amount,
            asset=asset,
            destination=destination,
        )

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    xrpl_adapter = XRPLAdapter()
    engine = PaymentEngine(xrpl_adapter)

    agent_b_address = os.getenv("AGENT_B_ADDRESS")

    if not agent_b_address:
        raise RuntimeError("AGENT_B_ADDRESS no configurada")

    result = engine.pay(
        amount=0.001,
        asset="XRP",
        destination=agent_b_address,
    )

    print("Pago completado")
    print(f"Resultado: {result}")