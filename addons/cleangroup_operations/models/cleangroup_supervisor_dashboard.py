# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CleanGroupSupervisorDashboard(models.TransientModel):
    _name = 'cleangroup.supervisor.dashboard'
    _description = 'Panel del Supervisor'
    _rec_name = 'display_name'

    user_id = fields.Many2one('res.users', string='Supervisor', default=lambda self: self.env.user)
    display_name = fields.Char(string='Nombre', compute='_compute_display_name')

    active_order_ids = fields.Many2many(
        'cleangroup.supply.order',
        compute='_compute_active_orders',
        string='Órdenes Activas'
    )

    location_ids = fields.Many2many(
        'cleangroup.location',
        compute='_compute_locations',
        string='Mis Ubicaciones'
    )

    sede_location_ids = fields.Many2many(
        'cleangroup.location',
        compute='_compute_locations',
        string='Todas las Ubicaciones de mi Sede',
    )

    @api.depends('user_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = 'Panel del Supervisor'

    @api.depends('user_id')
    def _compute_active_orders(self):
        for rec in self:
            rec.active_order_ids = self.env['cleangroup.supply.order'].search([
                ('supervisor_id', '=', rec.user_id.id),
                ('state', 'in', ['draft', 'confirmed'])
            ], order='date desc')

    @api.depends('user_id')
    def _compute_locations(self):
        for rec in self:
            assigned_locations = self.env['cleangroup.location'].search([
                ('supervisor_ids', 'in', [rec.user_id.id]),
                ('active', '=', True)
            ], order='name')
            rec.location_ids = assigned_locations
            rec.sede_location_ids = self.env['cleangroup.location'].search([
                ('warehouse_id', 'in', assigned_locations.mapped('warehouse_id').ids),
                ('active', '=', True),
            ], order='name')

    def action_refresh(self):
        return {'type': 'ir.actions.act_window_close'}
