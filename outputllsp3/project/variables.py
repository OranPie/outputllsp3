"""Variable and list management.

``VariableManager`` handles variable/list declaration and all data_* block
creation, including namespace qualification.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from . import LLSP3Project


class VariableManager:
    def __init__(self, project: "LLSP3Project") -> None:
        self._p = project

    # -- namespace helpers ------------------------------------------------

    def sanitize_namespace(self, value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_]+", "__", str(value)).strip("_")

    def set_default_namespace(self, namespace: str | None, *, function_namespace: bool = False) -> None:
        self._p.default_namespace = self.sanitize_namespace(namespace or "")
        self._p.function_namespace_mode = function_namespace

    def qualify_var_name(self, name: str, namespace: str | None = None, raw: bool = False) -> str:
        if raw:
            return name
        ns = self.sanitize_namespace(namespace if namespace is not None else self._p.default_namespace)
        if not ns:
            return name
        if name.startswith(ns + "__"):
            return name
        return f"{ns}__{name}"

    # -- variable management ----------------------------------------------

    def add_variable(self, name: str, value: Any = 0, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.qualify_var_name(name, namespace=namespace, raw=raw)
        vid = self._p._id("var")
        self._p.variables[vid] = [qname, value]
        return vid

    def variable_id(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.qualify_var_name(name, namespace=namespace, raw=raw)
        for vid, (n, _) in self._p.variables.items():
            if n == qname:
                return vid
        raise KeyError(qname)

    def variable(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.qualify_var_name(name, namespace=namespace, raw=raw)
        return self._p.add_block(
            "data_variable",
            fields={"VARIABLE": [qname, self.variable_id(name, namespace=namespace, raw=raw)]},
        )

    def _var_exists(self, name: str, *, namespace: str | None = None, raw: bool = False) -> bool:
        try:
            self.variable_id(name, namespace=namespace, raw=raw)
            return True
        except Exception:
            return False

    def set_variable(self, name: str, value: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        if not self._var_exists(name, namespace=namespace, raw=raw):
            import warnings
            warnings.warn(
                f"Variable '{name}' has not been declared; call add_variable() first.",
                stacklevel=2,
            )
            self.add_variable(name, 0, namespace=namespace, raw=raw)
        qname = self.qualify_var_name(name, namespace=namespace, raw=raw)
        return self._p.add_block(
            "data_setvariableto",
            inputs={"VALUE": self._p._blocks._text_input(value)},
            fields={"VARIABLE": [qname, self.variable_id(name, namespace=namespace, raw=raw)]},
        )

    def change_variable(self, name: str, value: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        if not self._var_exists(name, namespace=namespace, raw=raw):
            import warnings
            warnings.warn(
                f"Variable '{name}' has not been declared; call add_variable() first.",
                stacklevel=2,
            )
            self.add_variable(name, 0, namespace=namespace, raw=raw)
        qname = self.qualify_var_name(name, namespace=namespace, raw=raw)
        return self._p.add_block(
            "data_changevariableby",
            inputs={"VALUE": self._p._blocks._text_input(value)},
            fields={"VARIABLE": [qname, self.variable_id(name, namespace=namespace, raw=raw)]},
        )

    # -- list management --------------------------------------------------

    def add_list(self, name: str, value: list[Any] | None = None, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.qualify_var_name(name, namespace=namespace, raw=raw)
        lid = self._p._id("list")
        self._p.lists[lid] = [qname, list(value or [])]
        return lid

    def list_id(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.qualify_var_name(name, namespace=namespace, raw=raw)
        for lid, (n, _) in self._p.lists.items():
            if n == qname:
                return lid
        raise KeyError(qname)

    def list_name(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.qualify_var_name(name, namespace=namespace, raw=raw)

    def list_contents(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self._p.add_block(
            "data_listcontents",
            fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]},
        )

    def list_length(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self._p.add_block(
            "data_lengthoflist",
            fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]},
        )

    def list_item(self, name: str, index: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self._p.add_block(
            "data_itemoflist",
            inputs={"INDEX": self._p._blocks._num_input(index)},
            fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]},
        )

    def list_contains(self, name: str, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self._p.add_block(
            "data_listcontainsitem",
            inputs={"ITEM": self._p._blocks._text_input(item)},
            fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]},
        )

    def list_replace(self, name: str, index: Any, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self._p.add_block(
            "data_replaceitemoflist",
            inputs={
                "INDEX": self._p._blocks._num_input(index),
                "ITEM": self._p._blocks._text_input(item),
            },
            fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]},
        )

    def list_delete(self, name: str, index: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self._p.add_block(
            "data_deleteoflist",
            inputs={"INDEX": self._p._blocks._num_input(index)},
            fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]},
        )

    def list_insert(self, name: str, index: Any, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self._p.add_block(
            "data_insertatlist",
            inputs={
                "INDEX": self._p._blocks._num_input(index),
                "ITEM": self._p._blocks._text_input(item),
            },
            fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]},
        )

    def list_append(self, name: str, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self._p.add_block(
            "data_addtolist",
            inputs={"ITEM": self._p._blocks._text_input(item)},
            fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]},
        )

    def list_clear(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self._p.add_block(
            "data_deletealloflist",
            fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]},
        )
