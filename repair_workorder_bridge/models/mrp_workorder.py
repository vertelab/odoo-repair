# -*- coding: utf-8 -*-
# Copyright (C) 2026 Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models

from .repair_order import SKIP_SYNC


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    repair_ids = fields.Many2many(
        'repair.order', string='Repairs',
        compute='_compute_repair_ids',
        help="Repairs carried by this work order's manufacturing order.",
    )

    def _compute_repair_ids(self):
        for workorder in self:
            workorder.repair_ids = workorder.production_id.bridge_repair_ids

    def write(self, vals):
        """Mirror planning changes back onto the repair.

        The week planner and the assignment board write ``date_start``,
        ``date_finished`` and ``main_employee_id`` on the work order. Without
        this hook the repair would keep stale planning values and the two
        would drift apart -- the exact failure the bridge exists to prevent.

        ``state`` is mirrored too, in this direction only (design.md Beslut 6,
        interpretation C): when the work is finished, the repair follows. The
        opposite direction is deliberately not wired -- closing the repair must
        not close the bench work.
        """
        res = super().write(vals)
        if self.env.context.get(SKIP_SYNC):
            return res
        planning_fields = {'date_start', 'date_finished', 'main_employee_id'}
        if planning_fields & set(vals):
            for workorder in self:
                workorder.production_id.bridge_repair_ids._sync_from_workorder()
        if 'state' in vals:
            for workorder in self:
                workorder.production_id.bridge_repair_ids._sync_state_from_production()
        return res
