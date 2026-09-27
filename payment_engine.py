from xrpl_adapter import XRPLAdapter
from xrpl.core.addresscodec import is_valid_classic_address


class PaymentEngine:
    def __init__(self, adapter):
        self.adapter = adapter

        print("Rielx Payment Engine iniciado")

    def get_balance(self, address):
        return self.adapter.get_balance(address)

    def pay(self, amount, asset, destination):
        if amount <= 0:
            raise ValueError("El monto debe ser mayor que cero")

        if asset != "XRP":
            raise ValueError("Asset no soportado por el Payment Engine")

        if not is_valid_classic_address(destination):
            raise ValueError("Destination no es una dirección XRPL válida")

        result = self.adapter.pay(
            amount=amount,
            asset=asset,
            destination=destination,
        )

        return {
            "success": result["success"],
            "amount": amount,
            "asset": asset,
            "destination": destination,
            "tx_hash": result["tx_hash"],
            "ledger_index": result["ledger_index"],
            "delivered_amount": result["delivered_amount"],
        }