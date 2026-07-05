"""Passenger lookup tools over the Titanic demo dataset."""

# TODO(M3): implement and register on the MCP server:
#   - get_passenger(passenger_id: int) -> single row or not-found
#   - search_passengers(name: str | None, pclass: int | None, survived: bool | None,
#                       limit: int, offset: int) -> paginated rows
#     Filters map to an allow-listed set of columns; limit is capped by
#     settings.max_rows.


def get_passenger(passenger_id: int) -> dict | None:
    """Return one passenger by id, or ``None`` if not found."""
    raise NotImplementedError("TODO(M3)")


def search_passengers(**filters: object) -> list[dict]:
    """Return passengers matching the given allow-listed filters."""
    raise NotImplementedError("TODO(M3)")
