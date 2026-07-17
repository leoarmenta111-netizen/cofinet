# Mercado Pago Checkout Pro (Phase 1)

## Sandbox credentials

1. Sign in to the [Mercado Pago Developers credentials panel](https://www.mercadopago.com/developers/panel/app).
2. Create or select an application and open its test credentials.
3. Copy the sandbox Access Token and Public Key. Do not use production credentials for local testing.

## Local configuration

1. Copy `.env.example` to `.env` in this `backend` directory.
2. Set the database values and these variables:

   ```env
   MERCADOPAGO_ACCESS_TOKEN=TEST-your_sandbox_access_token
    MERCADOPAGO_PUBLIC_KEY=TEST-your_sandbox_public_key
    FRONTEND_URL=http://localhost:5500
   ```

   The access token is server-only. Never expose it to the browser or commit `.env`.

3. Install the checkout SDK along with the existing backend dependencies:

   ```powershell
   pip install -r requirements.txt -r requirements-payment.txt
   ```

4. Create/update database tables and run the API:

   ```powershell
   python -m app.database.init_db
   uvicorn app.main:app --reload
   ```

With `DEBUG=true`, the API prefers Mercado Pago's sandbox checkout URL when available. `POST /guest-purchases` creates a pending purchase, a Checkout Pro preference, and a pending payment record.

## Webhook (Phase 2)

In the Mercado Pago application, configure the payment webhook URL as:

```text
https://YOUR-PUBLIC-API-DOMAIN/payments/webhook
```

Mercado Pago must be able to reach this URL; a localhost URL will not receive production or sandbox notifications. Set `FRONTEND_URL` to the public URL that serves `index.html`, so Checkout Pro can redirect the guest back to the polling screen after payment. The webhook verifies each notification against Mercado Pago's Payments API before issuing a PIN.
