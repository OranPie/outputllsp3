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
