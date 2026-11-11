
import ast
import json
import math
import operator
import re
import sqlite3
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MCP Agent Tools")

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sample.db"


# TOOL 1: Safe, read-only SQL queries
@mcp.tool()
def query_database(sql: str) -> str:
    """Run a safe, read-only SELECT query on the SQLite database."""

    cleaned_sql = sql.strip()

    if not cleaned_sql:
        return "Error: SQL query cannot be empty."

    if ";" in cleaned_sql or "--" in cleaned_sql or "/*" in cleaned_sql:
        return "Error: Multiple statements and SQL comments are not allowed."

    if not re.match(r"^SELECT\b", cleaned_sql, re.IGNORECASE):
        return "Error: Only SELECT queries are allowed."

    forbidden = r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|DETACH|PRAGMA|REPLACE|VACUUM)\b"

    if re.search(forbidden, cleaned_sql, re.IGNORECASE):
        return "Error: This SQL operation is not allowed."

    if not DB_PATH.exists():
        return "Error: Database not found. Please create the sample database."

    try:
        db_uri = f"{DB_PATH.resolve().as_uri()}?mode=ro"

        with sqlite3.connect(db_uri, uri=True, timeout=5) as connection:
            connection.execute("PRAGMA query_only = ON")
            connection.row_factory = sqlite3.Row
            rows = connection.execute(cleaned_sql).fetchmany(100)

        return json.dumps([dict(row) for row in rows], default=str)

    except sqlite3.Error as error:
        return f"Database error: {error}"


# TOOL 2: Live weather information
@mcp.tool()
async def get_weather(city: str) -> str:
    """Find a city and return its current weather using Open-Meteo."""

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            geo_response = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1}
            )
            geo_response.raise_for_status()
            places = geo_response.json().get("results", [])

            if not places:
                return "Error: City not found."

            place = places[0]

            weather_response = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": place["latitude"],
                    "longitude": place["longitude"],
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m"
                }
            )
            weather_response.raise_for_status()
            weather = weather_response.json().get("current", {})

            result = {
                "city": place.get("name"),
                "country": place.get("country"),
                "temperature_celsius": weather.get("temperature_2m"),
                "humidity_percent": weather.get("relative_humidity_2m"),
                "wind_speed_kmh": weather.get("wind_speed_10m")
            }

            return json.dumps(result)

    except (httpx.HTTPError, KeyError, ValueError):
        return "Error: Weather service is unavailable. Please try again."


# TOOL 3: Safe math calculator (no eval or exec)
@mcp.tool()
def calculate(expression: str) -> str:
    """Safely calculate basic math expressions."""

    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }

    def calculate_node(node):
        if isinstance(node, ast.Expression):
            return calculate_node(node.body)

        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value

        if isinstance(node, ast.BinOp) and type(node.op) in allowed_operators:
            left = calculate_node(node.left)
            right = calculate_node(node.right)

            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("Exponent is too large.")

            result = allowed_operators[type(node.op)](left, right)

            if not math.isfinite(result) or abs(result) > 1e100:
                raise ValueError("Result is too large.")

            return result

        if isinstance(node, ast.UnaryOp) and isinstance(
            node.op, (ast.UAdd, ast.USub)
        ):
            value = calculate_node(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value

        raise ValueError("Only basic math operations are allowed.")

    try:
        if len(expression) > 100:
            return "Error: Expression is too long."

        tree = ast.parse(expression, mode="eval")
        result = calculate_node(tree)

        return str(result)

    except (ValueError, TypeError, SyntaxError, ZeroDivisionError, OverflowError):
        return "Error: Invalid or unsafe math expression."


if __name__ == "__main__":
    mcp.run()
