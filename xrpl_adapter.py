from xrpl.clients import JsonRpcClient
from xrpl.models.requests import ServerInfo


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


if __name__ == "__main__":
    adapter = XRPLAdapter()
    adapter.test_connection()