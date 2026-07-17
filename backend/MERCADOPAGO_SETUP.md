# Mercado Pago Checkout Pro (Phase 1)

## Sandbox credentials

1. Sign in to the [Mercado Pago Developers credentials panel](https://www.mercadopago.com/developers/panel/app).
2. Create or select an application and open its test credentials.
3. Copy the production Access Token and Public Key for the deployed environment.

## Local configuration

1. Copy `.env.example` to `.env` in this `backend` directory.
2. Set the database values and these variables:

   ```env
   DEBUG=false
   MERCADOPAGO_ACCESS_TOKEN=APP_USR-your_production_access_token
   MERCADOPAGO_PUBLIC_KEY=APP_USR-your_production_public_key
   FRONTEND_URL=https://YOUR_PUBLIC_DOMAIN
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

`POST /guest-purchases` creates a pending purchase, a Checkout Pro preference, and a pending payment record. The API always returns Mercado Pago's `init_point`; it never returns `sandbox_init_point`.

## Webhook (Phase 2)

In the Mercado Pago application, configure the payment webhook URL as:

```text
https://YOUR_PUBLIC_DOMAIN/api/payments/webhook
```

Mercado Pago must be able to reach this HTTPS URL. Set `FRONTEND_URL` to the public URL that serves `index.html`; each Checkout Pro preference then receives this payment notification URL automatically. The webhook verifies each notification against Mercado Pago's Payments API before issuing a PIN.
