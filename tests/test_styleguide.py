# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs AB 2026
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""The house style that black and isort cannot enforce, checked on every test run.

Ported from tergite-frontend's tests/test_styleguide.py.

Code that broke a rule when the rule was added is listed in
fixtures/styleguide_baseline.txt. That list may only shrink: a new violation fails, and so
does a listed one that has been fixed but not deleted from the list.
"""
import ast
import re
import tokenize
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Set, Tuple, Union

APP_ROOT = Path(__file__).resolve().parent.parent
BASELINE_FILE = Path(__file__).parent / "fixtures" / "styleguide_baseline.txt"
SOURCE_ROOTS = ("tergite",)
ALL_ROOTS = SOURCE_ROOTS + ("tests", "dev")
EXCLUDED_PREFIXES = (
    # generated from the services' specs, in their names
    "tergite/clients/mss/models.py",
    "tergite/clients/bcc/models.py",
)
PUBLIC_SURFACE = "tergite/__init__.py"

# a new verb is added here in review, never to the baseline; from_* and to_* convert a DTO
VERBS = frozenset(
    {
        "accept",
        "add",
        "authenticate",
        "authorize",
        "broadcast",
        "cancel",
        "check",
        "choose",
        "claim",
        "cleanup",
        "clear",
        "close",
        "collect",
        "compare",
        "compress",
        "compute",
        "connect",
        "construct",
        "convert",
        "count",
        "create",
        "decode",
        "decrypt",
        "delete",
        "derive",
        "destroy",
        "disconnect",
        "dismiss",
        "dispatch",
        "do",
        "download",
        "emit",
        "encode",
        "encrypt",
        "ensure",
        "expire",
        "export",
        "extract",
        "fetch",
        "filter",
        "find",
        "forget",
        "format",
        "from",
        "generate",
        "get",
        "handle",
        "ignore",
        "include",
        "increment",
        "index",
        "init",
        "initialize",
        "insert",
        "is",
        "keep",
        "load",
        "log",
        "login",
        "logout",
        "make",
        "map",
        "mark",
        "merge",
        "move",
        "normalise",
        "notify",
        "open",
        "order",
        "paginate",
        "parse",
        "partition",
        "patch",
        "pick",
        "prepare",
        "process",
        "publish",
        "pull",
        "push",
        "raise",
        "read",
        "receive",
        "record",
        "redirect",
        "refresh",
        "register",
        "reject",
        "remove",
        "render",
        "replace",
        "reply",
        "request",
        "require",
        "reset",
        "resolve",
        "restore",
        "rewrite",
        "route",
        "run",
        "save",
        "search",
        "seed",
        "send",
        "serialize",
        "set",
        "setup",
        "should",
        "sign",
        "sort",
        "split",
        "start",
        "stop",
        "store",
        "submit",
        "switch",
        "sync",
        "to",
        "toggle",
        "transfer",
        "translate",
        "try",
        "unwrap",
        "update",
        "upload",
        "upsert",
        "use",
        "validate",
        "verify",
        "view",
        "wait",
        "write",
    }
)
# names Qiskit's base classes, Pydantic or the public API (DESIGN.md §8, rule 14) fix
FRAMEWORK_NAMES = frozenset(
    {
        "_default_options",
        "acquire_channel",
        "backends",
        "configuration",
        "control_channel",
        "drive_channel",
        "job",
        "measure_channel",
        "memory_slot",
        "model_post_init",
        "providers",
        "result",
        "status",
    }
)
HOOK_PREFIX = "on"
BOOLEAN_PREFIXES = ("is_", "should_")
BOOLEAN_ANNOTATIONS = frozenset(
    {"bool", "Optional[bool]", "bool | None", "None | bool"}
)
VALUE_DECORATORS = frozenset({"property", "cached_property", "computed_field"})
LICENSE_MARKERS = (
    "# This code is part of Tergite",
    "This code is licensed under the Apache License, Version 2.0",
)
LICENSE_SEARCH_LINES = 15
CONSTANT_NAME = re.compile(r"^_?[A-Z][A-Z0-9_]*$")
BANNER_COMMENT = re.compile(
    r"^#\s*(?:[-=*#~_]{10,}|[-=*#~_]{3,}\s*\S.*\S\s*[-=*#~_]{3,})$"
)
DEFINITIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
HEADER_TOKENS = (tokenize.ENCODING, tokenize.COMMENT, tokenize.NL)

FunctionNode = Union[ast.FunctionDef, ast.AsyncFunctionDef]


@dataclass(frozen=True)
class Violation:
    rule: str
    location: str

    def __str__(self) -> str:
        return f"{self.rule}: {self.location}"


@dataclass(frozen=True)
class Module:
    name: str
    path: Path
    tree: ast.Module


def test_functions_are_named_with_a_verb():
    _assert_follows("verb")


def test_booleans_start_with_is_or_should():
    _assert_follows("boolean")


def test_constants_sit_above_the_first_definition():
    _assert_follows("constant-position")


def test_private_helpers_sit_below_public_code():
    _assert_follows("private-helper-position")


def test_no_banner_comments():
    _assert_follows("banner")


def test_every_file_carries_the_license_header():
    _assert_follows("license-header")


def test_all_lists_strings():
    _assert_follows("all-strings")


def test_the_public_surface_declares_all():
    _assert_follows("public-surface")


def test_functions_are_fully_type_hinted():
    _assert_follows("type-hints")


def test_baseline_lists_only_current_violations():
    current = {str(violation) for rule in _RULES for violation in find_violations(rule)}
    fixed = sorted(_read_baseline() - current)

    assert fixed == [], f"fixed, so delete from {BASELINE_FILE.name}:\n" + "\n".join(
        fixed
    )


def test_checks_catch_what_they_describe(tmp_path: Path):
    (tmp_path / "tergite").mkdir()
    (tmp_path / "tergite" / "__init__.py").write_text(
        "from .sample import job_status\n"
    )
    (tmp_path / "tergite" / "sample.py").write_text(
        "# Alteration Notice\n"
        "# -----------------\n"
        "def _get_limit() -> None: ...\n"
        "def job_status(active: bool) -> None: ...\n"
        "# ---- jobs ----\n"
        "LIMIT = 5\n"
        "def build_job(shots) -> None: ...\n"
    )

    found = {
        str(violation)
        for rule in _RULES
        for violation in find_violations(rule, app_root=tmp_path)
    }

    assert found == {
        "verb: tergite/sample.py::job_status",
        "verb: tergite/sample.py::build_job",
        "boolean: tergite/sample.py::job_status(active)",
        "constant-position: tergite/sample.py::LIMIT",
        "private-helper-position: tergite/sample.py::job_status",
        "private-helper-position: tergite/sample.py::build_job",
        "banner: tergite/sample.py:5",
        "license-header: tergite/__init__.py",
        "license-header: tergite/sample.py",
        "type-hints: tergite/sample.py::build_job",
        "public-surface: tergite/__init__.py",
    }


def find_violations(rule: str, app_root: Path = APP_ROOT) -> List[Violation]:
    check, roots = _RULES[rule]
    return [
        violation
        for module in _parse_modules(app_root, roots)
        for violation in check(module)
    ]


def _assert_follows(rule: str):
    baseline = _read_baseline()
    new = [str(v) for v in find_violations(rule) if str(v) not in baseline]

    assert new == [], "\n".join(new)


@lru_cache(maxsize=None)
def _read_baseline() -> Set[str]:
    lines = BASELINE_FILE.read_text().splitlines() if BASELINE_FILE.exists() else []
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


@lru_cache(maxsize=None)
def _parse_modules(app_root: Path, roots: Tuple[str, ...]) -> Tuple[Module, ...]:
    return tuple(
        Module(
            name=path.relative_to(app_root).as_posix(),
            path=path,
            tree=ast.parse(path.read_text(), filename=str(path)),
        )
        for path in _iter_python_files(app_root, roots)
    )


def _iter_python_files(app_root: Path, roots: Tuple[str, ...]) -> Iterator[Path]:
    for root in roots:
        path = app_root / root
        if path.is_file():
            yield path
        elif path.is_dir():
            yield from sorted(
                file
                for file in path.rglob("*.py")
                if "__pycache__" not in file.parts
                and not file.relative_to(app_root)
                .as_posix()
                .startswith(EXCLUDED_PREFIXES)
            )


def _check_verbs(module: Module) -> Iterator[Violation]:
    for qualname, node in _walk_functions(module.tree):
        if not (
            _is_dunder(node.name)
            or _is_value(node)
            or node.name in FRAMEWORK_NAMES
            or _starts_with_verb(node.name)
        ):
            yield Violation("verb", f"{module.name}::{qualname}")


def _check_booleans(module: Module) -> Iterator[Violation]:
    for qualname, node in _walk_functions(module.tree):
        for argument in _arguments_of(node):
            if _is_boolean(argument.annotation) and not _has_boolean_prefix(
                argument.arg
            ):
                yield Violation("boolean", f"{module.name}::{qualname}({argument.arg})")

    for qualname, node in _walk_annotated_names(module.tree):
        if _is_boolean(node.annotation) and not _has_boolean_prefix(node.target.id):
            yield Violation("boolean", f"{module.name}::{qualname}")


def _check_constant_positions(module: Module) -> Iterator[Violation]:
    defined_names: Set[str] = set()
    for statement in module.tree.body:
        if isinstance(statement, DEFINITIONS):
            defined_names.add(statement.name)
            continue

        is_after_definitions = bool(defined_names)
        is_built_from_definitions = bool(_names_used_in(statement) & defined_names)
        for name in _constant_names_assigned_by(statement):
            if is_after_definitions and not is_built_from_definitions:
                yield Violation("constant-position", f"{module.name}::{name}")


def _check_private_helper_positions(module: Module) -> Iterator[Violation]:
    has_private_function_above = False
    for statement in module.tree.body:
        if not isinstance(statement, DEFINITIONS) or _is_dunder(statement.name):
            continue

        is_private = statement.name.startswith("_")
        if is_private and not isinstance(statement, ast.ClassDef):
            has_private_function_above = True
        elif not is_private and has_private_function_above:
            yield Violation(
                "private-helper-position", f"{module.name}::{statement.name}"
            )


def _check_banners(module: Module) -> Iterator[Violation]:
    # the licence header's "Alteration Notice" is underlined, which is no banner
    is_in_header = True
    with module.path.open("rb") as file:
        for token in tokenize.tokenize(file.readline):
            if token.type not in HEADER_TOKENS:
                is_in_header = False
            if (
                not is_in_header
                and token.type == tokenize.COMMENT
                and BANNER_COMMENT.match(token.string.strip())
            ):
                yield Violation("banner", f"{module.name}:{token.start[0]}")


def _check_license_header(module: Module) -> Iterator[Violation]:
    head = "\n".join(module.path.read_text().splitlines()[:LICENSE_SEARCH_LINES])
    if not all(marker in head for marker in LICENSE_MARKERS):
        yield Violation("license-header", module.name)


def _check_all_strings(module: Module) -> Iterator[Violation]:
    for statement in module.tree.body:
        if (
            isinstance(statement, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "__all__" for t in statement.targets
            )
            and isinstance(statement.value, (ast.List, ast.Tuple))
            and not all(
                isinstance(item, ast.Constant) and isinstance(item.value, str)
                for item in statement.value.elts
            )
        ):
            yield Violation("all-strings", f"{module.name}::__all__")


def _check_public_surface(module: Module) -> Iterator[Violation]:
    if module.name != PUBLIC_SURFACE:
        return
    names = {
        target.id
        for statement in module.tree.body
        if isinstance(statement, ast.Assign)
        for target in statement.targets
        if isinstance(target, ast.Name)
    }
    if "__all__" not in names:
        yield Violation("public-surface", module.name)


def _check_type_hints(module: Module) -> Iterator[Violation]:
    for qualname, node in _walk_functions(module.tree):
        arguments = _arguments_of(node)
        if _is_method(qualname) and arguments and arguments[0].arg in ("self", "cls"):
            arguments = arguments[1:]
        is_missing_return = node.returns is None and node.name != "__init__"
        if is_missing_return or any(a.annotation is None for a in arguments):
            yield Violation("type-hints", f"{module.name}::{qualname}")


def _walk_functions(tree: ast.AST) -> Iterator[Tuple[str, FunctionNode]]:
    for qualname, node in _walk_qualified(tree, prefix=""):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield qualname, node


def _walk_annotated_names(tree: ast.AST) -> Iterator[Tuple[str, ast.AnnAssign]]:
    for qualname, node in _walk_qualified(tree, prefix=""):
        if isinstance(node, ast.AnnAssign):
            yield qualname, node


def _walk_qualified(node: ast.AST, prefix: str) -> Iterator[Tuple[str, ast.AST]]:
    """Yields every function, class and annotated name with its dotted qualified name"""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, DEFINITIONS):
            qualname = f"{prefix}{child.name}"
            yield qualname, child
            yield from _walk_qualified(child, prefix=f"{qualname}.")
        elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            yield f"{prefix}{child.target.id}", child
        else:
            yield from _walk_qualified(child, prefix)


def _arguments_of(node: FunctionNode) -> List[ast.arg]:
    args = node.args
    variadic = [arg for arg in (args.vararg, args.kwarg) if arg is not None]
    return args.posonlyargs + args.args + args.kwonlyargs + variadic


def _names_used_in(statement: ast.stmt) -> Set[str]:
    return {node.id for node in ast.walk(statement) if isinstance(node, ast.Name)}


def _constant_names_assigned_by(statement: ast.stmt) -> List[str]:
    if isinstance(statement, ast.Assign):
        targets = statement.targets
    elif isinstance(statement, ast.AnnAssign):
        targets = [statement.target]
    else:
        return []
    return [
        t.id for t in targets if isinstance(t, ast.Name) and CONSTANT_NAME.match(t.id)
    ]


def _is_method(qualname: str) -> bool:
    return "." in qualname


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def _is_value(node: FunctionNode) -> bool:
    """Whether a decorator turns the function into a value, which is named as a noun"""
    return any(
        _decorator_name(decorator) in VALUE_DECORATORS
        for decorator in node.decorator_list
    )


def _decorator_name(decorator: ast.expr) -> str:
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    if isinstance(target, ast.Attribute):
        return target.attr
    return target.id if isinstance(target, ast.Name) else ""


def _starts_with_verb(name: str) -> bool:
    first_word = name.lstrip("_").split("_")[0]
    return first_word in VERBS or first_word == HOOK_PREFIX


def _is_boolean(annotation: Optional[ast.expr]) -> bool:
    return annotation is not None and ast.unparse(annotation) in BOOLEAN_ANNOTATIONS


def _has_boolean_prefix(name: str) -> bool:
    return name.lstrip("_").startswith(BOOLEAN_PREFIXES)


_RULES: Dict[str, Tuple[Callable[[Module], Iterator[Violation]], Tuple[str, ...]]] = {
    "verb": (_check_verbs, SOURCE_ROOTS),
    "boolean": (_check_booleans, SOURCE_ROOTS),
    "constant-position": (_check_constant_positions, SOURCE_ROOTS),
    "private-helper-position": (_check_private_helper_positions, SOURCE_ROOTS),
    "banner": (_check_banners, ALL_ROOTS),
    "license-header": (_check_license_header, ALL_ROOTS),
    "all-strings": (_check_all_strings, SOURCE_ROOTS),
    "public-surface": (_check_public_surface, SOURCE_ROOTS),
    "type-hints": (_check_type_hints, SOURCE_ROOTS),
}
