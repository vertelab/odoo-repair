A repair order is planned through a manufacturing order. The bridge creates
that manufacturing order automatically, but it needs two things from you: a
product that can be manufactured, and a routing.

## The product

Use a product of type **Service**. A service product carries no stock and no
valuation, so the carrier leaves the inventory untouched — verified: a
manufacturing order for a service product with a component-less bill of
materials creates no `stock.valuation.layer`.

A storable product works too, but then the manufacturing order produces stock
you probably did not want.

## The bill of materials

Attach a bill of materials of type **Normal** to the product, with
**exactly one operation**:

1. Open the product and go to *Bill of Materials*.
2. Create one, type *Normal*.
3. Add a single operation on the *Operations* tab: a name, a work center and a
   duration. This is the operation the week planner will show.

Without an operation the manufacturing order gets no work order, and the repair
is invisible in the week planner. The bridge does not create a routing for you —
a repair that silently invents its own operation would be worse than one that
refuses to appear.

### Leave the components empty

**Do not put components on the bill of materials.** The repair order already
owns its material: the repairer adds lines on the *Parts* tab, and
`action_repair_done()` consumes them.

If the bill of materials also carries components, the same material is consumed
twice. Reproduced: a repair with 1.0 leather on its own lines, against a bill of
materials needing 0.7 leather and 0.1 glue, gives a leather consumption of 1.7
for a single repair — 1.0 from the repair and 0.7 from the manufacturing order.

A component-less bill of materials gives exactly one source of consumption: the
repair order.

## The work center

Any work center will do. The work order inherits it, and the Gantt view groups
on it, so pick the one that represents where repairs actually happen.

## Verify the setup

Create a repair order for the product. A smart button labelled *Work Order
Carrier* should appear, pointing at a manufacturing order with one work order.
Schedule it — set *Planned Start* — and the work order should appear in the week
planner under that week.

## Planning past the promised date

A repair carries two dates that mean different things:

| Field | Means |
|-------|-------|
| *Scheduled Date* (`schedule_date`) | when the customer was told the work would be done |
| *Planned Start* / *Planned Finish* | when the workshop intends to do it |

Nothing forces the two to agree, so a repair could be planned weeks past its
promise without anyone noticing. It cannot any more: saving a plan that
finishes after the scheduled date is refused, and the message says how late the
plan is.

The way forward is the **Plan Past Scheduled Date** button in the repair's
header. It opens a dialog that states the delay in days and hours; confirming
saves the plan, cancelling leaves the repair untouched. The button only appears
when the repair actually is late.

Planning late is allowed, and sometimes right — parts arrive late, the customer
agrees to wait. The point is that it has to be a decision. A yellow banner can
be clicked away without being read.

The same message appears in the form as soon as a planned finish past the
scheduled date is entered, so nobody fills in a form only to be refused at the
end.

### If you do not want the question

The check is a guard in `repair.order.write()`. It does not fire when the work
order mirrors back the dates it actually accepted — that is bookkeeping, not a
planning decision — so the mirror keeps working regardless.
