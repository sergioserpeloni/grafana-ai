import sqlite3
from pathlib import Path
import statistics


DB_PATH = Path(__file__).resolve().parent / "metrics.db"


def analyze():
    connection = sqlite3.connect(DB_PATH)

    rows = connection.execute("""
        SELECT timestamp, value
        FROM metrics
        ORDER BY timestamp
    """).fetchall()

    connection.close()

    if not rows:
        print("Nenhum dado encontrado.")
        return

    values = [row[1] for row in rows]

    mean = statistics.mean(values)
    minimum = min(values)
    maximum = max(values)
    std_dev = statistics.stdev(values) if len(values) > 1 else 0

    anomalies = [value for value in values if value > 70]

    print("=" * 50)
    print("ANÁLISE DA MÉTRICA")
    print("=" * 50)

    print(f"Total de pontos:       {len(values)}")
    print(f"Média:                 {mean:.2f}")
    print(f"Mínimo:                {minimum:.2f}")
    print(f"Máximo:                {maximum:.2f}")
    print(f"Desvio padrão:         {std_dev:.2f}")
    print(f"Valores > 70:          {len(anomalies)}")

    if anomalies:
        print()
        print("Possíveis anomalias:")

        for value in anomalies:
            print(f"  {value:.2f}")

    print("=" * 50)


if __name__ == "__main__":
    analyze()
