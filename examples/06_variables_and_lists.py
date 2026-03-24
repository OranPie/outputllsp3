"""Variables, lists, and operators showcase.

Demonstrates:
- api.vars.add(), get(), set(), change()
- api.lists.add(), append(), clear(), get_item(), set_item(), length()
- api.ops arithmetic, comparison, boolean, string, and math operators
- Accumulating results into a list for inspection
- api.flow.for_loop to iterate, writing to a list at each step

Compile::

    outputllsp3 build examples/06_variables_and_lists.py --out vars.llsp3
"""
from outputllsp3 import MotorPair

def build(project, api, ns=None):
    f  = api.flow
    v  = api.vars
    ls = api.lists
    o  = api.ops

    # Declare variables
    v.add("total", 0)
    v.add("step",  5)
    v.add("msg",   "")

    # Declare a results list
    ls.add("readings")

    # Procedure: accumulate step*n values into list
    f.procedure("FillReadings", ["count"], [
        ls.clear("readings"),
        v.set("total", 0),
        *f.for_loop("fi", 1, project.arg("count"),
            v.change("total", v.get("step")),
            ls.append("readings", v.get("total")),
        ),
    ])

    # Procedure: compute a formatted summary string
    f.procedure("ShowSummary", [], [
        v.set("msg",
            o.join("len=",
            o.join(o.join(
                    ls.length("readings"), ""),
                   o.join(" max=",
                   o.join(ls.get_item("readings", ls.length("readings")), ""))
            ))
        ),
        api.light.show_text(v.get("msg")),
        api.wait.seconds(2),
    ])

    # Procedure: demonstrate operator variety
    f.procedure("OpsDemo", [], [
        v.set("total", o.add(10, o.mul(3, 4))),        # 10 + (3*4) = 22
        v.set("total", o.mod(v.get("total"), 7)),       # 22 % 7 = 1
        v.set("total", o.abs(o.sub(5, 10))),            # |5-10| = 5
        v.set("total", o.round(o.div(22, 7))),          # round(22/7) = 3
        v.set("total", o.random(1, 100)),               # random 1–100
        v.set("msg",   o.join("r=", o.join(v.get("total"), ""))),
        api.light.show_text(v.get("msg")),
        api.wait.seconds(1),
    ])

    # Main
    f.start(
        api.move.set_pair(MotorPair.AB),
        f.call("FillReadings", 8),
        f.call("ShowSummary"),
        f.call("OpsDemo"),
        api.light.clear(),
    )
