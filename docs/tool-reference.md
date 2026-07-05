# Tool reference

The gateway exposes exactly **six** read-only MCP tools. There is **no
raw-SQL-execution tool**: callers cannot run arbitrary SQL, name arbitrary
tables or columns, or perform any write. Every filter is validated against an
allow-list in code, and every caller value is passed to PostgreSQL as a bound
parameter — never string-interpolated into SQL.

Validation happens *before* any SQL is issued. A rejected argument raises a tool
error and no query runs. Numeric database values (e.g. `age`, `fare`,
`survival_rate`) are returned as JSON numbers. See the
[security model](security-model.md) for how this fits the defense-in-depth
layers, and [architecture](architecture.md) for the request path.

---

## `list_tables`

- **Purpose:** list the tables the gateway can query.
- **Arguments:** none.
- **Validation:** none needed — the result is the fixed allow-list.
- **Result:** a list of table names, currently `["passengers"]`.
- **Failure modes:** none.

## `describe_table`

- **Purpose:** describe the columns of an allow-listed table.
- **Arguments:** `table` (string, optional, default `"passengers"`).
- **Validation:** `table` must be on the allow-list (currently only
  `passengers`); anything else — including schema-qualified names like
  `information_schema.columns` — is rejected before any SQL runs. The column
  metadata is curated in code, so no arbitrary database metadata is exposed.
- **Result:** an object of the form:

  ```json
  {
    "table": "passengers",
    "columns": [
      {"name": "passenger_id", "type": "integer", "nullable": false, "description": "..."}
    ]
  }
  ```

  Each column has `name`, `type`, `nullable`, and a short `description`.
- **Failure modes:** `UnknownTableError` for any name not on the allow-list.

## `get_passenger`

- **Purpose:** look up a single passenger by id.
- **Arguments:** `passenger_id` (integer, required).
- **Validation:** must be a positive integer (booleans are rejected).
- **Result:** the passenger row as an object (the columns listed by
  `describe_table`), or `null` if no passenger has that id.
- **Failure modes:** `InvalidFilterError` for a non-positive or non-integer id.

## `search_passengers`

- **Purpose:** find passengers matching allow-listed filters.
- **Arguments (all optional):**

  | Argument | Type | Accepted values |
  | --- | --- | --- |
  | `pclass` | integer | `1`, `2`, or `3` |
  | `survived` | integer/boolean | `0` or `1` (a boolean is normalized to `0`/`1`) |
  | `sex` | string | `"male"` or `"female"` |
  | `embarked` | string | `"C"`, `"Q"`, or `"S"` |
  | `min_age` | number | non-negative |
  | `max_age` | number | non-negative; must be ≥ `min_age` |
  | `limit` | integer | positive; must not exceed `MAX_ROWS` |

- **Validation:** each provided filter must match its accepted values;
  `max_age` must not be smaller than `min_age`; `limit` must be positive and at
  most `MAX_ROWS`. Filters map to fixed columns and values are bound as
  parameters.
- **Result:** a list of passenger row objects, ordered by `passenger_id`. The
  number of rows is capped at `limit` when given, otherwise at `MAX_ROWS`.
- **Failure modes:** `InvalidFilterError` for any out-of-range value or an
  invalid age range or limit.

## `survival_summary`

- **Purpose:** overall passenger count and survival rate.
- **Arguments:** none.
- **Validation:** none.
- **Result:** an object with `total_count`, `survived_count`, and
  `survival_rate` (a fraction between `0.0` and `1.0`, `0.0` when there are no
  rows).
- **Failure modes:** none.

## `survival_by`

- **Purpose:** counts and survival rate grouped by an allow-listed column.
- **Arguments:** `group_by` (string, required).
- **Validation:** `group_by` must be one of `pclass`, `sex`, or `embarked`.
  Each allowed value selects a fixed SQL template; the caller value is never
  spliced into SQL.
- **Result:** a list of objects, one per group, each with `group`,
  `total_count`, `survived_count`, and `survival_rate`.
- **Failure modes:** `InvalidGroupByError` for any other value (including
  attempts like `"pclass; DROP TABLE passengers"`).

---

See [validation](validation.md) for the tests that pin this behavior.
