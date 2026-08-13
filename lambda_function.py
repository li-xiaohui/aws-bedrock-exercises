import json
import os
import shutil
import sqlite3

# /var/task is read-only in Lambda, so copy the bundled DB to /tmp on cold
# start and mutate that copy. Writes therefore persist only for the lifetime
# of a single Lambda container -- fine for this demo, not for production.
BUNDLED_DB = "/var/task/employee_database.db"
DB_PATH = "/tmp/employee_database.db"

if not os.path.exists(DB_PATH):
    shutil.copyfile(BUNDLED_DB, DB_PATH)


def _connect():
    return sqlite3.connect(DB_PATH)


def get_available_vacations_days(employee_id):
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT employee_vacation_days_available
            FROM vacations
            WHERE employee_id = ?
            ORDER BY year DESC
            LIMIT 1
            """,
            (employee_id,),
        ).fetchone()
    if row is None:
        return {"error": f"No vacation data found for employee_id {employee_id}"}
    return {"employee_id": employee_id, "available_vacation_days": row[0]}


def reserve_vacation_time(employee_id, start_date, end_date=None):
    """Reserve vacation time for an employee.

    - Adds a row to planned_vacations covering [start_date, end_date] (inclusive
      of start_date, exclusive of end_date to match the seed data's convention).
    - Decrements employee_vacation_days_available on the current-year row of
      vacations by the number of days reserved.
    - If end_date is omitted, reserves a single day (start_date only).
    """
    from datetime import date as _date

    if end_date is None:
        end_date = start_date
    try:
        start = _date.fromisoformat(start_date)
        end = _date.fromisoformat(end_date)
    except ValueError as exc:
        return {"error": f"Invalid date: {exc}. Use YYYY-MM-DD."}

    days = (end - start).days + 1  # inclusive of both endpoints
    if days <= 0:
        return {"error": "end_date must be on or after start_date"}

    with _connect() as conn:
        row = conn.execute(
            """
            SELECT employee_vacation_days_available, year
            FROM vacations
            WHERE employee_id = ?
            ORDER BY year DESC
            LIMIT 1
            """,
            (employee_id,),
        ).fetchone()
        if row is None:
            return {"error": f"No vacation record for employee_id {employee_id}"}
        available, year = row
        if available < days:
            return {
                "error": (
                    f"Not enough vacation days: requested {days}, "
                    f"available {available}"
                )
            }

        conn.execute(
            """
            INSERT INTO planned_vacations
                (employee_id, vacation_start_date, vacation_end_date, vacation_days_taken)
            VALUES (?, ?, ?, ?)
            """,
            (employee_id, start_date, end_date, days),
        )
        conn.execute(
            """
            UPDATE vacations
            SET employee_vacation_days_taken =
                    employee_vacation_days_taken + ?,
                employee_vacation_days_available =
                    employee_vacation_days_available - ?
            WHERE employee_id = ? AND year = ?
            """,
            (days, days, employee_id, year),
        )
        conn.commit()

    return {
        "employee_id": employee_id,
        "reserved_start_date": start_date,
        "reserved_end_date": end_date,
        "days_reserved": days,
        "remaining_vacation_days": available - days,
        "status": "confirmed",
    }


# Dispatch table: the notebook passes tool_name in the event so one Lambda
# can serve multiple AgentCore tools.
TOOLS = {
    "get_available_vacations_days": get_available_vacations_days,
    "reserve_vacation_time": reserve_vacation_time,
}


def lambda_handler(event, context):
    tool_name = event.get("tool_name")
    if not tool_name:
        # Back-compat: older callers sent {"employee_id": N} with no tool_name.
        tool_name = "get_available_vacations_days"

    fn = TOOLS.get(tool_name)
    if fn is None:
        return {"statusCode": 400, "body": {"error": f"unknown tool: {tool_name}"}}

    kwargs = {k: v for k, v in event.items() if k != "tool_name"}
    try:
        if "employee_id" in kwargs:
            kwargs["employee_id"] = int(kwargs["employee_id"])
    except (TypeError, ValueError):
        return {"statusCode": 400, "body": {"error": "employee_id must be an integer"}}

    try:
        result = fn(**kwargs)
    except TypeError as exc:
        return {"statusCode": 400, "body": {"error": f"bad arguments: {exc}"}}
    return {"statusCode": 200, "body": result}
