-- Pagamento Stripe Checkout sugli ordini.
--   stripe_session_id     = id della Checkout Session (per ritrovare l'ordine
--                           dal webhook e per idempotenza).
--   stripe_payment_intent = id del PaymentIntent pagato (riferimento/refund).
ALTER TABLE orders ADD COLUMN stripe_session_id VARCHAR(120);
ALTER TABLE orders ADD COLUMN stripe_payment_intent VARCHAR(120);
