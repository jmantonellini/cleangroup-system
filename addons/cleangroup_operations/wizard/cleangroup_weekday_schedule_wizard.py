# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CleanGroupWeekdayScheduleWizard(models.TransientModel):
    _name = 'cleangroup.weekday.schedule.wizard'
    _description = 'Asistente para Horarios de Lunes a Viernes'

    location_id = fields.Many2one(
        'cleangroup.location',
        string='Ubicación',
        required=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
    )
    start_time = fields.Float(
        string='Hora Inicio',
        required=True,
    )
    end_time = fields.Float(
        string='Hora Fin',
        required=True,
    )

    @api.constrains('start_time', 'end_time')
    def _check_time_range(self):
        for wizard in self:
            if wizard.end_time <= wizard.start_time:
                raise UserError(_('La hora de fin debe ser posterior a la hora de inicio.'))

    def action_apply(self):
        self.ensure_one()
        schedule_model = self.env['cleangroup.employee.schedule']
        for day in ('monday', 'tuesday', 'wednesday', 'thursday', 'friday'):
            schedules = schedule_model.search([
                ('location_id', '=', self.location_id.id),
                ('employee_id', '=', self.employee_id.id),
                ('day_of_week', '=', day),
            ])
            values = {
                'location_id': self.location_id.id,
                'employee_id': self.employee_id.id,
                'day_of_week': day,
                'start_time': self.start_time,
                'end_time': self.end_time,
                'active': True,
            }
            if schedules:
                schedules.write(values)
            else:
                schedule_model.create(values)

        return {'type': 'ir.actions.act_window_close'}