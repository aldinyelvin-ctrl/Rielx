"""Punto de partida HTTP 402 para un recurso protegido de Agent B."""

from threading import Lock

from flask import Flask, jsonify, request

from payment_engine import PaymentEngine
from payment_models import PaymentRequest, PaymentVerificationRequest


PAYMENT_HEADER = "X-Rielx-Payment"


def create_agent_b_app(
    engine: PaymentEngine,
    required_payment: PaymentRequest,
    *,
    expected_source: str | None = None,
) -> Flask:
    """Crea un recurso que exige un pago XRPL Testnet previamente validado.

    El cliente (Agent A) paga por separado y envía el hash validado en
    ``X-Rielx-Payment``. Cada hash aceptado se consume una sola vez durante la
    vida del proceso para no reutilizar el mismo pago en peticiones posteriores.
    Para un despliegue multiinstancia, sustituye el conjunto en memoria por una
    reserva atómica persistente.
    """

    app = Flask(__name__)
    used_transactions: set[str] = set()
    transaction_lock = Lock()

    def payment_terms():
        return {
            "amount": str(required_payment.amount),
            "asset": {
                "currency": required_payment.asset.currency,
                "issuer": required_payment.asset.issuer,
            },
            "destination": required_payment.destination,
            "network": "XRPL Testnet",
            "payment_header": PAYMENT_HEADER,
        }

    def payment_required(reason: str):
        return (
            jsonify(
                {
                    "error": "payment_required",
                    "reason": reason,
                    "payment": payment_terms(),
                }
            ),
            402,
        )

    @app.get("/resource")
    def protected_resource():
        tx_hash = request.headers.get(PAYMENT_HEADER, "").strip().upper()
        if not tx_hash:
            return payment_required("Falta el hash de un pago XRPL Testnet")

        # La verificación y el consumo quedan bajo el mismo lock para impedir
        # que dos solicitudes paralelas acepten el mismo pago.
        with transaction_lock:
            if tx_hash in used_transactions:
                return jsonify({"error": "payment_already_used"}), 409

            try:
                verification = engine.verify_payment(
                    PaymentVerificationRequest(
                        tx_hash=tx_hash,
                        amount=required_payment.amount,
                        asset=required_payment.asset,
                        destination=required_payment.destination,
                        source=expected_source,
                    )
                )
            except (TypeError, ValueError, RuntimeError):
                return payment_required("No fue posible verificar el pago")

            if not verification.verified:
                return payment_required(
                    verification.reason or "El pago no cumple los requisitos"
                )

            used_transactions.add(tx_hash)

        return jsonify(
            {
                "status": "payment_verified",
                "tx_hash": tx_hash,
                "ledger_index": verification.ledger_index,
            }
        )

    return app
