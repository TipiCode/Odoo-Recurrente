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

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('recurrente', "Recurrente")], ondelete={'recurrente': 'set default'}
    )
    recurrente_public_key = fields.Char(string="Recurrente Public Key", groups='base.group_system')
    recurrente_secret_key = fields.Char(string="Recurrente Secret Key", groups='base.group_system')

    @api.model
    def _get_compatible_providers(self, *args, is_validation=False, **kwargs):
        """ Override of `payment` to filter out Recurrente providers for validation operations. """
        providers = super()._get_compatible_providers(*args, is_validation=is_validation, **kwargs)

        if is_validation:
            providers = providers.filtered(lambda p: p.code != 'recurrente')
        return providers

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'recurrente':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

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

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'recurrente':
            return default_codes
        return const.DEFAULT_PAYMENT_METHODS_CODES
