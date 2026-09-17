# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    cleangroup_schedule_ids = fields.One2many(
        'cleangroup.employee.schedule',
        'employee_id',
        string='Horarios CleanGroup',
    )

    cleangroup_client_ids = fields.Many2many(
        'res.partner',
        string='Clientes CleanGroup',
        compute='_compute_cleangroup_overview',
    )

    cleangroup_schedule_summary = fields.Char(
        string='Resumen de horarios',
        compute='_compute_cleangroup_overview',
    )

    @api.depends(
        'cleangroup_schedule_ids.partner_id',
        'cleangroup_schedule_ids.location_id',
        'cleangroup_schedule_ids.day_of_week',
        'cleangroup_schedule_ids.start_time',
        'cleangroup_schedule_ids.end_time',
        'cleangroup_schedule_ids.active',
    )
    def _compute_cleangroup_overview(self):
        day_names = dict(
            self.env['cleangroup.employee.schedule']._fields['day_of_week'].selection
        )
        for employee in self:
            schedules = employee.cleangroup_schedule_ids.filtered('active')
            employee.cleangroup_client_ids = schedules.mapped('partner_id')
            summary = []
            for schedule in schedules:
                start = '%02d:%02d' % (int(schedule.start_time), int((schedule.start_time % 1) * 60))
                end = '%02d:%02d' % (int(schedule.end_time), int((schedule.end_time % 1) * 60))
                client = schedule.partner_id.name or schedule.location_id.name
                summary.append('%s: %s %s-%s' % (
                    client,
                    day_names.get(schedule.day_of_week, schedule.day_of_week),
                    start,
                    end,
                ))
            employee.cleangroup_schedule_summary = ' | '.join(summary)

    # Custom fields for CleanGroup employee management
    x_zona = fields.Char(string='Zona')
    x_hs_semanales = fields.Char(string='Horas Semanales')
    x_convenio = fields.Char(string='Convenio')
    x_categoria = fields.Char(string='Categoría')
    x_fecha_ingreso = fields.Date(string='Fecha de Ingreso')
    x_fecha_reclutamiento = fields.Date(string='Fecha de Reclutamiento')
    x_fecha_baja = fields.Date(string='Fecha de Baja')
    x_motivo_baja = fields.Text(string='Motivo de Baja')
    x_notas = fields.Text(string='Notas')

    @api.constrains('x_fecha_baja', 'x_motivo_baja')
    def _check_offboarding_reason(self):
        for employee in self:
            if employee.x_fecha_baja and not employee.x_motivo_baja:
                raise ValidationError(_('El motivo de baja es obligatorio cuando se informa una fecha de baja.'))

    def action_add_weekday_schedule(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Agregar Horario Lunes a Viernes',
            'res_model': 'cleangroup.weekday.schedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_employee_id': self.id},
        }
