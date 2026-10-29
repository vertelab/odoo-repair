# -*- coding: utf-8 -*-
# Copyright (C) 2026 Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class RepairLateConfirm(models.TransientModel):
    """Ask before a plan is allowed to run past the promised date.

    ``planned_finished`` is when the work will be done; ``schedule_date`` is
    when the customer was told it would be. Planning past the promise is
    sometimes the only option -- parts arrive late, the customer agrees to wait
    -- but it must never happen by accident.

    So the write is held back and this wizard asks. Confirming releases it;
    cancelling leaves the repair untouched. The flow is broken on purpose: a
    warning the planner can click away without reading is not a decision.
    """

    _name = 'repair.late.confirm'
    _description = 'Planned Later Than Promised'

    repair_id = fields.Many2one(
        'repair.order', string='Repair', required=True, ondelete='cascade',
    )
    schedule_date = fields.Datetime(
        string='Scheduled Date', related='repair_id.schedule_date',
        readonly=True,
    )
    late_days = fields.Float(
        string='Days Late', related='repair_id.late_days', readonly=True,
    )
    message = fields.Text(
        string='Consequence', compute='_compute_message',
    )

    # The values the caller was trying to write. Only the planning fields are
    # carried: they are the ones the guard holds back, and repeating the whole
    # write here would risk applying something the planner never saw.
    planned_start = fields.Datetime(string='Planned Start')
    planned_finished = fields.Datetime(string='Planned Finish')
    technician_id = fields.Many2one('hr.employee', string='Assigned Technician')

    @api.depends('repair_id', 'planned_start', 'planned_finished')
    def _compute_message(self):
        """Describe the delay from the values in the wizard, not from the
        repair.

        The repair still holds the old plan -- that is the whole point of
        asking first -- so asking it would describe a delay that has not been
        applied yet.
        """
        for wizard in self:
            if not (wizard.repair_id and wizard.planned_finished):
                wizard.message = ''
                continue
            simulated = wizard.repair_id.new({
                'planned_start': wizard.planned_start,
                'planned_finished': wizard.planned_finished,
                'schedule_date': wizard.repair_id.schedule_date,
            })
            wizard.message = simulated._late_message() or ''

    def action_confirm(self):
        """Apply the held-back write and let the flow continue."""
        self.ensure_one()
        values = {}
        if self.planned_start:
            values['planned_start'] = self.planned_start
        if self.planned_finished:
            values['planned_finished'] = self.planned_finished
        if self.technician_id:
            values['technician_id'] = self.technician_id.id
        if values:
            # ``late_confirmed`` tells the guard in ``write`` that the planner
            # has seen the question and said yes.
            self.repair_id.with_context(late_confirmed=True).write(values)
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        """Leave the repair as it was."""
        return {'type': 'ir.actions.act_window_close'}
