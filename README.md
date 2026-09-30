# Rielx

Infraestructura experimental para pagos agénticos sobre **XRPL Testnet**.
No está preparada para fondos reales.

## Estado actual

Rielx permite actualmente:

- Crear wallets de prueba para Agent A y Agent B, y guardar sus credenciales en
  `.env`, excluido de Git.
- Consultar saldos XRP y saldos de activos emitidos (issued currencies).
- Modelar XRP y activos emitidos con su issuer.
- Preparar y enviar pagos XRP o emitidos desde Agent A, pero sólo después de
  pasar `confirm=True` explícitamente.
- Consultar si una cuenta mantiene una trust line para un activo y abrir una
  trust line desde el firmante explícito de Agent A o Agent B, sólo con
  confirmación explícita.
- Verificar un pago ya validado en el ledger sin una seed: exige `tesSUCCESS`,
  destino, origen opcional, activo, importe y entrega exactos; también rechaza
  pagos parciales.
- Exponer una base de recurso de Agent B que responde HTTP 402 y acepta un hash
  en `X-Rielx-Payment` sólo una vez tras verificarlo en Testnet.

El adapter usa exclusivamente `https://s.altnet.rippletest.net:51234` y aborta
si `XRPL_NETWORK` no es exactamente `testnet`.

## Activos emitidos y RLUSD de prueba

Un activo emitido necesita el issuer de **Testnet** correspondiente. No se
incluye ni se presupone un issuer de RLUSD en este repositorio.

```python
from decimal import Decimal

from payment_models import Asset, PaymentRequest, TrustLineRequest

rlusd = Asset("RLUSD", issuer="<ISSUER_DE_TESTNET>")
```

XRPL no admite `RLUSD` directamente como código corto de moneda. Rielx acepta
ese alias legible y lo traduce a
`524C555344000000000000000000000000000000`, la representación XRPL de 160
bits. Los códigos de tres caracteres (por ejemplo, `USD`) se usan tal cual.

Antes de recibir un activo emitido, la cuenta receptora necesita una trust
line. Para un pago Agent A → Agent B, se abre desde el signer de Agent B. La
siguiente operación **sí envía una transacción de Testnet**, por lo que sólo se
debe ejecutar tras revisar issuer, límite y cuenta receptora:

```python
from payment_engine import PaymentEngine
from xrpl_adapter import XRPLAdapter

agent_b_engine = PaymentEngine(XRPLAdapter(signer_account="agent_b"))
agent_b_engine.open_trust_line(
    TrustLineRequest(asset=rlusd, limit=Decimal("100")),
    confirm=True,
)
```

El pago se firma desde Agent A:

```python
agent_a_engine = PaymentEngine(XRPLAdapter(signer_account="agent_a"))
agent_a_engine.pay(
    PaymentRequest(
        amount=Decimal("2.5"),
        asset=rlusd,
        destination="<AGENT_B_ADDRESS>",
    ),
    confirm=True,
)
```

Si se omite `confirm=True`, Rielx corta la operación antes de firmar o enviar.

## Verificación y base Agent A ↔ Agent B

Agent B puede usar el adapter en modo de sólo lectura, sin `AGENT_A_SEED`:

```python
from decimal import Decimal

from agent_b_api import create_agent_b_app
from payment_engine import PaymentEngine
from payment_models import Asset, PaymentRequest
from xrpl_adapter import XRPLAdapter

verifier = PaymentEngine(XRPLAdapter(require_signer=False))
app = create_agent_b_app(
    verifier,
    PaymentRequest(
        amount=Decimal("2.5"),
        asset=Asset("RLUSD", issuer="<ISSUER_DE_TESTNET>"),
        destination="<AGENT_B_ADDRESS>",
    ),
    expected_source="<AGENT_A_ADDRESS>",
)
```

`GET /resource` devuelve HTTP 402 con los términos de pago si falta el header.
Agent A paga fuera de la petición y reintenta incluyendo
`X-Rielx-Payment: <TX_HASH>`. Si la transacción está validada y coincide de
forma exacta, el recurso responde 200. Un hash ya consumido recibe 409. La
protección antirrepetición actual es intencionalmente local al proceso; un
despliegue de varias instancias requiere una reserva atómica persistente.

## Pruebas locales

Las pruebas no contactan Testnet y no firman ni envían transacciones:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Seguridad

- Sólo XRPL Testnet; no usar con fondos reales.
- Las seeds no se almacenan en el código ni se añaden a Git.
- Los importes son `Decimal`; no se aceptan floats implícitos.
- XRP debe corresponder a un número entero de drops.
- Un pago emitido sólo se acepta para Agent B cuando el ledger confirma la
  entrega exacta y no contiene la bandera de pago parcial.
