
from server.mcp_server import calculate, query_database


def test_calculate_addition():
    assert calculate("10 + 5") == "15"


def test_calculate_multiplication():
    assert calculate("250 * 4") == "1000"


def test_calculate_division():
    assert calculate("20 / 4") == "5.0"


def test_calculate_blocks_unsafe_python():
    result = calculate("__import__('os').system('whoami')")
    assert "error" in result.lower()


def test_calculate_blocks_large_exponent():
    result = calculate("2 ** 100")
    assert "error" in result.lower()


def test_database_allows_select():
    result = query_database("SELECT * FROM employees")
    assert "Alice" in str(result)


def test_database_blocks_delete():
    result = query_database("DELETE FROM employees")
    assert "error" in str(result).lower()
