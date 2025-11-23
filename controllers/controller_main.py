# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class InvoicePDFPublicController(http.Controller):

    @http.route('/public/invoice/pdf/<int:invoice_id>/<string:token>', type='http', auth='none', methods=['GET'])
    def download_invoice_pdf(self, invoice_id, token):
        expected_token = request.env['ir.config_parameter'].sudo().get_param('invoice_webhook.token')
        if token != expected_token:
            _logger.warning("Token inválido al intentar descargar factura.")
            return request.not_found()

        invoice = request.env['account.move'].sudo().browse(invoice_id)
        if not invoice.exists():
            _logger.warning(f"Factura con ID {invoice_id} no encontrada.")
            return request.not_found()

        try:
            report = request.env['ir.actions.report']._get_report_from_name('account.report_invoice')
            if not report:
                _logger.error("No se encontró el reporte")
                return request.make_response("Reporte no encontrado.", [('Content-Type', 'text/plain')])

            admin_env = request.env(user=2)
            pdf_content, content_type = admin_env['ir.actions.report']._render_qweb_pdf(
                #'account.report_invoice', [invoice.id]
                'account.report_invoice_with_payments', [invoice.id]
            )

            return request.make_response(
                pdf_content,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'inline; filename=\"{invoice.name}.pdf\"'),
                ],
            )

        except Exception as e:
            _logger.error(f"Error generando PDF para {invoice.name}: {e}")
            return request.make_response(str(e), [('Content-Type', 'text/plain')])
