# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CleanGroupSupplyOrder(models.Model):
    _name = 'cleangroup.supply.order'
    _description = 'Orden de Insumos'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'
    _check_company_auto = True

    name = fields.Char(string='Referencia', required=True, copy=False, default='Nuevo', readonly=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('done', 'Entregada'),
        ('cancelled', 'Cancelada'),
    ], string='Estado', default='draft', tracking=True)

    location_id = fields.Many2one(
        'cleangroup.location',
        string='Ubicación',
        required=True,
        tracking=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        related='location_id.partner_id',
        store=True,
        readonly=True
    )

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Depósito Origen',
        related='location_id.warehouse_id',
        store=True,
        readonly=True,
        check_company=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        related='location_id.company_id',
        store=True,
        readonly=True,
    )

    supervisor_id = fields.Many2one(
        'res.users',
        string='Supervisor',
        default=lambda self: self.env.user,
        required=True
    )

    date = fields.Date(string='Fecha de Orden', default=fields.Date.today, required=True)

    line_ids = fields.One2many(
        'cleangroup.supply.order.line',
        'order_id',
        string='Líneas de Orden'
    )

    available_product_ids = fields.Many2many(
        'product.product',
        compute='_compute_available_products',
        string='Productos Disponibles'
    )

    stock_picking_id = fields.Many2one(
        'stock.picking',
        string='Movimiento de Stock',
        readonly=True,
        copy=False
    )

    notes = fields.Text(string='Notas Internas')
    total_items = fields.Integer(compute='_compute_totals', string='Total de Ítems')

    # Firma digital y prueba de entrega
    signature = fields.Binary(string='Firma Digital', attachment=True)
    delivery_photo = fields.Binary(string='Foto de Entrega', attachment=True)
    delivery_notes = fields.Text(string='Notas de Entrega')
    confirmed_date = fields.Datetime(string='Entrega Confirmada El', readonly=True)

    @api.depends('line_ids.quantity')
    def _compute_totals(self):
        for order in self:
            order.total_items = sum(order.line_ids.mapped('quantity'))

    @api.depends('warehouse_id')
    def _compute_available_products(self):
        for order in self:
            if order.warehouse_id:
                quants = self.env['stock.quant'].read_group(
                    [('location_id', '=', order.warehouse_id.lot_stock_id.id), ('quantity', '>', 0)],
                    ['product_id'], ['product_id']
                )
                product_ids = [q['product_id'][0] for q in quants if q['product_id']]
                order.available_product_ids = product_ids if product_ids else False
            else:
                order.available_product_ids = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('cleangroup.supply.order') or 'Nuevo'
        return super(CleanGroupSupplyOrder, self).create(vals_list)

    def action_confirm(self):
        """El supervisor envía la orden. Crea el picking en borrador."""
        for order in self:
            if not order.line_ids:
                raise UserError(_('No se puede confirmar una orden sin líneas.'))
            order._create_stock_picking()
            order.state = 'confirmed'

    def action_open_delivery_wizard(self):
        """Abre asistente para capturar firma y confirmar entrega."""
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_('Solo órdenes confirmadas pueden ser entregadas.'))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Confirmar Entrega',
            'res_model': 'cleangroup.delivery.confirmation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def action_cancel(self):
        for order in self:
            if order.stock_picking_id and order.stock_picking_id.state == 'done':
                raise UserError(_('No se puede cancelar una orden con un movimiento de stock validado.'))
            if order.stock_picking_id:
                order.stock_picking_id.action_cancel()
            order.state = 'cancelled'

    def action_draft(self):
        for order in self:
            if order.stock_picking_id and order.stock_picking_id.state != 'cancel':
                order.stock_picking_id.action_cancel()
            order.write({
                'state': 'draft',
                'signature': False,
                'delivery_photo': False,
                'delivery_notes': False,
                'confirmed_date': False,
            })

    def _create_stock_picking(self):
        self.ensure_one()
        warehouse = self.warehouse_id
        company = warehouse.company_id if warehouse else self.company_id
        if not warehouse or not company:
            raise UserError(_('La ubicación de la orden debe tener un depósito y una empresa configurados.'))
        picking_type = warehouse.out_type_id
        if not picking_type:
            raise UserError(_('El depósito %s no tiene un tipo de operación de salida configurado.') % warehouse.name)

        incompatible_records = []
        if warehouse.company_id != company:
            incompatible_records.append(_('el depósito'))
        if warehouse.lot_stock_id.company_id != company:
            incompatible_records.append(_('la ubicación de origen'))
        if picking_type.company_id != company:
            incompatible_records.append(_('el tipo de operación de salida'))
        if incompatible_records:
            raise UserError(_(
                'El depósito %(warehouse)s está configurado para la empresa %(company)s, '
                'pero %(records)s pertenecen a otra empresa. Configure el almacén, '
                'la ubicación de origen y el tipo de operación dentro de la misma empresa.'
            ) % {
                'warehouse': warehouse.display_name,
                'company': company.display_name,
                'records': ', '.join(incompatible_records),
            })

        partner_loc = self.env.ref('stock.stock_location_customers')

        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': partner_loc.id,
            'company_id': company.id,
            'origin': self.name,
            'move_ids': [],
        }

        move_vals = []
        for line in self.line_ids:
            move_vals.append((0, 0, {
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': partner_loc.id,
            }))

        picking_vals['move_ids'] = move_vals
        picking = self.env['stock.picking'].with_company(company).create(picking_vals)
        self.stock_picking_id = picking
        return picking

    def action_view_picking(self):
        self.ensure_one()
        if not self.stock_picking_id:
            raise UserError(_('Aún no se ha creado un movimiento de stock.'))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Movimiento de Stock',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.stock_picking_id.id,
        }

    def action_open_from_dashboard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Orden de Insumos',
            'res_model': 'cleangroup.supply.order',
            'view_mode': 'form',
            'views': [(self.env.ref('cleangroup_operations.view_cleangroup_supply_order_form').id, 'form')],
            'res_id': self.id,
            'target': 'new',
        }

    def action_print_remito(self):
        """Imprime el Remito en PDF."""
        self.ensure_one()
        return self.env.ref('cleangroup_operations.action_report_remito').report_action(self)


class CleanGroupSupplyOrderLine(models.Model):
    _name = 'cleangroup.supply.order.line'
    _description = 'Línea de Orden de Insumos'

    order_id = fields.Many2one('cleangroup.supply.order', string='Orden', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    quantity = fields.Float(string='Cantidad', required=True, default=1.0)
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unidad de Medida',
        related='product_id.uom_id',
        store=True,
        readonly=True
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
