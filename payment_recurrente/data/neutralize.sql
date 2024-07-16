-- disable paypal payment provider
UPDATE payment_provider
   SET recurrente_public_key = NULL,
       recurrente_secret_key = NULL;
