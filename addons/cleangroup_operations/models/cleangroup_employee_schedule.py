# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CleanGroupEmployeeSchedule(models.Model):
    _name = 'cleangroup.employee.schedule'
    _description = 'Horario de Empleado por Ubicación'
    _order = 'day_of_week_sort, start_time'

    location_id = fields.Many2one(
        'cleangroup.location',
        string='Ubicación',
        required=True,
        ondelete='cascade'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        related='location_id.partner_id',
        store=True,
        readonly=True,
    )

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)

    day_of_week = fields.Selection([
        ('monday', 'Lunes'),
        ('tuesday', 'Martes'),
        ('wednesday', 'Miércoles'),
        ('thursday', 'Jueves'),
        ('friday', 'Viernes'),
        ('saturday', 'Sábado'),
        ('sunday', 'Domingo'),
    ], string='Día de la Semana', required=True)

    day_of_week_sort = fields.Integer(
        string='Orden del Día',
        compute='_compute_day_of_week_sort',
        store=True,
    )

    start_time = fields.Float(string='Hora Inicio', required=True, help='Formato 24h (ej. 8.5 = 08:30)')
    end_time = fields.Float(string='Hora Fin', required=True, help='Formato 24h (ej. 17.0 = 17:00)')
    active = fields.Boolean(string='Activo', default=True)

    schedule_display = fields.Char(string='Horario', compute='_compute_schedule_display')

    @api.depends('day_of_week')
    def _compute_day_of_week_sort(self):
        spanish_day_order = {
            'monday': 1,
            'tuesday': 2,
            'wednesday': 3,
            'thursday': 4,
            'friday': 5,
            'saturday': 6,
            'sunday': 7,
        }
        for rec in self:
            rec.day_of_week_sort = spanish_day_order.get(rec.day_of_week, 99)

    @api.depends('day_of_week', 'start_time', 'end_time', 'employee_id')
    def _compute_schedule_display(self):
        for rec in self:
            start = '%02d:%02d' % (int(rec.start_time), int((rec.start_time % 1) * 60))
            end = '%02d:%02d' % (int(rec.end_time), int((rec.end_time % 1) * 60))
            rec.schedule_display = f"{rec.employee_id.name} | {dict(self._fields['day_of_week'].selection).get(rec.day_of_week)} {start}-{end}"
