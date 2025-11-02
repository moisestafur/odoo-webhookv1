# -*- coding: utf-8 -*-
from odoo import models, api
import requests
import logging
import time

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def write(self, vals):
        """
        Detecta cambios en el estado EDI (edi_state) y envía un webhook
        cuando la factura cambia a 'sent', 'error' o 'cancelled'.
        """
        _logger.warning(f"write() interceptado en {self.name}, vals={vals}")
        old_states = {m.id: m.edi_state for m in self}
        res = super(AccountMove, self).write(vals)

        if 'edi_state' in vals:
            for record in self:
                old_state = old_states.get(record.id)
                new_state = record.edi_state
                if old_state != new_state and new_state in ['sent', 'error', 'cancelled']:
                    _logger.info(f"Cambio de estado EDI en {record.name}: {old_state} → {new_state}")
                    record._send_invoice_webhook_notification(new_state)
        return res

    def _send_invoice_webhook_notification(self, estado):
        url = self.env['ir.config_parameter'].sudo().get_param('invoice_webhook.url')
        token = self.env['ir.config_parameter'].sudo().get_param('invoice_webhook.token')

        if not url:
            _logger.warning("No se encontró el parámetro del sistema 'invoice_webhook.url'.")
            return
        # Token personalizado
        headers = {
            "Content-Type": "application/json",
        }
        if token:
            headers["X-Odoo-Token"] = token
            
        for record in self:
            payload = {
                "invoice_number": record.name,
                "partner_name": record.partner_id.name,
                "amount_total": record.amount_total,
                "currency": record.currency_id.name,
                "invoice_date": record.invoice_date.strftime("%Y-%m-%d") if record.invoice_date else None,
                "state": record.state,
                "edi_state": estado,
            }
            
            _logger.info(f"Enviando webhook a {url} con payload: {payload}")

            for intento in range(3):
                try:
                    response = requests.post(url, json=payload, headers=headers, timeout=5)
                    if response.ok:
                        mensaje = ""
                        if estado == "sent":
                            mensaje = "Factura enviada y validada correctamente por SUNAT."
                        elif estado == "to_send":
                            mensaje = "Factura pendiente de envío a SUNAT."
                        elif estado == "error":
                            mensaje = "Error en validación con SUNAT/OSE."
                        elif estado == "cancelled":
                            mensaje = "Factura cancelada en SUNAT."

                        _logger.info(mensaje)
                        record.message_post(body=f"{mensaje} (intento {intento+1}).")
                        break

                except requests.exceptions.RequestException as e:
                    _logger.error(f"Error al enviar webhook (intento {intento+1}): {str(e)}")
                    time.sleep(2)