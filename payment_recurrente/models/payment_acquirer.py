import logging
import pprint

import requests
from werkzeug.urls import url_join

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment_recurrente import const
from odoo.addons.payment_recurrente.controllers.main import RecurrenteController

_logger = logging.getLogger(__name__)

class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('recurrente', "Recurrente")], ondelete={'recurrente': 'set default'}
    )
    recurrente_public_key = fields.Char(string="Recurrente Public Key", groups='base.group_system')
    recurrente_secret_key = fields.Char(string="Recurrente Secret Key", groups='base.group_system')

    @api.model
    def _get_compatible_acquirers(self, *args, currency_id=None, **kwargs):
        """ Override of `payment` to filter out Recurrente acquirers for unsupported currencies. """
        acquirers = super()._get_compatible_acquirers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()
        if currency and currency.name not in const.SUPPORTED_CURRENCIES:
            acquirers = acquirers.filtered(lambda p: p.provider != 'recurrente')
        return acquirers

    def _recurrente_make_request(self, endpoint, payload=None, method='POST'):
        """ Make a request to Recurrente API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()
        
        url = url_join('https://aurora.codingtipi.com/pay/v1/recurrente/', endpoint)
        headers = {
            'X-PUBLIC-KEY': f'{self.recurrente_public_key}',
            'X-SECRET-KEY': f'{self.recurrente_secret_key}',
            'X-ORIGIN': f'{self.get_base_url()}',
            'X-STORE': f"{self.company_id.name.replace(' ', '-')}",
        }
        try:
            if method == 'GET':
                response = requests.get(url, params=payload, headers=headers, timeout=10)
            else:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    f"Invalid API request at {url} with data:\n{pprint.pformat(payload)}"
                )
                raise ValidationError("Recurrente: " + _(
                    f"The communication with the API failed. Recurrente gave us the following information: '{response.json().get('message', '')}'" 
                ))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception(f"Unable to reach endpoint at {url}")
            raise ValidationError(
                "Recurrente: " + _("Could not establish the connection to the API.")
            )
        return response.json()

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'recurrente':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_recurrente.payment_method_recurrente').id
