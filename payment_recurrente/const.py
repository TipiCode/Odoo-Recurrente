SUPPORTED_CURRENCIES = (
    'GTQ',
    'USD',
)

DEFAULT_PAYMENT_METHODS_CODES = [
    'recurrente',
]

PAYMENT_STATUS_MAPPING = {
    'pending': ('request_success', 'bank_transfer_intent.pending', 'payment_intent.failed',),
    'done': ('bank_transfer_intent.succeeded', 'payment_intent.succeeded',),
    'cancel': ('request_cancel',),
    'error': ('bank_transfer_intent.failed',),
}
