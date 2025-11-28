"""Utility functions for building CDash GraphQL queries."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any


def parse_relative_date(date_str: str) -> str:
    """Parse relative date strings to YYYY-MM-DD format.

    Args:
        date_str: Date string (can be relative like "yesterday", "today", "last_7_days"
                  or absolute like "2025-11-26")

    Returns:
        Date string in YYYY-MM-DD format

    Examples:
        >>> parse_relative_date("yesterday")
        "2025-11-26"
        >>> parse_relative_date("2025-11-26")
        "2025-11-26"
    """
    date_str = date_str.lower().strip()
    today = datetime.now()

    # Handle relative dates
    relative_dates = {
        "today": today,
        "yesterday": today - timedelta(days=1),
        "last_week": today - timedelta(days=7),
        "last_month": today - timedelta(days=30),
    }

    if date_str in relative_dates:
        return relative_dates[date_str].strftime("%Y-%m-%d")

    # Handle "N days ago" format
    if date_str.endswith("days ago"):
        try:
            days = int(date_str.split()[0])
            return (today - timedelta(days=days)).strftime("%Y-%m-%d")
        except (ValueError, IndexError):
            pass

    # Handle "last_N_days" format
    if date_str.startswith("last_") and date_str.endswith("_days"):
        try:
            days = int(date_str.replace("last_", "").replace("_days", ""))
            return (today - timedelta(days=days)).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Assume it's already in the correct format
    return date_str


def parse_date_range(date_range: str) -> tuple[str, str]:
    """Parse date range string to start and end dates.

    Args:
        date_range: Date range like "last_7_days", "yesterday..today", "2025-11-20..2025-11-27"

    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format
    """
    today = datetime.now()

    # Handle "last_N_days" format
    if date_range.startswith("last_") and date_range.endswith("_days"):
        try:
            days = int(date_range.replace("last_", "").replace("_days", ""))
            end_date = today.strftime("%Y-%m-%d")
            start_date = (today - timedelta(days=days - 1)).strftime("%Y-%m-%d")
            return (start_date, end_date)
        except ValueError:
            pass

    # Handle range format "start..end"
    if ".." in date_range:
        start, end = date_range.split("..", 1)
        return (parse_relative_date(start), parse_relative_date(end))

    # Single date - return same date for both
    date = parse_relative_date(date_range)
    return (date, date)


def build_builds_query(
    project_name: str,
    limit: int = 10,
    order_by: Optional[str] = None,
    order_direction: str = "DESC",
    date: Optional[str] = None,
    date_range: Optional[str] = None,
    site_name: Optional[str] = None,
    build_name: Optional[str] = None,
) -> tuple[str, Dict[str, Any]]:
    """Build a GraphQL query for fetching builds with advanced filtering and sorting.

    Args:
        project_name: Name of the project
        limit: Maximum number of builds to return
        order_by: Field to sort by (e.g., "buildDuration", "startTime")
        order_direction: Sort direction ("ASC" or "DESC")
        date: Specific date or relative date (e.g., "yesterday", "2025-11-26")
        date_range: Date range (e.g., "last_7_days", "2025-11-20..2025-11-27")
        site_name: Filter by site name
        build_name: Filter by build name pattern

    Returns:
        Tuple of (query_string, variables_dict)
    """
    # Note: date, date_range, site_name, and build_name parameters are reserved
    # for future server-side filtering when CDash GraphQL supports them.
    # Currently, these should be handled client-side after fetching results.

    variables = {"projectName": project_name, "first": limit}

    # Build the query
    query = """
    query GetBuilds($projectName: String!, $first: Int!) {
      project(name: $projectName) {
        id
        name
        builds(first: $first) {
          edges {
            node {
              id
              name
              stamp
              startTime
              endTime
              buildDuration
              configureDuration
              testDuration
              buildErrorsCount
              buildWarningsCount
              site {
                name
              }
            }
          }
        }
      }
    }
    """

    return (query, variables)


def format_schema_type(type_info: Dict[str, Any], indent: int = 0) -> str:
    """Format a GraphQL type for display.

    Args:
        type_info: Type information from schema introspection
        indent: Indentation level

    Returns:
        Formatted string representation
    """
    ind = "  " * indent
    output = []

    name = type_info.get("name", "Unknown")
    kind = type_info.get("kind", "OBJECT")
    description = type_info.get("description", "")

    # Skip internal types
    if name.startswith("__"):
        return ""

    output.append(f"{ind}**{name}** ({kind})")
    if description:
        output.append(f"{ind}  {description}")

    fields = type_info.get("fields", [])
    if fields and len(fields) > 0:
        output.append(f"{ind}  Fields:")
        for field in fields[:10]:  # Limit to first 10 fields
            field_name = field.get("name", "unknown")
            field_desc = field.get("description", "")
            output.append(f"{ind}    - {field_name}: {field_desc or 'No description'}")

        if len(fields) > 10:
            output.append(f"{ind}    ... and {len(fields) - 10} more fields")

    return "\n".join(output)
