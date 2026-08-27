import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "metrics.db"


def create_database():
    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            metric_name TEXT NOT NULL,
            value REAL NOT NULL,
            instance TEXT,
            job TEXT
        )
    """)

    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_database()
    print(f"Banco criado em: {DB_PATH}")
