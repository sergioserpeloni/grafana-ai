from prometheus_client import get_metrics
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "metrics.db"


def save_metrics(results):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    total = 0

    for series in results:
        metric = series["metric"]

        metric_name = metric.get("__name__")
        instance = metric.get("instance")
        job = metric.get("job")

        for timestamp, value in series["values"]:
            cursor.execute(
                """
                INSERT INTO metrics (
                    timestamp,
                    metric_name,
                    value,
                    instance,
                    job
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    metric_name,
                    float(value),
                    instance,
                    job,
                ),
            )

            total += 1

    connection.commit()
    connection.close()

    return total


if __name__ == "__main__":
    results = get_metrics(minutes=10)

    total = save_metrics(results)

    print(f"Dados recebidos: {total}")
    print(f"Banco: {DB_PATH}")
