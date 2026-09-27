# Rielx

Infraestructura experimental para pagos agenticos sobre XRPL.

## Estado actual

Rielx se encuentra en fase de prototipo sobre **XRPL Testnet**.

Actualmente podemos:

- Crear wallets para Agent A y Agent B.
- Guardar las credenciales de forma segura en `.env`.
- Verificar que las seeds corresponden a sus addresses.
- Consultar los saldos desde Python.
- Preparar pagos XRP.
- Firmar y enviar pagos desde Agent A.
- Verificar posteriormente el resultado en el ledger.

## Primer pago exitoso

El primer pago de prueba de Rielx fue realizado en XRPL Testnet.

**Origen**

Agent A

**Destino**

Agent B

**Cantidad**

`0.001 XRP`

**Resultado XRPL**

`tesSUCCESS`

**TX Hash**

`83B48E5BF4D61832D78A2524995186CFB30DB07F2FA7784E6C494FC4C813758B`

### Saldos verificados despues del pago

| Cuenta | Saldo |
|---|---:|
| Agent A | 99.99899 XRP |
| Agent B | 100.001 XRP |

La diferencia adicional de Agent A corresponde al coste de la transaccion.

## Seguridad

- XRPL Testnet unicamente.
- Las seeds no se almacenan en el codigo.
- `.env` esta excluido de Git.
- Las transacciones requieren confirmacion explicita antes de enviarse.
- No utilizar estas credenciales ni este codigo experimental con fondos reales sin implementar las verificaciones de seguridad necesarias.

## Proximo objetivo

Convertir el flujo de pago de prueba en un componente reutilizable del motor de pagos de Rielx.
