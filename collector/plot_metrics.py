import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt


DB_PATH = Path(__file__).resolve().parent / "metrics.db"


def load_metrics():
    connection = sqlite3.connect(DB_PATH)

    rows = connection.execute("""
        SELECT timestamp, value
        FROM metrics
        ORDER BY timestamp
    """).fetchall()

    connection.close()

    return rows


def plot_metrics(rows):
    timestamps = [row[0] for row in rows]
    values = [row[1] for row in rows]

    # Consideramos o início de um possível evento
    # quando a métrica ultrapassa 85%.
    anomaly_x = []
    anomaly_y = []

    for timestamp, value in rows:
        if value >= 85:
            anomaly_x.append(timestamp)
            anomaly_y.append(value)

    plt.figure(figsize=(12, 6))

    plt.plot(
        timestamps,
        values,
        marker="o",
        markersize=3,
        linewidth=1,
        label="System utilization"
    )

    if anomaly_x:
        plt.scatter(
            anomaly_x,
            anomaly_y,
            s=50,
            label="Possible anomaly"
        )

    plt.axhline(
        y=70,
        linestyle="--",
        linewidth=1,
        label="Threshold 70%"
    )

    plt.axhline(
        y=85,
        linestyle="--",
        linewidth=1,
        label="Anomaly trigger 85%"
    )

    plt.title("System Utilization - Histórico")
    plt.xlabel("Timestamp")
    plt.ylabel("Utilization (%)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    output = Path(__file__).resolve().parent / "metrics.png"
    plt.savefig(output, dpi=150)

    print(f"Gráfico salvo em: {output}")


if __name__ == "__main__":
    rows = load_metrics()

    print(f"Pontos carregados: {len(rows)}")

    if rows:
        plot_metrics(rows)
    else:
        print("Nenhum dado encontrado.")
