{
    'name': 'Payment Provider: Recurrente',
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'summary': "Integration with Recurrente payment gateway.",
    'depends': ['payment'],
    'author': 'tipi(code)',
    'data': [
        'views/payment_recurrente_templates.xml',
        'views/payment_acquirer_views.xml',
        'views/payment_transaction_view.xml',
        'data/payment_icon_data.xml',
        'data/payment_acquirer_data.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
