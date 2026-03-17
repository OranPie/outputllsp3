"""Smoke tests for LLSP3 parsing and basic project creation."""
import json
import os
import tempfile
import zipfile
from pathlib import Path


def _bundled(name):
    from outputllsp3.workflow import bundled_paths
    return bundled_paths()[name]


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

def test_parse_bundled_ok():
    from outputllsp3 import parse_llsp3, LLSP3Document
    doc = parse_llsp3(_bundled('template'))
    assert isinstance(doc, LLSP3Document)
    assert doc.path
    assert 'targets' in doc.project


def test_parse_bundled_full():
    from outputllsp3 import parse_llsp3
    doc = parse_llsp3(_bundled('full'))
    assert doc.project


def test_parse_bundled_block_reference():
    from outputllsp3 import parse_llsp3
    doc = parse_llsp3(_bundled('block_reference'))
    assert doc.project


def test_llsp3_document_properties():
    from outputllsp3 import parse_llsp3
    doc = parse_llsp3(_bundled('template'))
    # sprite property
    sprite = doc.sprite
    assert isinstance(sprite, dict)
    # blocks and variables
    assert isinstance(doc.blocks, dict)
    assert isinstance(doc.variables, dict)
    # opcode_counts
    counts = doc.opcode_counts()
    assert hasattr(counts, '__getitem__')
    # procedure_names
    names = doc.procedure_names()
    assert isinstance(names, list)
    # summary
    s = doc.summary()
    assert 'block_count' in s
    assert 'variable_count' in s


def test_parse_file_not_found():
    from outputllsp3 import parse_llsp3
    import pytest
    with pytest.raises(FileNotFoundError):
        parse_llsp3('/nonexistent/path.llsp3')


# ---------------------------------------------------------------------------
# Project creation tests
# ---------------------------------------------------------------------------

def test_project_creates_and_saves():
    from outputllsp3 import LLSP3Project, API
    from outputllsp3.workflow import discover_defaults

    defaults = discover_defaults('.')
    project = LLSP3Project(defaults['template'], defaults['strings'])
    api = API(project)
    api.flow.start(api.wait.seconds(0.1))

    with tempfile.NamedTemporaryFile(suffix='.llsp3', delete=False) as f:
        out = f.name
    try:
        project.save(out)
        assert Path(out).exists()
        assert Path(out).stat().st_size > 0
        # Verify it's a valid zip
        with zipfile.ZipFile(out) as zf:
            assert 'scratch.sb3' in zf.namelist()
    finally:
        project.cleanup()
        if Path(out).exists():
            os.unlink(out)


def test_project_variables():
    from outputllsp3 import LLSP3Project, API
    from outputllsp3.workflow import discover_defaults

    defaults = discover_defaults('.')
    project = LLSP3Project(defaults['template'], defaults['strings'])
    api = API(project)
    api.vars.add('speed', 420)
    api.vars.add('dist', 30)
    api.flow.start(
        api.vars.set('speed', 300),
    )

    with tempfile.NamedTemporaryFile(suffix='.llsp3', delete=False) as f:
        out = f.name
    try:
        project.save(out)
        assert Path(out).exists()
    finally:
        project.cleanup()
        if Path(out).exists():
            os.unlink(out)


def test_project_custom_procedure():
    from outputllsp3 import LLSP3Project, API
    from outputllsp3.workflow import discover_defaults

    defaults = discover_defaults('.')
    project = LLSP3Project(defaults['template'], defaults['strings'])
    api = API(project)

    # Define a procedure with defaults
    defid = api.flow.procedure(
        'test_proc',
        ['a', 'b'],
        api.wait.seconds(0.1),
        defaults=[10, 20],
    )
    assert defid

    # Call it with all args
    callid = api.flow.call('test_proc', 5, 15)
    assert callid

    # Call it with one arg (should fill default for b)
    callid2 = api.flow.call('test_proc', 5)
    assert callid2

    api.flow.start(callid, callid2)

    with tempfile.NamedTemporaryFile(suffix='.llsp3', delete=False) as f:
        out = f.name
    try:
        project.save(out)
        assert Path(out).exists()
    finally:
        project.cleanup()
        if Path(out).exists():
            os.unlink(out)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

def test_bundled_schema_loads():
    from outputllsp3 import bundled_schema, SchemaRegistry
    schema = bundled_schema()
    assert isinstance(schema, SchemaRegistry)


def test_bundled_schema_has_opcodes():
    from outputllsp3 import bundled_schema
    schema = bundled_schema()
    d = schema.to_dict()
    assert len(d) > 10
    # Known opcodes that must be present
    assert 'flipperevents_whenProgramStarts' in d
    assert 'flippermove_stopMove' in d
