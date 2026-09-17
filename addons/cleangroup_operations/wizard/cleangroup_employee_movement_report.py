# -*- coding: utf-8 -*-
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CleanGroupEmployeeMovementReport(models.TransientModel):
    _name = 'cleangroup.employee.movement.report'
    _description = 'Reporte de Altas y Bajas de Empleados'

    company_id = fields.Many2one(
        'res.company',
        string='Sede',
        required=True,
        readonly=True,
        default=lambda self: self._default_company(),
    )
    movement_type = fields.Selection([
        ('hire', 'Altas'),
        ('offboarding', 'Bajas'),
        ('both', 'Altas y bajas'),
    ], string='Mostrar', required=True, default='both')
    date_from = fields.Date(
        string='Desde',
        required=True,
        default=lambda self: date.today().replace(day=1),
    )
    date_to = fields.Date(
        string='Hasta',
        required=True,
        default=fields.Date.context_today,
    )
    hire_count = fields.Integer(string='Altas', readonly=True)
    offboarding_count = fields.Integer(string='Bajas', readonly=True)
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Empleados encontrados',
        readonly=True,
    )

    @api.model
    def _default_company(self):
        employee = self.env['hr.employee'].search([
            ('user_id', '=', self.env.uid),
        ], limit=1)
        return employee.company_id or self.env.company

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for report in self:
            if report.date_from and report.date_to and report.date_from > report.date_to:
                raise UserError(_('La fecha Desde no puede ser posterior a la fecha Hasta.'))

    def action_generate_report(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_('La fecha Desde no puede ser posterior a la fecha Hasta.'))

        employee_model = self.env['hr.employee']
        common_domain = [('company_id', '=', self.company_id.id)]
        hire_domain = common_domain + [
            ('x_fecha_ingreso', '>=', self.date_from),
            ('x_fecha_ingreso', '<=', self.date_to),
        ]
        offboarding_domain = common_domain + [
            ('x_fecha_baja', '>=', self.date_from),
            ('x_fecha_baja', '<=', self.date_to),
        ]
        hires = employee_model.search(hire_domain, order='x_fecha_ingreso, name')
        offboardings = employee_model.search(offboarding_domain, order='x_fecha_baja, name')

        if self.movement_type == 'hire':
            employees = hires
        elif self.movement_type == 'offboarding':
            employees = offboardings
        else:
            employees = hires | offboardings

        self.write({
            'hire_count': len(hires) if self.movement_type in ('hire', 'both') else 0,
            'offboarding_count': len(offboardings) if self.movement_type in ('offboarding', 'both') else 0,
            'employee_ids': [(6, 0, employees.ids)],
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reporte de Altas y Bajas'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
