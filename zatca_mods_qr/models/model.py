import json

from odoo import api, fields, models, _
from base64 import b64decode, b64encode
from lxml import etree


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('amount_total_signed', 'amount_tax_signed', 'l10n_sa_confirmation_datetime', 'company_id',
                 'company_id.vat', 'journal_id', 'journal_id.l10n_sa_production_csid_json',
                 'l10n_sa_invoice_signature', 'l10n_sa_chain_index')
    def _compute_qr_code_str(self):
        """ Override to update QR code generation in accordance with ZATCA Phase 2"""
        for move in self:
            move.l10n_sa_qr_code_str = ''
            if move.country_code == 'SA' and move.move_type in (
                    'out_invoice', 'out_refund') and move.l10n_sa_chain_index:
                edi_format = self.env.ref('l10n_sa_edi.edi_sa_zatca')
                zatca_document = move.edi_document_ids.filtered(lambda d: d.edi_format_id == edi_format)
                if move._l10n_sa_is_simplified():
                    x509_cert = json.loads(move.journal_id.l10n_sa_production_csid_json)['binarySecurityToken']
                    xml_content = self.env.ref('l10n_sa_edi.edi_sa_zatca')._l10n_sa_generate_zatca_template(move)
                    qr_code_str = move._l10n_sa_get_qr_code(move.journal_id, xml_content, b64decode(x509_cert),
                                                            move.l10n_sa_invoice_signature,
                                                            move._l10n_sa_is_simplified())
                    print(qr_code_str, 'qr_code_str___2', b64encode(qr_code_str).decode())
                    move.l10n_sa_qr_code_str = b64encode(qr_code_str).decode()
                elif zatca_document.state == 'sent' and zatca_document.attachment_id.datas:
                    document_xml = zatca_document.attachment_id.with_context(bin_size=False).datas.decode()
                    root = etree.fromstring(b64decode(document_xml))
                    qr_node = root.xpath('//*[local-name()="ID"][text()="QR"]/following-sibling::*/*')[0]
                    move.l10n_sa_qr_code_str = qr_node.text
