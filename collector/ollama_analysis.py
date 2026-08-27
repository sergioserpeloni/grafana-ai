import sqlite3
import requests
import statistics
from datetime import datetime


DB = "collector/metrics.db"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma3:4b"


def load_metrics():
    db = sqlite3.connect(DB)

    rows = db.execute("""
        SELECT timestamp, value
        FROM metrics
        ORDER BY timestamp
    """).fetchall()

    db.close()

    return rows


def summarize_metrics(rows):
    values = [value for _, value in rows]

    minimum = min(values)
    maximum = max(values)
    average = statistics.mean(values)
    std = statistics.pstdev(values)

    # Principais variações entre pontos consecutivos
    variations = []

    for i in range(1, len(rows)):
        timestamp = rows[i][0]
        previous = rows[i - 1][1]
        current = rows[i][1]

        jump = current - previous

        variations.append(
            (
                abs(jump),
                timestamp,
                previous,
                current,
                jump
            )
        )

    variations.sort(reverse=True)

    largest_variations = variations[:10]

    # Valores mais altos
    highest = sorted(
        rows,
        key=lambda x: x[1],
        reverse=True
    )[:10]

    start_time = datetime.fromtimestamp(
        rows[0][0]
    ).strftime("%H:%M:%S")

    end_time = datetime.fromtimestamp(
        rows[-1][0]
    ).strftime("%H:%M:%S")

    summary = []

    summary.append(
        f"Período: {start_time} até {end_time}"
    )

    summary.append(
        f"Quantidade de pontos: {len(rows)}"
    )

    summary.append(
        f"Mínimo: {minimum:.2f}%"
    )

    summary.append(
        f"Máximo: {maximum:.2f}%"
    )

    summary.append(
        f"Média: {average:.2f}%"
    )

    summary.append(
        f"Desvio padrão: {std:.2f}"
    )

    summary.append("")
    summary.append("10 maiores valores:")

    for timestamp, value in highest:
        time = datetime.fromtimestamp(
            timestamp
        ).strftime("%H:%M:%S")

        summary.append(
            f"{time} -> {value:.2f}%"
        )

    summary.append("")
    summary.append("10 maiores variações:")

    for _, timestamp, previous, current, jump in largest_variations:

        time = datetime.fromtimestamp(
            timestamp
        ).strftime("%H:%M:%S")

        summary.append(
            f"{time}: "
            f"{previous:.2f}% -> "
            f"{current:.2f}% "
            f"(variação {jump:+.2f})"
        )

    return "\n".join(summary)


def analyze_with_ollama(summary):

    prompt = f"""
Você é um analista de monitoramento de infraestrutura.

Analise a série temporal de utilização de CPU abaixo.

Seu objetivo é interpretar o comportamento dos dados.

Explique:

1. Qual foi o comportamento geral da utilização.
2. Qual foi o nível típico de utilização.
3. Quais foram os períodos de maior utilização.
4. Se ocorreram mudanças bruscas relevantes.
5. Se existe algum comportamento que mereça investigação.
6. Qual seria a conclusão geral sobre essa série temporal.

IMPORTANTE:

- Baseie sua análise somente nos dados fornecidos.
- Não invente causas.
- Não diga que existe um problema apenas porque a utilização aumentou.
- Diferencie observação de hipótese.
- Seja objetivo.
- Gere um relatório curto.

DADOS:

{summary}
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 500
            }
        },
        timeout=300
    )

    response.raise_for_status()

    return response.json()["response"]


def main():

    print()
    print("=" * 60)
    print(" ANÁLISE DA SÉRIE TEMPORAL COM IA LOCAL")
    print("=" * 60)
    print()

    rows = load_metrics()

    print(f"Pontos analisados: {len(rows)}")
    print()

    summary = summarize_metrics(rows)

    print("Resumo enviado para a IA:")
    print()
    print(summary)
    print()

    print("=" * 60)
    print(" CONSULTANDO GEMMA 3 4B...")
    print("=" * 60)
    print()

    report = analyze_with_ollama(summary)

    print("=" * 60)
    print(" RELATÓRIO DA IA")
    print("=" * 60)
    print()

    print(report)

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
