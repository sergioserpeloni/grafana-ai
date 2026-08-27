import sqlite3
from datetime import datetime

DB = "collector/metrics.db"

HIGH_THRESHOLD = 85
JUMP_THRESHOLD = 8
EVENT_GAP = 10


def load_data():
    db = sqlite3.connect(DB)

    rows = db.execute(
        """
        SELECT timestamp, value
        FROM metrics
        ORDER BY timestamp
        """
    ).fetchall()

    db.close()

    return rows


def create_events_table():
    db = sqlite3.connect(DB)

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS anomaly_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_timestamp REAL NOT NULL,
            end_timestamp REAL NOT NULL,
            duration REAL NOT NULL,
            initial_value REAL NOT NULL,
            peak_value REAL NOT NULL,
            peak_timestamp REAL NOT NULL,
            initial_jump REAL NOT NULL,
            score REAL NOT NULL,
            severity TEXT NOT NULL,
            UNIQUE(start_timestamp, end_timestamp)
        )
        """
    )

    db.commit()
    db.close()


def save_events(events):
    db = sqlite3.connect(DB)

    for event in events:
        db.execute(
            """
            INSERT OR IGNORE INTO anomaly_events
            (
                start_timestamp,
                end_timestamp,
                duration,
                initial_value,
                peak_value,
                peak_timestamp,
                initial_jump,
                score,
                severity
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["start_timestamp"],
                event["end_timestamp"],
                event["duration"],
                event["initial_value"],
                event["peak_value"],
                event["peak_timestamp"],
                event["initial_jump"],
                event["score"],
                event["severity"],
            )
        )

    db.commit()
    db.close()


def format_time(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")


def detect_events(rows):

    anomaly_points = []

    for i in range(1, len(rows)):

        timestamp, value = rows[i]

        previous_timestamp, previous_value = rows[i - 1]

        jump = value - previous_value

        is_anomaly = (
            value >= HIGH_THRESHOLD
            or abs(jump) >= JUMP_THRESHOLD
        )

        if is_anomaly:
            anomaly_points.append(
                {
                    "timestamp": timestamp,
                    "value": value,
                    "previous_value": previous_value,
                    "jump": jump
                }
            )

    events = []

    if not anomaly_points:
        return events

    current = [anomaly_points[0]]

    for point in anomaly_points[1:]:

        gap = point["timestamp"] - current[-1]["timestamp"]

        if gap <= EVENT_GAP:
            current.append(point)
        else:
            events.append(build_event(current))
            current = [point]

    events.append(build_event(current))

    return events


def build_event(points):

    first = points[0]
    last = points[-1]

    peak = max(points, key=lambda x: x["value"])

    initial_jump = first["jump"]

    if (
        abs(initial_jump) >= 15
        or peak["value"] >= 90
    ):
        score = 1.00
        severity = "CRÍTICA"

    elif (
        abs(initial_jump) >= 8
        or peak["value"] >= 85
    ):
        score = 0.90
        severity = "ALTA"

    else:
        score = 0.50
        severity = "MODERADA"

    return {
        "start_timestamp": first["timestamp"],
        "end_timestamp": last["timestamp"],
        "duration": last["timestamp"] - first["timestamp"],
        "initial_value": first["previous_value"],
        "peak_value": peak["value"],
        "peak_timestamp": peak["timestamp"],
        "initial_jump": initial_jump,
        "score": score,
        "severity": severity
    }


def main():

    create_events_table()

    rows = load_data()

    print()
    print("======================================")
    print(" DETECTOR DE EVENTOS DE ANOMALIAS")
    print("======================================")
    print()

    print(f"Total de pontos: {len(rows)}")
    print()

    events = detect_events(rows)

    print("EVENTOS DE ANOMALIA:")
    print()

    for index, event in enumerate(events, start=1):

        print(f"EVENTO #{index}")

        print(
            f"Início:        "
            f"{format_time(event['start_timestamp'])}"
        )

        print(
            f"Fim:           "
            f"{format_time(event['end_timestamp'])}"
        )

        print(
            f"Duração:       "
            f"{event['duration']:.0f}s"
        )

        print(
            f"Valor inicial: "
            f"{event['initial_value']:.2f}%"
        )

        print(
            f"Salto inicial: "
            f"{event['initial_jump']:+.2f}"
        )

        print(
            f"Pico:          "
            f"{event['peak_value']:.2f}% "
            f"({format_time(event['peak_timestamp'])})"
        )

        print(
            f"Score:         "
            f"{event['score']:.2f}"
        )

        print(
            f"Severidade:    "
            f"{event['severity']}"
        )

        print()

    save_events(events)

    print("--------------------------------------")
    print(f"Total de eventos: {len(events)}")
    print("Eventos salvos no SQLite.")
    print("--------------------------------------")


if __name__ == "__main__":
    main()
