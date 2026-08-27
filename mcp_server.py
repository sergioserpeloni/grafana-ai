import os
import requests

from mcp.server.fastmcp import FastMCP


GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN")

mcp = FastMCP("grafana-observability")


def grafana_headers():
    if not GRAFANA_TOKEN:
        raise RuntimeError(
            "GRAFANA_TOKEN não está configurado."
        )

    return {
        "Authorization": f"Bearer {GRAFANA_TOKEN}",
        "Content-Type": "application/json",
    }


def get_dashboard(dashboard_uid):
    url = f"{GRAFANA_URL}/api/dashboards/uid/{dashboard_uid}"

    response = requests.get(
        url,
        headers=grafana_headers(),
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def get_panel_data(
    dashboard_uid: str,
    panel_id: int,
) -> dict:
    """
    Obtém os dados de um painel diretamente do Grafana.

    O MCP consulta a configuração do dashboard para descobrir
    automaticamente o datasource e a query do painel e depois
    solicita os dados ao Grafana.
    """

    dashboard_response = get_dashboard(dashboard_uid)

    dashboard = dashboard_response["dashboard"]

    panel = None

    for item in dashboard.get("panels", []):
        if item.get("id") == panel_id:
            panel = item
            break

    if panel is None:
        raise ValueError(
            f"Painel {panel_id} não encontrado "
            f"no dashboard {dashboard_uid}"
        )

    if panel.get("type") != "timeseries":
        raise ValueError(
            f"O painel {panel_id} não é um Time Series. "
            f"Tipo encontrado: {panel.get('type')}"
        )

    targets = panel.get("targets", [])

    if not targets:
        raise ValueError(
            f"O painel {panel_id} não possui queries."
        )

    queries = []

    for target in targets:

        if target.get("hide", False):
            continue

        datasource = target.get(
            "datasource",
            panel.get("datasource")
        )

        query = {
            "refId": target.get("refId", "A"),
            "datasource": datasource,
            "expr": target.get("expr"),
            "intervalMs": 5000,
            "maxDataPoints": 1000,
        }

        queries.append(query)

    payload = {
        "queries": queries,
        "from": dashboard.get(
            "time",
            {}
        ).get("from", "now-15m"),
        "to": dashboard.get(
            "time",
            {}
        ).get("to", "now"),
    }

    response = requests.post(
        f"{GRAFANA_URL}/api/ds/query",
        headers=grafana_headers(),
        json=payload,
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()

    return {
        "dashboard": {
            "uid": dashboard.get("uid"),
            "title": dashboard.get("title"),
        },
        "panel": {
            "id": panel.get("id"),
            "title": panel.get("title"),
            "type": panel.get("type"),
        },
        "queries": queries,
        "time_range": {
            "from": payload["from"],
            "to": payload["to"],
        },
        "data": data,
    }


if __name__ == "__main__":
    mcp.run()
