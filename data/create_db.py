
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "sample.db"

connection = sqlite3.connect(db_path)

connection.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    salary REAL NOT NULL
)
""")

connection.execute("DELETE FROM employees")

connection.executemany(
    "INSERT INTO employees (name, department, salary) VALUES (?, ?, ?)",
    [
        ("Alice", "IT", 75000),
        ("Bob", "HR", 65000),
        ("Sarah", "Engineering", 90000),
    ]
)

connection.commit()
connection.close()

print("Sample database created successfully!")
