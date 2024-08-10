import logging
import pprint

from werkzeug import urls

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_recurrente import const
from odoo.addons.payment_recurrente.controllers.main import RecurrenteController

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    id_recurrente_checkout = fields.Char(string="Recurrente Checkout ID")
    url_recurrente_checkout = fields.Char(string="Recurrente Checkout URL")
    product_recurrente_checkout = fields.Char(string="Recurrente Checkout Product")

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Recurrente-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != 'recurrente':
            return res

        # Initiate the payment and retrieve the payment link data.
        number = int(self.reference.split("-")[0][2:])
        name_split = self.partner_name.split(" ", maxsplit=1)
        name, surname = (name_split[0], name_split[1]) if len(name_split) > 1 else (name_split[0], "--")
        payload = {
            'number': number,
            'description': self.reference,
            'amount': self.amount,
            'currency': self.currency_id.name,
            'redirection': {
                "successUrl": f"{self.get_base_url()}{RecurrenteController._request_url}?tx_ref={self.reference}&status=request_success",
                "cancelUrl": f"{self.get_base_url()}{RecurrenteController._request_url}?tx_ref={self.reference}&status=request_cancel",
            },
            'billing': {
                "name": name,
                "surname": surname,
                "taxid": self.partner_id.vat or "CF",
                "email": self.partner_email,
                "phone": self.partner_phone,
                "address": self.partner_address or "Ciudad",
            }
        }
        payment_link_data = self.acquirer_id._recurrente_make_request('checkouts', payload=payload)

        self.id_recurrente_checkout = payment_link_data["id"]
        self.url_recurrente_checkout = payment_link_data["url"]
        self.product_recurrente_checkout = payment_link_data["product"]

        # Extract the payment link URL and embed it in the redirect form.
        rendering_values = {
            'api_url': payment_link_data['url'],
        }
        return rendering_values

    def _get_tx_return_data(self, notification_data):
        """ Find the transaction based on the request data.

        :param dict notification_data: The request data sent by the provider.
        :return: The transaction, if found.
        :rtype: recordset of `payment.transaction`
        """
        reference = notification_data['tx_ref']
        tx = self.search([('reference', '=', reference), ('provider', '=', 'recurrente')])
        if not tx:
            raise ValidationError(
                "Recurrente: " + _(f"No transaction found matching reference {reference}.")
            )
        return tx

    def _process_return_data(self, notification_data):
        """ Update the transaction state based on the request data.

        Note: `self.ensure_one()`

        :param dict notification_data: The request data sent by the provider.
        :return: None
        """
        self.ensure_one()
        request_status = notification_data["status"]
        if request_status in const.PAYMENT_STATUS_MAPPING['pending'] and self.state == 'draft':
            self._set_pending(_("The payment is in process."))
        elif request_status in const.PAYMENT_STATUS_MAPPING['cancel'] and self.state == 'draft':
            self._set_canceled(_("The client went back from the Recurrente's checkout."))

    def _handle_return_data(self, notification_data):
        """ Match the transaction with the notification data, update its state and return it.

        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction.
        :rtype: recordset of `payment.transaction`
        """
        tx = self._get_tx_return_data(notification_data)
        tx._process_return_data(notification_data)
        # tx._execute_callback()
        return tx

    def _get_tx_from_webhook_data(self, notification_data):
        """ Find the transaction based on the webhook data.

        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction, if found.
        :rtype: recordset of `payment.transaction`
        """
        
        checkout = notification_data.get('checkout')
        product = notification_data.get('product')

        checkout_id = checkout.get('id') if checkout else False
        product_id = product.get('id') if product else False
        if not checkout_id or not product_id:
            raise ValidationError("Recurrente: " + _("Received data with missing reference."))

        tx = self.search([('id_recurrente_checkout', '=', checkout_id), ('product_recurrente_checkout', '=', product_id), ('provider', '=', 'recurrente')])
        if not tx:
            raise ValidationError(
                "Recurrente: " + _(f"No transaction found matching reference {checkout_id} and {product_id}.")
            )
        return tx

    def _process_webhook_data(self, notification_data):
        """ Update the transaction state and the provider reference based on the webhook data.

        Note: `self.ensure_one()`

        :param dict notification_data: The webhook data sent by the provider.
        :return: None
        """
        self.ensure_one()

        payment = notification_data.get("payment")

        payment_id = payment.get("id") if payment else False
        if not payment_id:
            raise ValidationError("Recurrente: " + _("Received data with missing payment."))

        # Update the provider reference.
        self.acquirer_reference = payment_id

        # Update the payment state.
        payment_status = notification_data['event_type'].lower()
        if payment_status in const.PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['error']:
            self._set_error(_(
                f"An error occurred during the processing of your payment (status {payment_status}). Please try again.\nReason: {notification_data.get('failure_reason', 'No reason.')}",
            ))
        else:
            _logger.warning(
                f"Received data with invalid payment status ({payment_status}) for transaction with reference {self.reference}.",
            )
            self._set_error("Recurrente: " + _(f"Unknown payment status: {payment_status}"))

    def _handle_webhook_data(self, notification_data):
        """ Match the transaction with the notification data, update its state and return it.

        :param str provider: The code of the provider handling the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction.
        :rtype: recordset of `payment.transaction`
        """
        tx = self._get_tx_from_webhook_data(notification_data)
        tx._process_webhook_data(notification_data)
        # tx._execute_callback()
        return tx
