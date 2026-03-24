"""Tests for FlowBuilder helper methods: for_loop, while_loop, cond."""
import pytest
from outputllsp3.flow import FlowBuilder


class TestForLoop:
    def test_returns_list_of_two(self, project):
        project.add_variable("i", 0)
        flow = FlowBuilder(project)
        result = flow.for_loop("i", 0, 10)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_block_ids_are_strings(self, project):
        project.add_variable("i", 0)
        flow = FlowBuilder(project)
        result = flow.for_loop("i", 0, 10)
        assert all(isinstance(bid, str) for bid in result)

    def test_set_block_in_project(self, project):
        project.add_variable("counter", 0)
        flow = FlowBuilder(project)
        set_id, repeat_id = flow.for_loop("counter", 0, 5)
        assert set_id in project.blocks
        assert repeat_id in project.blocks

    def test_set_block_opcode(self, project):
        project.add_variable("counter", 0)
        flow = FlowBuilder(project)
        set_id, _ = flow.for_loop("counter", 1, 5)
        assert project.blocks[set_id]["opcode"] == "data_setvariableto"

    def test_repeat_block_opcode(self, project):
        project.add_variable("counter", 0)
        flow = FlowBuilder(project)
        _, repeat_id = flow.for_loop("counter", 1, 5)
        assert project.blocks[repeat_id]["opcode"] == "control_repeat_until"

    def test_with_body(self, project):
        project.add_variable("counter", 0)
        flow = FlowBuilder(project)
        body_block = project.wait(0.1)
        result = flow.for_loop("counter", 1, 5, body_block)
        assert len(result) == 2

    def test_custom_step_accepted(self, project):
        project.add_variable("j", 0)
        flow = FlowBuilder(project)
        result = flow.for_loop("j", 0, 100, step=10)
        assert len(result) == 2


class TestWhileLoop:
    def test_returns_block_id(self, project):
        flow = FlowBuilder(project)
        cond = project.gt(1, 0)
        result = flow.while_loop(cond)
        assert isinstance(result, str)

    def test_block_in_project(self, project):
        flow = FlowBuilder(project)
        cond = project.gt(1, 0)
        result = flow.while_loop(cond)
        assert result in project.blocks

    def test_opcode_is_repeat_until(self, project):
        flow = FlowBuilder(project)
        cond = project.eq(1, 1)
        result = flow.while_loop(cond)
        assert project.blocks[result]["opcode"] == "control_repeat_until"

    def test_with_body(self, project):
        flow = FlowBuilder(project)
        cond = project.gt(1, 0)
        body = project.wait(0.1)
        result = flow.while_loop(cond, body)
        assert isinstance(result, str)
        assert result in project.blocks


class TestCond:
    def test_returns_block_id(self, project):
        flow = FlowBuilder(project)
        cond_blk = project.gt(1, 0)
        true_blk = project.add(1, 2)
        false_blk = project.add(3, 4)
        result = flow.cond(cond_blk, true_blk, false_blk)
        assert isinstance(result, str)

    def test_block_in_project(self, project):
        flow = FlowBuilder(project)
        cond_blk = project.gt(2, 1)
        true_blk = project.add(10, 0)
        false_blk = project.add(0, 20)
        result = flow.cond(cond_blk, true_blk, false_blk)
        assert result in project.blocks

    def test_opcode_is_if_else(self, project):
        flow = FlowBuilder(project)
        cond_blk = project.eq(1, 1)
        true_blk = project.wait(0.1)
        false_blk = project.wait(0.2)
        result = flow.cond(cond_blk, true_blk, false_blk)
        assert project.blocks[result]["opcode"] == "control_if_else"


class TestWhenEvent:
    """Tests for FlowBuilder.when() – event handler hat creation."""

    def _make_flow(self, project):
        from outputllsp3.project.layout import LayoutManager
        return FlowBuilder(project, LayoutManager())

    def test_button_opcode(self, project):
        flow = self._make_flow(project)
        bid = flow.when('button', button='left', action='pressed')
        assert project.blocks[bid]['opcode'] == 'flipperevents_whenButton'

    def test_button_fields(self, project):
        flow = self._make_flow(project)
        bid = flow.when('button', button='right', action='released')
        fields = project.blocks[bid]['fields']
        assert fields['BUTTON'][0] == 'right'
        assert fields['EVENT'][0] == 'released'

    def test_gesture_opcode(self, project):
        flow = self._make_flow(project)
        bid = flow.when('gesture', gesture='shake')
        assert project.blocks[bid]['opcode'] == 'flipperevents_whenGesture'
        assert project.blocks[bid]['fields']['EVENT'][0] == 'shake'

    def test_orientation_opcode(self, project):
        flow = self._make_flow(project)
        bid = flow.when('orientation', value='upside-down')
        assert project.blocks[bid]['opcode'] == 'flipperevents_whenOrientation'
        assert project.blocks[bid]['fields']['VALUE'][0] == 'upside-down'

    def test_tilted_opcode(self, project):
        flow = self._make_flow(project)
        bid = flow.when('tilted', direction='front')
        assert project.blocks[bid]['opcode'] == 'flipperevents_whenTilted'
        # Tilted uses an input menu (shadow block)
        assert 'VALUE' in project.blocks[bid]['inputs']

    def test_timer_opcode(self, project):
        flow = self._make_flow(project)
        bid = flow.when('timer', threshold=7.5)
        assert project.blocks[bid]['opcode'] == 'flipperevents_whenTimer'

    def test_color_opcode(self, project):
        flow = self._make_flow(project)
        bid = flow.when('color', port='A', color='red')
        assert project.blocks[bid]['opcode'] == 'flipperevents_whenColor'

    def test_force_opcode(self, project):
        flow = self._make_flow(project)
        bid = flow.when('force', port='A', option='pressed')
        assert project.blocks[bid]['opcode'] == 'flipperevents_whenPressed'
        assert project.blocks[bid]['fields']['OPTION'][0] == 'pressed'

    def test_near_maps_to_distance(self, project):
        flow = self._make_flow(project)
        bid = flow.when('near', port='A', value=15)
        assert project.blocks[bid]['opcode'] == 'flipperevents_whenDistance'
        assert project.blocks[bid]['fields']['COMPARATOR'][0] == 'less_than'

    def test_far_maps_to_distance(self, project):
        flow = self._make_flow(project)
        bid = flow.when('far', port='A', value=30)
        assert project.blocks[bid]['opcode'] == 'flipperevents_whenDistance'
        assert project.blocks[bid]['fields']['COMPARATOR'][0] == 'greater_than'

    def test_distance_opcode(self, project):
        flow = self._make_flow(project)
        bid = flow.when('distance', port='B', comparator='greater_than', value=20)
        assert project.blocks[bid]['opcode'] == 'flipperevents_whenDistance'
        assert project.blocks[bid]['fields']['COMPARATOR'][0] == 'greater_than'

    def test_broadcast_opcode(self, project):
        flow = self._make_flow(project)
        bid = flow.when('broadcast', message='go!')
        assert project.blocks[bid]['opcode'] == 'event_whenbroadcastreceived'
        assert project.blocks[bid]['fields']['BROADCAST_OPTION'][0] == 'go!'

    def test_condition_opcode(self, project):
        flow = self._make_flow(project)
        bid = flow.when('condition')
        assert project.blocks[bid]['opcode'] == 'flipperevents_whenCondition'

    def test_body_chained(self, project):
        flow = self._make_flow(project)
        body = project.wait(0.5)
        bid = flow.when('button', body, button='left')
        assert project.blocks[bid]['next'] == body

    def test_is_top_level(self, project):
        flow = self._make_flow(project)
        bid = flow.when('gesture', gesture='tapped')
        assert project.blocks[bid]['topLevel'] is True

    def test_uses_event_x_position(self, project):
        """Default position comes from layout.next_event() (x ≈ 250)."""
        from outputllsp3.project.layout import LayoutManager
        lm = LayoutManager()
        flow = FlowBuilder(project, lm)
        bid = flow.when('button')
        assert project.blocks[bid]['x'] == 250

    def test_explicit_position_overrides(self, project):
        flow = self._make_flow(project)
        bid = flow.when('gesture', x=999, y=888, gesture='tapped')
        assert project.blocks[bid]['x'] == 999
        assert project.blocks[bid]['y'] == 888

    def test_case_insensitive(self, project):
        flow = self._make_flow(project)
        bid = flow.when('BUTTON', button='left')
        assert project.blocks[bid]['opcode'] == 'flipperevents_whenButton'

    def test_unknown_event_raises(self, project):
        flow = self._make_flow(project)
        import pytest
        with pytest.raises(ValueError, match="Unknown event_type"):
            flow.when('bad_event_name')
