"""Tests for the LayoutManager auto-positioning system."""
import pytest
from outputllsp3.project.layout import LayoutManager


class TestLayoutManagerDefaults:
    def test_first_start(self):
        lm = LayoutManager()
        assert lm.next_start() == (-220, 90)

    def test_second_start_increments_y(self):
        lm = LayoutManager()
        lm.next_start()
        assert lm.next_start() == (-220, 590)

    def test_third_start(self):
        lm = LayoutManager()
        lm.next_start()
        lm.next_start()
        assert lm.next_start() == (-220, 1090)

    def test_first_procedure(self):
        lm = LayoutManager()
        assert lm.next_procedure() == (700, 160)

    def test_second_procedure_increments_x(self):
        lm = LayoutManager()
        lm.next_procedure()
        assert lm.next_procedure() == (1100, 160)

    def test_procedure_y_constant_within_first_row(self):
        """Procedures stay on y=160 until proc_x_wrap is reached."""
        lm = LayoutManager()
        for _ in range(4):   # 700, 1100, 1500, 1900  — all within wrap=2000
            _, y = lm.next_procedure()
            assert y == 160

    def test_procedure_wraps_to_next_row(self):
        """After 4 procedures (x hits 2300 ≥ 2000), the 5th starts a new row."""
        lm = LayoutManager()
        for _ in range(4):
            lm.next_procedure()
        # 5th procedure: x wraps back to 700, y advances by proc_y_step=600
        x5, y5 = lm.next_procedure()
        assert x5 == 700
        assert y5 == 160 + 600  # 760

    def test_start_and_procedure_independent(self):
        lm = LayoutManager()
        lm.next_start()
        lm.next_start()
        # procedures not affected by start calls
        assert lm.next_procedure() == (700, 160)


class TestLayoutManagerEvent:
    def test_first_event(self):
        lm = LayoutManager()
        assert lm.next_event() == (250, 90)

    def test_second_event_increments_y(self):
        lm = LayoutManager()
        lm.next_event()
        assert lm.next_event() == (250, 590)

    def test_events_and_starts_independent_y(self):
        """Start and event counters advance independently."""
        lm = LayoutManager()
        lm.next_start()   # start y → 590
        x_e, y_e = lm.next_event()
        assert x_e == 250
        assert y_e == 90   # event counter still at initial

    def test_event_x_differs_from_start_x(self):
        lm = LayoutManager()
        sx, _ = lm.next_start()
        ex, _ = lm.next_event()
        assert ex != sx


class TestLayoutManagerCustom:
    def test_custom_step(self):
        lm = LayoutManager(start_y_step=300, proc_x_step=500)
        lm.next_start()
        assert lm.next_start() == (-220, 390)
        lm.next_procedure()
        assert lm.next_procedure() == (1200, 160)

    def test_custom_initial(self):
        lm = LayoutManager(start_y_initial=200, proc_x_initial=1000, proc_y=200)
        assert lm.next_start() == (-220, 200)
        assert lm.next_procedure() == (1000, 200)

    def test_custom_event_x(self):
        lm = LayoutManager(event_x=400)
        assert lm.next_event() == (400, 90)

    def test_custom_proc_x_wrap(self):
        lm = LayoutManager(proc_x_initial=700, proc_x_step=400, proc_x_wrap=1500)
        lm.next_procedure()   # 700 → next=1100
        lm.next_procedure()   # 1100 → next=1500; 1500 >= 1500 → wrap to row 2
        x3, y3 = lm.next_procedure()
        assert x3 == 700
        assert y3 == 160 + 600  # 760


class TestLayoutManagerReset:
    def test_reset_restores_start(self):
        lm = LayoutManager()
        lm.next_start()
        lm.next_start()
        lm.reset()
        assert lm.next_start() == (-220, 90)

    def test_reset_restores_procedure(self):
        lm = LayoutManager()
        lm.next_procedure()
        lm.next_procedure()
        lm.reset()
        assert lm.next_procedure() == (700, 160)

    def test_reset_restores_event(self):
        lm = LayoutManager()
        lm.next_event()
        lm.next_event()
        lm.reset()
        assert lm.next_event() == (250, 90)

    def test_reset_respects_custom_initial(self):
        """reset() must restore the values passed to __init__, not hardcoded defaults."""
        lm = LayoutManager(start_y_initial=200, proc_x_initial=1000, event_x=500)
        lm.next_start(); lm.next_event(); lm.next_procedure()
        lm.reset()
        assert lm.next_start() == (-220, 200)
        assert lm.next_event() == (500, 200)
        assert lm.next_procedure() == (1000, 160)


class TestLayoutManagerRelayout:
    """Tests for post-build position recomputation."""

    def _make_blocks(self, *chains):
        """Build a minimal block dict from chains of opcodes.

        Each chain is a list of opcode strings; they are connected via 'next'.
        The first block in each chain is top-level.
        """
        blocks: dict = {}
        bid_counter = [0]

        def new_id():
            bid_counter[0] += 1
            return f'b{bid_counter[0]}'

        for chain_ops in chains:
            ids = [new_id() for _ in chain_ops]
            for i, (op, bid) in enumerate(zip(chain_ops, ids)):
                block: dict = {'opcode': op, 'inputs': {}, 'fields': {}}
                if i == 0:
                    block['topLevel'] = True
                    block['x'] = 0
                    block['y'] = 0
                if i < len(ids) - 1:
                    block['next'] = ids[i + 1]
                else:
                    block['next'] = None
                if i > 0:
                    block['parent'] = ids[i - 1]
                blocks[bid] = block
        return blocks

    def test_relayout_separates_starts(self):
        blocks = self._make_blocks(
            ['flipperevents_whenProgramStarts', 'control_wait'],
            ['flipperevents_whenProgramStarts', 'control_wait', 'control_wait'],
        )
        lm = LayoutManager()
        lm.relayout(blocks)
        tops = [bid for bid, b in blocks.items() if b.get('topLevel')]
        ys = sorted(blocks[bid]['y'] for bid in tops)
        # Second stack must be below the first
        assert ys[1] > ys[0]

    def test_relayout_events_in_middle_column(self):
        blocks = self._make_blocks(
            ['flipperevents_whenButton'],
        )
        lm = LayoutManager()
        lm.relayout(blocks)
        top = next(bid for bid, b in blocks.items() if b.get('topLevel'))
        assert blocks[top]['x'] == 250   # event_x default

    def test_relayout_procedure_grid(self):
        blocks = self._make_blocks(
            ['procedures_definition'],
            ['procedures_definition'],
        )
        lm = LayoutManager()
        lm.relayout(blocks)
        procs = [bid for bid, b in blocks.items() if b.get('topLevel')]
        xs = [blocks[bid]['x'] for bid in procs]
        ys = [blocks[bid]['y'] for bid in procs]
        # They should be at different x positions on the same row
        assert len(set(xs)) == 2
        assert ys[0] == ys[1] == 160

    def test_relayout_deeper_stacks_push_next_start_down(self):
        """A longer chain should create more vertical space before the next stack."""
        blocks_short = self._make_blocks(
            ['flipperevents_whenProgramStarts'],  # 1 block
            ['flipperevents_whenProgramStarts'],  # 1 block
        )
        blocks_long = self._make_blocks(
            ['flipperevents_whenProgramStarts', 'control_wait', 'control_wait',
             'control_wait', 'control_wait', 'control_wait'],  # 6 blocks
            ['flipperevents_whenProgramStarts'],
        )
        lm_short = LayoutManager()
        lm_short.relayout(blocks_short)
        lm_long = LayoutManager()
        lm_long.relayout(blocks_long)

        def y_gap(blocks):
            tops = sorted(
                [bid for bid, b in blocks.items() if b.get('topLevel')],
                key=lambda bid: blocks[bid]['y']
            )
            return blocks[tops[1]]['y'] - blocks[tops[0]]['y']

        assert y_gap(blocks_long) > y_gap(blocks_short)


class TestFlowBuilderAutoLayout:
    """Integration: FlowBuilder uses LayoutManager for auto-positioning."""

    def test_start_uses_layout(self, project):
        """Two start() calls without x/y should produce different y coordinates."""
        from outputllsp3.flow import FlowBuilder
        lm = LayoutManager()
        flow = FlowBuilder(project, lm)
        id1 = flow.start()
        id2 = flow.start()
        b = project.blocks
        y1 = b[id1]["y"]
        y2 = b[id2]["y"]
        assert y2 > y1

    def test_explicit_xy_overrides_layout(self, project):
        """Explicit x/y still overrides auto-layout."""
        from outputllsp3.flow import FlowBuilder
        lm = LayoutManager()
        flow = FlowBuilder(project, lm)
        sid = flow.start(x=999, y=888)
        assert project.blocks[sid]["x"] == 999
        assert project.blocks[sid]["y"] == 888
