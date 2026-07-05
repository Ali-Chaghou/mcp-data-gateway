"""Read-only SQL guard.

A **deny-by-default first filter** that validates a SQL string is a single,
read-only ``SELECT`` over allowed tables before it may reach the database
driver. Anything not positively identified as safe is rejected, even at the
cost of refusing some legitimate queries (CTEs, comments, quoted identifiers,
``EXPLAIN``, subqueries in ``FROM``).

This is deliberately **not a complete SQL parser**. It works on a "skeleton"
of the statement with string literals blanked out (so keywords inside literals
don't cause false rejections, while keywords Postgres would actually parse as
code stay visible) and uses small, explainable regex/token scans. Because it is
a heuristic, it errs toward rejection when unsure.

It is one layer of a defense-in-depth model, not the authoritative control.
**The database role and session remain the authoritative enforcement layer:**
the server must connect as a ``SELECT``-only role with
``default_transaction_read_only = on`` so that anything this filter fails to
catch is still refused by PostgreSQL itself. That role/session enforcement is
planned for M2 (see SECURITY.md); until it lands, this guard is the only active
control and should be treated accordingly.

This module is developed test-first — ``tests/test_readonly_sql.py`` is the
authoritative specification of what SQL is allowed through.
"""

import re
from collections.abc import Iterator
from typing import Final

ALLOWED_TABLES: Final[frozenset[str]] = frozenset({"passengers"})

#: Keywords that indicate writes, DDL, privilege changes, transaction control,
#: session changes, or server-side execution. A plain SELECT never needs any
#: of them, so each is rejected as a whole word anywhere outside a string
#: literal (this also catches e.g. ``FOR UPDATE`` and writing CTEs).
_FORBIDDEN_KEYWORDS: Final[frozenset[str]] = frozenset(
    {
        # writes
        "insert",
        "update",
        "delete",
        "merge",
        "into",
        # DDL and maintenance
        "create",
        "alter",
        "drop",
        "truncate",
        "rename",
        "comment",
        "vacuum",
        "analyze",
        "analyse",
        "reindex",
        "cluster",
        "refresh",
        # privileges
        "grant",
        "revoke",
        # server-side execution and bulk I/O
        "call",
        "execute",
        "do",
        "prepare",
        "deallocate",
        "copy",
        # session / transaction control
        "set",
        "reset",
        "show",
        "begin",
        "commit",
        "rollback",
        "savepoint",
        "release",
        "abort",
        "start",
        "lock",
        "discard",
        "listen",
        "unlisten",
        "notify",
    }
)

#: Functions with no legitimate use in a read-only query tool and a large blast
#: radius. This is a curated denylist (not exhaustive): the authoritative
#: control against dangerous functions is the SELECT-only database role, which
#: is not granted EXECUTE on most of these. We block the well-known offenders
#: early so they never reach the driver.
_FORBIDDEN_FUNCTIONS: Final[frozenset[str]] = frozenset(
    {
        # connection stalling / denial of service
        "pg_sleep",
        # cross-database / cross-host access
        "dblink",
        # server filesystem read/write
        "lo_import",
        "lo_export",
        "pg_read_file",
        "pg_read_binary_file",
        "pg_ls_dir",
        "pg_stat_file",
        # configuration / secret disclosure and session mutation
        "current_setting",
        "set_config",
        # execute an arbitrary SQL string the skeleton scan cannot inspect
        "query_to_xml",
        "query_to_xmlschema",
        "query_to_xml_and_xmlschema",
    }
)

# A single-quoted literal with '' as the escaped quote (standard SQL).
_STRING_LITERAL: Final[re.Pattern[str]] = re.compile(r"'(?:[^']|'')*'")
_WORD: Final[re.Pattern[str]] = re.compile(r"[a-z_][a-z0-9_$]*")
_TRAILING_LIMIT: Final[re.Pattern[str]] = re.compile(
    r"\blimit\s+(?P<limit>\d+)(?P<offset>\s+offset\s+\d+)?\s*$", re.IGNORECASE
)

# Tokens that matter for locating table references: bare or schema-qualified
# identifiers, and the punctuation that delimits a relation list. Everything
# else (operators, numbers, ``*``, ``%s`` placeholders) is skipped.
_TOKEN: Final[re.Pattern[str]] = re.compile(r"[a-z_][a-z0-9_$.]*|[(),]")

# Keywords that occupy a table position but are not tables themselves.
_RELATION_MODIFIERS: Final[frozenset[str]] = frozenset({"lateral", "only"})

# Keywords that close a FROM clause's relation list. JOIN and comma continue
# the list; ON/USING do not close it, so trailing comma-joins remain visible.
_FROM_CLAUSE_END: Final[frozenset[str]] = frozenset(
    {
        "where",
        "group",
        "order",
        "having",
        "limit",
        "offset",
        "window",
        "fetch",
        "union",
        "intersect",
        "except",
    }
)


class ReadOnlyViolation(Exception):
    """Raised when SQL fails the read-only check."""


def _iter_relation_names(skeleton: str) -> Iterator[str]:
    """Yield every identifier that sits in a table position.

    A table position is the token immediately after ``FROM`` or ``JOIN``, or
    after a comma that continues an open ``FROM`` clause (a comma join). This
    catches unauthorized tables reached via comma joins and every ``JOIN``
    variant (``CROSS``/``LEFT``/``LATERAL`` ...), including inside subqueries.

    It is a small single-pass scanner, not a parser: when unsure it errs toward
    yielding a name so the allow-list check can reject it (deny by default).
    """
    depth = 0
    from_depths: set[int] = set()  # paren depths with an open FROM clause
    expect_relation = False

    for tok in _TOKEN.findall(skeleton):
        if tok == "(":
            depth += 1
            continue
        if tok == ")":
            depth -= 1
            from_depths = {d for d in from_depths if d <= depth}
            expect_relation = False
            continue
        if tok == ",":
            if depth in from_depths:
                expect_relation = True  # comma join: another relation follows
            continue

        # tok is an identifier
        if tok == "from":
            from_depths.add(depth)
            expect_relation = True
        elif tok == "join":
            expect_relation = True
        elif expect_relation:
            if tok == "select":
                expect_relation = False  # a subquery term, not a table
            elif tok not in _RELATION_MODIFIERS:
                expect_relation = False
                yield tok
            # relation modifiers (LATERAL, ONLY) keep expecting the real table
        elif tok in _FROM_CLAUSE_END and depth in from_depths:
            from_depths.discard(depth)


def _normalize(sql: str) -> str:
    """Strip surrounding whitespace and at most one trailing semicolon.

    Exactly one, so that ``SELECT 1;;`` still contains a semicolon afterwards
    and is rejected as statement chaining.
    """
    statement = sql.strip()
    if statement.endswith(";"):
        statement = statement[:-1].rstrip()
    return statement


def assert_readonly(sql: str, allowed_tables: frozenset[str] = ALLOWED_TABLES) -> None:
    """Raise :class:`ReadOnlyViolation` unless ``sql`` is one safe SELECT.

    Safe means: a single statement whose first keyword is SELECT, containing
    no comments, no quoted identifiers, no forbidden keyword or function
    outside string literals, and referencing only tables in ``allowed_tables``.
    """
    if not isinstance(sql, str) or not sql.strip():
        raise ReadOnlyViolation("SQL must be a non-empty string")

    statement = _normalize(sql)
    skeleton = _STRING_LITERAL.sub("''", statement).lower()

    if ";" in skeleton:
        raise ReadOnlyViolation("multiple SQL statements are not allowed")
    if "--" in skeleton or "/*" in skeleton or "*/" in skeleton:
        raise ReadOnlyViolation("SQL comments are not allowed")
    if '"' in skeleton:
        raise ReadOnlyViolation("quoted identifiers are not allowed")
    if not re.match(r"select\b", skeleton):
        raise ReadOnlyViolation("only SELECT statements are allowed")

    for word in _WORD.findall(skeleton):
        if word in _FORBIDDEN_KEYWORDS:
            raise ReadOnlyViolation(f"forbidden keyword in SQL: {word.upper()}")
        # startswith covers the dblink_* helper family (dblink_exec, ...).
        if word in _FORBIDDEN_FUNCTIONS or word.startswith("dblink_"):
            raise ReadOnlyViolation(f"forbidden function in SQL: {word}")

    for ref in _iter_relation_names(skeleton):
        table = ref.removeprefix("public.")
        if table not in allowed_tables:
            raise ReadOnlyViolation(f"table {ref!r} is not on the allowed list")


def apply_row_limit(sql: str, max_rows: int) -> str:
    """Return ``sql`` guaranteed to yield at most ``max_rows`` rows.

    Appends ``LIMIT max_rows`` when the statement has no trailing limit, and
    clamps an existing trailing ``LIMIT n [OFFSET m]`` when n exceeds the cap.
    Call only on SQL that already passed :func:`assert_readonly`.
    """
    if max_rows <= 0:
        raise ValueError("max_rows must be positive")

    statement = _normalize(sql)
    match = _TRAILING_LIMIT.search(statement)
    if match is None:
        return f"{statement} LIMIT {max_rows}"
    if int(match.group("limit")) <= max_rows:
        return statement
    offset = match.group("offset") or ""
    return f"{statement[: match.start()]}LIMIT {max_rows}{offset}"
