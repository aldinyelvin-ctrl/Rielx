from xrpl.clients import JsonRpcClient
from xrpl.models.requests import ServerInfo
from xrpl.models.requests import AccountInfo


class XRPLAdapter:
    def __init__(self):
        self.client = JsonRpcClient(
            "https://s.altnet.rippletest.net:51234"
        )

        print("XRPL Adapter iniciado")

    def test_connection(self):
        response = self.client.request(ServerInfo())

        if response.is_successful():
            print("Conexion XRPL Testnet OK")
            return True

        print("Error de conexion XRPL")
        print(response.result)
        return False

    def get_balance(self, address):
        request = AccountInfo(
            account=address,
            ledger_index="validated",
        )

        response = self.client.request(request)

        if not response.is_successful():
            raise RuntimeError(
                f"Error consultando saldo: {response.result}"
            )

        balance_drops = int(
            response.result["account_data"]["Balance"]
        )

        return balance_drops / 1_000_000

    def pay(self, amount, asset, destination):
        print("Pago solicitado al XRPL Adapter")
        print(f"Cantidad: {amount}")
        print(f"Asset: {asset}")
        print(f"Destino: {destination}")

        if asset != "XRP":
            raise ValueError(
                "El XRPL Adapter actualmente solo soporta XRP"
            )

        print("Preparacion de pago completada")


if __name__ == "__main__":
    adapter = XRPLAdapter()
    adapter.test_connection()