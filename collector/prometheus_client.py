import requests
from datetime import datetime, timedelta, timezone

PROMETHEUS_URL = "http://localhost:9090"
QUERY = "system_utilization_percent"


def get_metrics(minutes=10):
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)

    params = {
        "query": QUERY,
        "start": start.timestamp(),
        "end": end.timestamp(),
        "step": 5,
    }

    response = requests.get(
        f"{PROMETHEUS_URL}/api/v1/query_range",
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    if data["status"] != "success":
        raise RuntimeError(data)

    return data["data"]["result"]


if __name__ == "__main__":
    results = get_metrics()

    print(f"Séries encontradas: {len(results)}")

    for series in results:
        print("\nMétrica:")
        print(series["metric"])

        values = series["values"]

        print(f"Quantidade de pontos: {len(values)}")

        print("\nÚltimos 10 valores:")

        for timestamp, value in values[-10:]:
            dt = datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc,
            )

            print(
                f"{dt.strftime('%H:%M:%S')} -> {value}"
            )
