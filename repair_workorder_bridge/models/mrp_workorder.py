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
            workorder.repair_ids = workorder.production_id.repair_order_ids

    def write(self, vals):
        """Mirror planning changes back onto the repair.

        The week planner and the assignment board write ``date_start``,
        ``date_finished`` and ``main_employee_id`` on the work order. Without
        this hook the repair would keep stale planning values and the two
        would drift apart -- the exact failure the bridge exists to prevent.
        """
        res = super().write(vals)
        planning_fields = {'date_start', 'date_finished', 'main_employee_id'}
        if planning_fields & set(vals) and not self.env.context.get(SKIP_SYNC):
            for workorder in self:
                workorder.production_id.repair_order_ids._sync_from_workorder()
        return res
