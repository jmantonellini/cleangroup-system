# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CleanGroupDeliveryWizard(models.TransientModel):
    _name = 'cleangroup.delivery.confirmation.wizard'
    _description = 'Asistente de Confirmación de Entrega'

    order_id = fields.Many2one('cleangroup.supply.order', string='Orden', required=True)
    signature = fields.Binary(string='Firma Digital', required=True, attachment=True)
    delivery_photo = fields.Binary(string='Foto de Entrega', attachment=True)
    delivery_notes = fields.Text(string='Notas de Entrega')

    @staticmethod
    def _normalize_binary_value(value):
        if not isinstance(value, str):
            return value
        if value.startswith('data:') and ',' in value:
            value = value.split(',', 1)[1]
        value = ''.join(value.split())
        if len(value) % 4 == 1:
            raise UserError(_('La firma digital no tiene un formato válido.'))
        return value + '=' * ((4 - len(value) % 4) % 4)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            for field_name in ('signature', 'delivery_photo'):
                if field_name in vals:
                    vals[field_name] = self._normalize_binary_value(vals[field_name])
        return super().create(vals_list)

    def action_confirm_delivery(self):
        self.ensure_one()
        if not self.signature:
            raise UserError(_('La firma digital es obligatoria para confirmar la entrega.'))

        order = self.order_id
        order.write({
            'signature': self.signature,
            'delivery_photo': self.delivery_photo,
            'delivery_notes': self.delivery_notes,
            'state': 'done',
            'confirmed_date': fields.Datetime.now(),
        })

        # Valida el picking y descuenta el inventario
        if order.stock_picking_id:
            if order.stock_picking_id.state == 'draft':
                order.stock_picking_id.action_confirm()
            for move in order.stock_picking_id.move_ids:
                move.quantity = move.product_uom_qty
            order.stock_picking_id.button_validate()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cleangroup.supply.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }
