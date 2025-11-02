# -*- coding: utf-8 -*-
from odoo import models
import requests
import logging
import time

_logger = logging.getLogger(__name__)

class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

    def write(self, vals):
        old_states = {r.id: r.state for r in self}
        res = super(AccountEdiDocument, self).write(vals)

        if 'state' in vals or 'error' in vals:
            for record in self:
                old_state = old_states.get(record.id)
                new_state = record.state
                move = record.move_id

                estados_relevantes = ['to_send', 'sent', 'error', 'cancelled']
                if old_state != new_state and new_state in estados_relevantes:
                    _logger.warning(f"EDI cambio detectado para {move.name}: {old_state} → {new_state}")
                    move._send_invoice_webhook_notification(new_state)
                    continue

                if getattr(record, 'error', False):
                    _logger.error(f"Error detectado en OSE/SUNAT para {move.name}: {record.error}")
                    move._send_invoice_webhook_notification('error')

        return res
