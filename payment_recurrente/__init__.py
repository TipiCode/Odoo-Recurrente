from . import controllers
from . import models

from odoo.addons.payment import reset_payment_acquirer

def uninstall_hook(cr, registry):
    reset_payment_acquirer(cr, registry, 'recurrente')