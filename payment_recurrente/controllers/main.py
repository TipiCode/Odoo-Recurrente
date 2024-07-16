import hmac
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http, _
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

class RecurrenteController(http.Controller):
    _request_url = '/payment/recurrente/request'
    _webhook_url = '/payment/recurrente/webhook'

    @http.route(_request_url, type='http', methods=['GET'], auth='public')
    def recurrente_return_from_checkout(self, **data):
        """ Process the notification data sent by Recurrent after redirection from checkout.

        :param dict data: The notification data.
        """
        _logger.info(f"Handling redirection from Recurrente with data:\n{pprint.pformat(data)}")

        # Handle the request data.
        request.env['payment.transaction'].sudo()._handle_return_data(data)
        
        # Redirect the user to the status page.
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def recurrente_webhook(self):
        """ Process the notification data sent by Recurrente to the webhook.

        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        data = request.get_json_data()
        _logger.info(f"Notification received from Recurrente with data:\n{pprint.pformat(data)}")

        try:
            request.env['payment.transaction'].sudo()._handle_webhook_data(data)
        except ValidationError:
            _logger.exception("Unable to handle the notification data; skipping to acknowledge")
        return request.make_json_response('')
