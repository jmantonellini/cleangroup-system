# -*- coding: utf-8 -*-
from urllib.parse import quote

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CleanGroupLocation(models.Model):
    _name = 'cleangroup.location'
    _description = 'Ubicación de Operación'
    _inherit = ['mail.thread']
    _order = 'name'
    _check_company_auto = True

    name = fields.Char(string='Nombre de Ubicación', required=True, tracking=True)
    active = fields.Boolean(string='Activo', default=True)

    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        help='Enlace a un cliente existente en Odoo',
        tracking=True
    )

    street = fields.Char(string='Calle')
    street2 = fields.Char(string='Calle 2')
    city = fields.Char(string='Ciudad')
    state_id = fields.Many2one('res.country.state', string='Provincia/Estado')
    zip = fields.Char(string='Código Postal')
    country_id = fields.Many2one('res.country', string='País')

    latitude = fields.Float(string='Latitud', digits=(10, 7))
    longitude = fields.Float(string='Longitud', digits=(10, 7))

    google_maps_url = fields.Char(
        string='Google Maps',
        compute='_compute_google_maps_url',
    )

    supervisor_ids = fields.Many2many(
        'res.users',
        'cleangroup_location_supervisor_rel',
        'location_id', 'user_id',
        string='Supervisores',
        help='Usuarios que pueden gestionar órdenes de insumos para esta ubicación'
    )

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Depósito Origen',
        required=True,
        help='Depósito desde el cual se descontarán los insumos'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        related='warehouse_id.company_id',
        store=True,
        readonly=True,
    )

    employee_schedule_ids = fields.One2many(
        'cleangroup.employee.schedule',
        'location_id',
        string='Horarios de Empleados'
    )

    supply_order_ids = fields.One2many(
        'cleangroup.supply.order',
        'location_id',
        string='Órdenes de Insumos'
    )

    order_count = fields.Integer(string='Cant. Órdenes', compute='_compute_order_count')
    today_employee_count = fields.Integer(string='Empleados Hoy', compute='_compute_today_employees')

    @api.constrains('warehouse_id')
    def _check_warehouse_configuration(self):
        for location in self:
            warehouse = location.warehouse_id
            if not warehouse:
                continue
            company = warehouse.company_id
            invalid_records = []
            if warehouse.lot_stock_id.company_id != company:
                invalid_records.append(_('la ubicación de existencias'))
            if warehouse.out_type_id.company_id != company:
                invalid_records.append(_('el tipo de operación de salida'))
            if invalid_records:
                raise ValidationError(_(
                    'El depósito %(warehouse)s no está configurado correctamente para '
                    'la empresa %(company)s: %(records)s deben pertenecer a la misma empresa.'
                ) % {
                    'warehouse': warehouse.display_name,
                    'company': company.display_name,
                    'records': ', '.join(invalid_records),
                })

    @api.depends('supply_order_ids')
    def _compute_order_count(self):
        for loc in self:
            loc.order_count = len(loc.supply_order_ids)

    @api.depends('employee_schedule_ids')
    def _compute_today_employees(self):
        import datetime
        dias = {
            'monday': 'lunes', 'tuesday': 'martes', 'wednesday': 'miércoles',
            'thursday': 'jueves', 'friday': 'viernes', 'saturday': 'sábado', 'sunday': 'domingo'
        }
        today_name = datetime.datetime.now().strftime('%A').lower()
        for loc in self:
            loc.today_employee_count = self.env['cleangroup.employee.schedule'].search_count([
                ('location_id', '=', loc.id),
                ('day_of_week', '=', today_name)
            ])

    @api.depends('latitude', 'longitude', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id')
    def _compute_google_maps_url(self):
        for location in self:
            if location.latitude and location.longitude:
                destination = '%s,%s' % (location.latitude, location.longitude)
            else:
                address_parts = [
                    location.street,
                    location.street2,
                    location.city,
                    location.state_id.name,
                    location.zip,
                    location.country_id.name,
                ]
                destination = ', '.join(part for part in address_parts if part)
            location.google_maps_url = (
                'https://www.google.com/maps/search/?api=1&query=%s' % quote(destination)
                if destination else False
            )

    def action_open_google_maps(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.google_maps_url,
            'target': 'new',
        }

    def action_view_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Órdenes de Insumos',
            'res_model': 'cleangroup.supply.order',
            'view_mode': 'list,form',
            'domain': [('location_id', '=', self.id)],
            'context': {'default_location_id': self.id, 'default_partner_id': self.partner_id.id},
        }

    def action_create_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nueva Orden de Insumos',
            'res_model': 'cleangroup.supply.order',
            'view_mode': 'form',
            'context': {
                'default_location_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_warehouse_id': self.warehouse_id.id,
            },
        }

    def action_add_weekday_schedule(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Agregar Horario Lunes a Viernes',
            'res_model': 'cleangroup.weekday.schedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_location_id': self.id},
        }


class ResUsers(models.Model):
    _inherit = 'res.users'

    cleangroup_warehouse_ids = fields.Many2many(
        'stock.warehouse',
        compute='_compute_cleangroup_warehouse_ids',
        string='Sedes CleanGroup',
    )

    def _compute_cleangroup_warehouse_ids(self):
        locations = self.env['cleangroup.location'].sudo().search([
            ('supervisor_ids', 'in', self.ids),
        ])
        warehouses_by_user = {
            user_id: locations.filtered(lambda location: user_id in location.supervisor_ids.ids).mapped('warehouse_id')
            for user_id in self.ids
        }
        for user in self:
            user.cleangroup_warehouse_ids = warehouses_by_user.get(user.id, self.env['stock.warehouse'])
