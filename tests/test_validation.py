"""Tests for validation and deprecation warnings in the API layer."""
import warnings
import pytest


class TestDeprecationWarnings:
    def test_move_set_motor_pair_deprecated(self, project):
        from outputllsp3.api import API
        api = API(project)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            api.move.set_motor_pair("AB")
        assert any(issubclass(x.category, DeprecationWarning) for x in w)
        assert any("set_motor_pair" in str(x.message) for x in w)

    def test_move_pair_deprecated(self, project):
        from outputllsp3.api import API
        api = API(project)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            api.move.pair("AB")
        assert any(issubclass(x.category, DeprecationWarning) for x in w)

    def test_move_start_dual_speed_deprecated(self, project):
        from outputllsp3.api import API
        api = API(project)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            api.move.start_dual_speed(50, 50)
        assert any(issubclass(x.category, DeprecationWarning) for x in w)

    def test_wait_sleep_deprecated(self, project):
        from outputllsp3.api import API
        api = API(project)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            api.wait.sleep(1.0)
        assert any(issubclass(x.category, DeprecationWarning) for x in w)

    def test_wait_sleep_ms_deprecated(self, project):
        from outputllsp3.api import API
        api = API(project)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            api.wait.sleep_ms(100)
        assert any(issubclass(x.category, DeprecationWarning) for x in w)

    def test_lists_item_deprecated(self, project):
        from outputllsp3.api import API
        api = API(project)
        api.lists.add("mylist")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            api.lists.item("mylist", 1)
        assert any(issubclass(x.category, DeprecationWarning) for x in w)

    def test_lists_setitem_deprecated(self, project):
        from outputllsp3.api import API
        api = API(project)
        api.lists.add("mylist")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            api.lists.setitem("mylist", 1, "val")
        assert any(issubclass(x.category, DeprecationWarning) for x in w)

    def test_canonical_methods_no_warning(self, project):
        from outputllsp3.api import API
        api = API(project)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            api.move.set_pair("AB")
            api.wait.seconds(1.0)
            api.wait.ms(100)
        dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep_warnings) == 0


class TestProcedureArityWarning:
    def test_arity_mismatch_warns(self, project):
        from outputllsp3.api import API
        api = API(project)
        api.flow.procedure("MyProc", ["a", "b"])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            api.flow.call("MyProc", 1)  # only 1 arg, expects 2
        assert any("MyProc" in str(x.message) for x in w)

    def test_correct_arity_no_warning(self, project):
        from outputllsp3.api import API
        api = API(project)
        api.flow.procedure("MyProc2", ["a", "b"])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            api.flow.call("MyProc2", 1, 2)
        arity_warnings = [x for x in w if "MyProc2" in str(x.message)]
        assert len(arity_warnings) == 0


class TestVariableExistenceWarning:
    def test_set_undeclared_warns(self, project):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            project.set_variable("undeclared_var", 42)
        assert any("undeclared_var" in str(x.message) for x in w)

    def test_set_declared_no_warning(self, project):
        project.add_variable("declared_var", 0)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            project.set_variable("declared_var", 99)
        existence_warnings = [x for x in w if "declared_var" in str(x.message)]
        assert len(existence_warnings) == 0
