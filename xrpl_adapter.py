import os
import re
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from payment_adapter import PaymentAdapter
from payment_models import (
    Asset,
    BalanceRequest,
    PaymentRequest,
    PaymentResult,
    PaymentVerificationRequest,
    PaymentVerificationResult,
    TrustLineRequest,
    TrustLineResult,
)
from xrpl.clients import JsonRpcClient
from xrpl.core.addresscodec import is_valid_classic_address
from xrpl.models import IssuedCurrency, Payment, TrustSet
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models.requests import AccountInfo, AccountLines, ServerInfo, Tx
from xrpl.transaction import autofill_and_sign, submit_and_wait
from xrpl.wallet import Wallet


TESTNET_URL = "https://s.altnet.rippletest.net:51234"
_DROPS_PER_XRP = Decimal("1000000")
_PARTIAL_PAYMENT_FLAG = 0x00020000
_TX_HASH = re.compile(r"^[A-Fa-f0-9]{64}$")


class XRPLAdapter(PaymentAdapter):
    """Adapter XRPL restringido al endpoint público de Testnet.

    Para un proceso de Agent B que sólo verifique cobros, instáncialo con
    ``require_signer=False``. En ese modo no se carga ni se necesita una seed.
    """

    def __init__(
        self,
        *,
        require_signer: bool = True,
        signer_account: str = "agent_a",
        client=None,
    ):
        load_dotenv()

        if os.getenv("XRPL_NETWORK") != "testnet":
            raise RuntimeError(
                "Por seguridad, XRPLAdapter sólo puede ejecutarse en Testnet"
            )
        if signer_account not in {"agent_a", "agent_b"}:
            raise ValueError("signer_account debe ser 'agent_a' o 'agent_b'")

        self.client = client or JsonRpcClient(TESTNET_URL)
        self.agent_a_address = os.getenv("AGENT_A_ADDRESS")
        self.signer_account = signer_account
        self.signer_address = None
        self.wallet = None

        if require_signer:
            account_name = signer_account.upper()
            seed = os.getenv(f"{account_name}_SEED")
            address = os.getenv(f"{account_name}_ADDRESS")
            if not seed:
                raise RuntimeError(f"{account_name}_SEED no configurada")
            if not address:
                raise RuntimeError(f"{account_name}_ADDRESS no configurada")

            wallet = Wallet.from_seed(seed)
            if wallet.classic_address != address:
                raise RuntimeError(
                    f"La seed de {signer_account} no corresponde a su address"
                )
            self.wallet = wallet
            self.signer_address = address

    def test_connection(self) -> bool:
        response = self.client.request(ServerInfo())
        return response.is_successful()

    def validate_asset(self, asset: Asset) -> None:
        if not isinstance(asset, Asset):
            raise TypeError("asset debe ser una instancia de Asset")
        if asset.is_xrp:
            if asset.issuer is not None:
                raise ValueError("XRP no debe tener issuer")
            return

        try:
            IssuedCurrency(
                currency=asset.ledger_currency,
                issuer=asset.issuer,
            )
        except Exception as exc:
            raise ValueError(f"Activo emitido inválido: {exc}") from exc

    def validate_destination(self, destination: str) -> None:
        if not isinstance(destination, str) or not is_valid_classic_address(
            destination
        ):
            raise ValueError("Destination no es una dirección XRPL válida")

    @staticmethod
    def _transaction_result(result: dict) -> str:
        metadata = result.get("meta") or {}
        return metadata.get("TransactionResult", "unknown")

    @staticmethod
    def _ledger_index(result: dict) -> int | None:
        ledger_index = result.get("ledger_index")
        return int(ledger_index) if ledger_index is not None else None

    def _to_xrpl_amount(self, amount: Decimal, asset: Asset):
        if not isinstance(amount, Decimal) or not amount.is_finite() or amount <= 0:
            raise ValueError("El monto debe ser un Decimal positivo y finito")

        if asset.is_xrp:
            drops = amount * _DROPS_PER_XRP
            if drops != drops.to_integral_value():
                raise ValueError("Los pagos XRP no pueden tener menos de un drop")
            return str(int(drops))

        return IssuedCurrencyAmount(
            currency=asset.ledger_currency,
            issuer=asset.issuer,
            value=format(amount, "f"),
        )

    @staticmethod
    def _matches_line(line: dict, asset: Asset) -> bool:
        return (
            line.get("account") == asset.issuer
            and str(line.get("currency", "")).upper() == asset.ledger_currency
        )

    def _account_lines(self, address: str, asset: Asset) -> list[dict]:
        response = self.client.request(
            AccountLines(
                account=address,
                peer=asset.issuer,
                ledger_index="validated",
            )
        )
        if not response.is_successful():
            raise RuntimeError(f"Error consultando trust lines: {response.result}")
        return response.result.get("lines", [])

    def get_balance(self, request: BalanceRequest) -> Decimal:
        self.validate_asset(request.asset)
        self.validate_destination(request.address)

        if request.asset.is_xrp:
            response = self.client.request(
                AccountInfo(
                    account=request.address,
                    ledger_index="validated",
                )
            )
            if not response.is_successful():
                raise RuntimeError(f"Error consultando saldo: {response.result}")
            balance_drops = int(response.result["account_data"]["Balance"])
            return Decimal(balance_drops) / _DROPS_PER_XRP

        for line in self._account_lines(request.address, request.asset):
            if self._matches_line(line, request.asset):
                return Decimal(line["balance"])
        return Decimal("0")

    def has_trust_line(self, address: str, asset: Asset) -> bool:
        if asset.is_xrp:
            return False
        self.validate_asset(asset)
        self.validate_destination(address)
        for line in self._account_lines(address, asset):
            if self._matches_line(line, asset):
                return Decimal(line.get("limit", "0")) > 0
        return False

    def _require_signer(self) -> None:
        if self.wallet is None or not self.signer_address:
            raise RuntimeError(
                "Este adapter es de sólo lectura; no tiene un signer configurado"
            )

    def open_trust_line(
        self, request: TrustLineRequest, *, confirm: bool
    ) -> TrustLineResult:
        if not confirm:
            raise PermissionError(
                "Abrir una trust line requiere confirm=True explícito"
            )
        if request.asset.is_xrp:
            raise ValueError("XRP no utiliza trust lines")
        self.validate_asset(request.asset)
        self._require_signer()

        limit_amount = self._to_xrpl_amount(request.limit, request.asset)
        trust_set = TrustSet(
            account=self.signer_address,
            limit_amount=limit_amount,
        )
        signed = autofill_and_sign(trust_set, self.client, self.wallet)
        response = submit_and_wait(signed, self.client)
        result = response.result
        transaction_result = self._transaction_result(result)
        return TrustLineResult(
            success=transaction_result == "tesSUCCESS",
            asset=request.asset,
            limit=request.limit,
            tx_hash=result["hash"],
            ledger_index=self._ledger_index(result),
            transaction_result=transaction_result,
        )

    def pay(self, request: PaymentRequest, *, confirm: bool) -> PaymentResult:
        if not confirm:
            raise PermissionError("Enviar un pago requiere confirm=True explícito")
        self.validate_asset(request.asset)
        self.validate_destination(request.destination)
        self._require_signer()

        payment = Payment(
            account=self.signer_address,
            destination=request.destination,
            amount=self._to_xrpl_amount(request.amount, request.asset),
        )
        signed = autofill_and_sign(payment, self.client, self.wallet)
        response = submit_and_wait(signed, self.client)
        result = response.result
        transaction_result = self._transaction_result(result)
        delivered_amount = self._decimal_from_amount(
            (result.get("meta") or {}).get("delivered_amount"), request.asset
        )
        return PaymentResult(
            success=transaction_result == "tesSUCCESS",
            amount=request.amount,
            asset=request.asset,
            destination=request.destination,
            tx_hash=result["hash"],
            ledger_index=self._ledger_index(result),
            delivered_amount=delivered_amount,
            transaction_result=transaction_result,
        )

    def _amount_matches(
        self, value, asset: Asset, expected: Decimal
    ) -> bool:
        try:
            if asset.is_xrp:
                return isinstance(value, str) and Decimal(value) == (
                    expected * _DROPS_PER_XRP
                )
            return (
                isinstance(value, dict)
                and str(value.get("currency", "")).upper()
                == asset.ledger_currency
                and value.get("issuer") == asset.issuer
                and Decimal(value["value"]) == expected
            )
        except (InvalidOperation, KeyError):
            return False

    def _decimal_from_amount(self, value, asset: Asset) -> Decimal | None:
        if value in (None, "unavailable"):
            return None
        try:
            if asset.is_xrp and isinstance(value, str):
                return Decimal(value) / _DROPS_PER_XRP
            if (
                isinstance(value, dict)
                and str(value.get("currency", "")).upper()
                == asset.ledger_currency
                and value.get("issuer") == asset.issuer
            ):
                return Decimal(value["value"])
        except (InvalidOperation, KeyError):
            return None
        return None

    def verify_payment(
        self, request: PaymentVerificationRequest
    ) -> PaymentVerificationResult:
        if not _TX_HASH.fullmatch(request.tx_hash):
            return PaymentVerificationResult(
                verified=False,
                tx_hash=request.tx_hash,
                transaction_result=None,
                ledger_index=None,
                delivered_amount=None,
                reason="El hash de transacción no tiene el formato XRPL esperado",
            )

        try:
            response = self.client.request(Tx(transaction=request.tx_hash))
        except Exception:
            return PaymentVerificationResult(
                verified=False,
                tx_hash=request.tx_hash,
                transaction_result=None,
                ledger_index=None,
                delivered_amount=None,
                reason="No fue posible consultar la transacción en XRPL Testnet",
            )

        result = response.result
        transaction_result = self._transaction_result(result)
        ledger_index = self._ledger_index(result)
        delivered_amount = self._decimal_from_amount(
            (result.get("meta") or {}).get("delivered_amount"), request.asset
        )

        def rejected(reason: str) -> PaymentVerificationResult:
            return PaymentVerificationResult(
                verified=False,
                tx_hash=request.tx_hash,
                transaction_result=transaction_result,
                ledger_index=ledger_index,
                delivered_amount=delivered_amount,
                reason=reason,
            )

        if not response.is_successful():
            return rejected("XRPL no encontró una transacción verificable")
        if result.get("validated") is not True:
            return rejected("La transacción aún no está validada")
        if result.get("hash", request.tx_hash).upper() != request.tx_hash.upper():
            return rejected("El hash devuelto no coincide con el pago solicitado")
        if result.get("TransactionType") != "Payment":
            return rejected("La transacción no es un Payment")
        if transaction_result != "tesSUCCESS":
            return rejected(f"El pago no fue exitoso: {transaction_result}")
        if int(result.get("Flags", 0)) & _PARTIAL_PAYMENT_FLAG:
            return rejected("No se aceptan pagos parciales")
        if result.get("Destination") != request.destination:
            return rejected("El destino no coincide con el pago esperado")
        if request.source is not None and result.get("Account") != request.source:
            return rejected("El origen no coincide con el pagador esperado")
        if not self._amount_matches(result.get("Amount"), request.asset, request.amount):
            return rejected("El importe o activo no coincide con el pago esperado")
        if delivered_amount != request.amount:
            return rejected("El ledger no confirmó la entrega exacta esperada")

        return PaymentVerificationResult(
            verified=True,
            tx_hash=request.tx_hash,
            transaction_result=transaction_result,
            ledger_index=ledger_index,
            delivered_amount=delivered_amount,
        )


if __name__ == "__main__":
    print("Conexión XRPL Testnet OK" if XRPLAdapter().test_connection() else "Error")
