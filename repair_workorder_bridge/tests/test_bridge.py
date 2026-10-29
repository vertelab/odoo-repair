# -*- coding: utf-8 -*-
# Copyright (C) 2026 Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import datetime, timedelta

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestRepairWorkOrderBridge(TransactionCase):
    """The bridge gives a repair a work order carrier and keeps the two in sync."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Repair = cls.env['repair.order']
        cls.Production = cls.env['mrp.production']

        cls.product_service = cls.env['product.product'].create({
            'name': 'Bridge Test Repair Service',
            'type': 'service',
        })
        cls.employee_a = cls.env['hr.employee'].create({'name': 'Bridge Tech A'})
        cls.employee_b = cls.env['hr.employee'].create({'name': 'Bridge Tech B'})

    def _create_repair(self, product=None):
        return self.Repair.create({
            'product_id': (product or self.product_service).id,
            'product_qty': 1.0,
        })

    def test_carrier_created_on_create(self):
        """Every repair gets a carrier manufacturing order."""
        repair = self._create_repair()
        self.assertTrue(repair.production_id, "No carrier was created")
        self.assertEqual(repair.production_id.origin, repair.name)
        self.assertEqual(repair.production_id.product_id, self.product_service)

    def test_carrier_created_when_product_set_later(self):
        """A repair created without a product gets a carrier when one is set."""
        repair = self.Repair.create({'product_qty': 1.0})
        self.assertFalse(repair.production_id)
        repair.write({'product_id': self.product_service.id})
        self.assertTrue(repair.production_id)

    def test_smart_button_both_directions(self):
        """The link is visible from both sides."""
        repair = self._create_repair()
        self.assertEqual(repair.production_id.bridge_repair_ids, repair)
        self.assertEqual(repair.production_id.bridge_repair_count, 1)

    def test_unlink_is_breakable_and_creates_no_new_carrier(self):
        """Breaking the link is deliberate: no carrier is recreated."""
        repair = self._create_repair()
        production = repair.production_id
        repair.action_unlink_production()
        self.assertFalse(repair.production_id)
        self.assertFalse(
            production.exists(),
            "The draft carrier should be removed with the link",
        )

    def test_unlink_refuses_when_no_carrier(self):
        """Breaking a link that does not exist is an error, not a no-op."""
        repair = self._create_repair()
        repair.action_unlink_production()
        with self.assertRaises(Exception):
            repair.action_unlink_production()

    def test_carrier_survives_unlink_when_not_draft(self):
        """A confirmed carrier is kept: it may hold real production."""
        repair = self._create_repair()
        production = repair.production_id
        production.action_confirm()
        repair.action_unlink_production()
        self.assertFalse(repair.production_id)
        self.assertTrue(
            production.exists(),
            "A confirmed carrier must not be deleted",
        )

    def test_technician_mirrors_to_workorder(self):
        """The assigned technician reaches the work order."""
        repair = self._create_repair(self._product_with_routing())
        workorder = repair._get_carrier_workorder()
        self.assertTrue(workorder, "No work order: the carrier has no routing")
        repair.write({'technician_id': self.employee_a.id})
        self.assertEqual(workorder.main_employee_id, self.employee_a)

    def test_planned_start_alone_keeps_duration(self):
        """Moving only the start must not leave the end behind.

        Odoo refuses a work order whose end is before its start, so writing the
        start alone would raise a message about the work order's end date --
        meaningless to someone who only changed the repair's planned start.
        """
        repair = self._create_repair(self._product_with_routing())
        workorder = repair._get_carrier_workorder()
        first = datetime(2026, 11, 2, 7, 0)
        repair.write({'planned_start': first})
        duration = workorder.date_finished - workorder.date_start
        second = datetime(2026, 11, 9, 7, 0)
        repair.write({'planned_start': second})
        self.assertEqual(workorder.date_start, second)
        self.assertEqual(workorder.date_finished, second + duration)
        # Moving the start again, now that a planned finish exists, must still
        # not leave the end behind.
        third = datetime(2026, 11, 16, 7, 0)
        repair.write({'planned_start': third})
        self.assertEqual(workorder.date_start, third)
        self.assertEqual(workorder.date_finished, third + duration)

    def test_workorder_owns_its_end_date(self):
        """The work order derives its end from the operation's duration.

        An end date written from the repair may come back different, so the
        repair mirrors the actual value instead of keeping one the work order
        never accepted.
        """
        repair = self._create_repair(self._product_with_routing())
        workorder = repair._get_carrier_workorder()
        repair.write({
            'planned_start': datetime(2026, 11, 2, 7, 0),
            'planned_finished': datetime(2026, 11, 2, 12, 0),
        })
        self.assertEqual(workorder.date_start, datetime(2026, 11, 2, 7, 0))
        self.assertEqual(
            repair.planned_finished, workorder.date_finished,
            "The repair must show the end the work order actually has",
        )

    def test_planned_dates_mirror_to_workorder(self):
        """Planned start reaches the work order and lands in a week."""
        repair = self._create_repair(self._product_with_routing())
        workorder = repair._get_carrier_workorder()
        start = datetime(2026, 11, 2, 7, 0)
        repair.write({'planned_start': start})
        self.assertEqual(workorder.date_start, start)
        self.assertTrue(
            workorder.week_id,
            "The work order should land in a week once it has a start date",
        )

    def test_workorder_changes_mirror_back_to_repair(self):
        """Planning done on the board comes back to the repair."""
        repair = self._create_repair(self._product_with_routing())
        workorder = repair._get_carrier_workorder()
        workorder.write({'main_employee_id': self.employee_b.id})
        self.assertEqual(repair.technician_id, self.employee_b)

    def test_no_infinite_recursion(self):
        """The mirror hooks must not call each other without end."""
        repair = self._create_repair(self._product_with_routing())
        workorder = repair._get_carrier_workorder()
        repair.write({'technician_id': self.employee_a.id})
        workorder.write({'main_employee_id': self.employee_b.id})
        self.assertEqual(repair.technician_id, self.employee_b)
        self.assertEqual(workorder.main_employee_id, self.employee_b)

    def test_schedule_date_is_not_mirrored(self):
        """The deadline is not the planned start (design.md Beslut 3)."""
        repair = self._create_repair(self._product_with_routing())
        workorder = repair._get_carrier_workorder()
        before = workorder.date_start
        repair.write({'schedule_date': datetime(2026, 12, 1, 12, 0)})
        self.assertEqual(
            workorder.date_start, before,
            "schedule_date is the deadline and must not move the work order",
        )

    def test_carrier_without_routing_has_no_workorder(self):
        """Without routing there is nothing to plan -- a configuration gap."""
        repair = self._create_repair(self.product_service)
        self.assertTrue(repair.production_id)
        self.assertFalse(
            repair._get_carrier_workorder(),
            "A product without a bill of materials yields no work order",
        )


    # -- status mirroring (design.md Beslut 6, interpretation C) --------

    def test_production_done_marks_repair_done(self):
        """When the work is done, the repair follows."""
        repair = self._create_repair(self._product_with_routing())
        production = repair.production_id
        production.write({'state': 'progress'})
        self.assertEqual(repair.state, 'under_repair')
        production.write({'state': 'done'})
        self.assertEqual(repair.state, 'done')

    def test_production_cancel_marks_repair_cancelled(self):
        """A cancelled carrier cancels the repair."""
        repair = self._create_repair(self._product_with_routing())
        repair.production_id.write({'state': 'cancel'})
        self.assertEqual(repair.state, 'cancel')

    def test_repair_done_does_not_close_production(self):
        """Interpretation C: closing the repair must not close the bench work.

        An open work order left behind on the week planner is exactly the
        clutter the bridge exists to avoid, so the direction is one-way.
        """
        repair = self._create_repair(self._product_with_routing())
        production = repair.production_id
        production.write({'state': 'progress'})
        repair.write({'state': 'done'})
        self.assertEqual(
            production.state, 'progress',
            "Closing the repair must not close the manufacturing order",
        )

    def test_single_workorder_done_does_not_close_repair(self):
        """One finished operation is not a finished repair.

        A carrier with several operations keeps the repair ``under_repair``
        until the manufacturing order itself moves on -- the repair follows the
        state of the order, not of one operation.
        """
        repair = self._create_repair(self._product_with_routing())
        workorder = repair._get_carrier_workorder()
        repair.production_id.write({'state': 'progress'})
        workorder.write({'state': 'done'})
        self.assertEqual(repair.state, 'under_repair')

    def test_all_workorders_done_moves_production_to_close(self):
        """When every operation is finished the order is to_close, not done."""
        repair = self._create_repair(self._product_with_routing())
        production = repair.production_id
        production.write({'state': 'progress'})
        for workorder in production.workorder_ids:
            workorder.write({'state': 'done'})
        self.assertEqual(production.state, 'to_close')
        self.assertEqual(
            repair.state, 'under_repair',
            "to_close means the work is done but the order is not closed",
        )

    def test_state_mirror_does_not_recurse(self):
        """The state hooks must not bounce between the two records."""
        repair = self._create_repair(self._product_with_routing())
        production = repair.production_id
        production.write({'state': 'progress'})
        production.write({'state': 'done'})
        self.assertEqual(repair.state, 'done')
        self.assertEqual(production.state, 'done')


    # -- remaining §9 coverage -----------------------------------------

    def test_carrier_not_created_twice(self):
        """create + write must not produce two carriers."""
        repair = self.Repair.create({'product_qty': 1.0})
        repair.write({'product_id': self.product_service.id})
        first = repair.production_id
        repair.write({'product_id': self.product_service.id})
        self.assertEqual(
            repair.production_id, first,
            "A second write must reuse the carrier, not create another",
        )
        self.assertEqual(
            self.Production.search_count([('origin', '=', repair.name)]), 1,
        )

    def test_create_production_after_unlink(self):
        """The explicit way back after breaking the link."""
        repair = self._create_repair()
        repair.action_unlink_production()
        self.assertFalse(repair.production_id)
        repair.action_create_production()
        self.assertTrue(repair.production_id)
        self.assertEqual(repair.production_id.origin, repair.name)

    def test_create_production_refuses_when_carrier_exists(self):
        """Asking for a second carrier is an error, not a duplicate."""
        repair = self._create_repair()
        with self.assertRaises(Exception):
            repair.action_create_production()

    def test_repair_without_partner_gets_carrier(self):
        """A repair without a customer is still plannable."""
        repair = self.Repair.create({
            'product_id': self.product_service.id,
            'product_qty': 1.0,
        })
        self.assertTrue(repair.production_id)
        self.assertFalse(repair.partner_id)

    def test_all_production_states_map(self):
        """Every manufacturing state maps to a repair state."""
        expected = {
            'draft': 'draft',
            'confirmed': 'confirmed',
            'progress': 'under_repair',
            'to_close': 'under_repair',
            'done': 'done',
            'cancel': 'cancel',
        }
        self.assertEqual(self.Repair.PRODUCTION_TO_REPAIR_STATE, expected)

    # -- helpers ------------------------------------------------------

    def _product_with_routing(self):
        """A product whose bill of materials has one operation."""
        workcenter = self.env['mrp.workcenter'].search([], limit=1)
        if not workcenter:
            workcenter = self.env['mrp.workcenter'].create({
                'name': 'Bridge Test Workcenter',
            })
        product = self.env['product.product'].create({
            'name': 'Bridge Test Repair With Routing',
            'type': 'service',
        })
        self.env['mrp.bom'].create({
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [],
            'operation_ids': [(0, 0, {
                'name': 'Bridge Test Operation',
                'workcenter_id': workcenter.id,
                'time_cycle_manual': 10,
            })],
        })
        return product
