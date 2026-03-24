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

    def test_procedure_y_constant(self):
        lm = LayoutManager()
        for _ in range(5):
            _, y = lm.next_procedure()
            assert y == 160

    def test_start_and_procedure_independent(self):
        lm = LayoutManager()
        lm.next_start()
        lm.next_start()
        # procedures not affected by start calls
        assert lm.next_procedure() == (700, 160)


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
