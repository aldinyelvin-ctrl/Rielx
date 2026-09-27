class PaymentEngine:
    def __init__(self):
        print("Rielx Payment Engine iniciado")

    def pay(self, amount, asset, destination):
        print("Pago solicitado")
        print(f"Cantidad: {amount}")
        print(f"Asset: {asset}")
        print(f"Destino: {destination}")

if __name__ == "__main__":
    engine = PaymentEngine()

    engine.pay(
        amount=0.001,
        asset="XRP",
        destination="rTEST_DESTINATION",
    )