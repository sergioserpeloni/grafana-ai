import asyncio
import json
import os
import requests

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ============================================================
# CONFIGURAÇÕES
# ============================================================

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/generate"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "gemma3:4b"
)

DASHBOARD_UID = os.getenv(
    "DASHBOARD_UID",
    "ad7xgr9"
)

PANEL_ID = int(
    os.getenv(
        "PANEL_ID",
        "1"
    )
)

GRAFANA_URL = os.getenv(
    "GRAFANA_URL",
    "http://localhost:3000"
)

GRAFANA_TOKEN = os.getenv(
    "GRAFANA_TOKEN"
)


# ============================================================
# CONFIGURAÇÃO DA IA
# ============================================================

OLLAMA_CONTEXT = int(
    os.getenv(
        "OLLAMA_CONTEXT",
        "8192"
    )
)

OLLAMA_TEMPERATURE = float(
    os.getenv(
        "OLLAMA_TEMPERATURE",
        "0.1"
    )
)

MAX_RETRIES = 2


# ============================================================
# MCP
# ============================================================

async def get_grafana_panel_data():

    """
    Consulta o MCP e obtém os dados brutos do painel
    diretamente do Grafana.

    Esta função NÃO realiza análise estatística.
    """

    if not GRAFANA_TOKEN:
        raise RuntimeError(
            "GRAFANA_TOKEN não está configurado."
        )

    server_params = StdioServerParameters(

        command="python",

        args=[
            "mcp_server.py"
        ],

        env={
            **os.environ,

            "GRAFANA_TOKEN":
                GRAFANA_TOKEN,

            "GRAFANA_URL":
                GRAFANA_URL,
        },
    )

    async with stdio_client(
        server_params
    ) as (read, write):

        async with ClientSession(
            read,
            write
        ) as session:

            await session.initialize()

            result = await session.call_tool(

                "get_panel_data",

                {
                    "dashboard_uid":
                        DASHBOARD_UID,

                    "panel_id":
                        PANEL_ID,
                },
            )

            for content in result.content:

                if not hasattr(
                    content,
                    "text"
                ):
                    continue

                text = content.text

                try:

                    return json.loads(
                        text
                    )

                except json.JSONDecodeError as exc:

                    raise RuntimeError(
                        "O MCP retornou conteúdo "
                        "que não é JSON válido.\n\n"
                        f"Conteúdo recebido:\n{text}"
                    ) from exc


    raise RuntimeError(
        "Não foi possível obter os dados "
        "do Grafana através do MCP."
    )


# ============================================================
# EXTRAÇÃO DOS DADOS
# ============================================================

def extract_raw_series(
    mcp_result
):

    """
    Extrai a série temporal do resultado do Grafana.

    IMPORTANTE:

    Esta função NÃO calcula estatísticas.

    Ela apenas extrai:

        timestamp
        value
    """

    data = mcp_result.get(
        "data",
        {}
    )

    results = data.get(
        "results",
        {}
    )

    if not results:

        raise RuntimeError(
            "O Grafana não retornou resultados."
        )

    series = []

    for ref_id, result in results.items():

        frames = result.get(
            "frames",
            []
        )

        for frame in frames:

            schema = frame.get(
                "schema",
                {}
            )

            frame_data = frame.get(
                "data",
                {}
            )

            fields = schema.get(
                "fields",
                []
            )

            values = frame_data.get(
                "values",
                []
            )

            if not fields or not values:
                continue

            timestamp_index = None
            value_index = None

            for index, field in enumerate(
                fields
            ):

                field_name = (
                    field
                    .get("name", "")
                    .lower()
                    .strip()
                )

                if field_name in (
                    "time",
                    "timestamp",
                ):

                    timestamp_index = index

                elif field_name in (
                    "value",
                    "system_utilization_percent",
                ):

                    value_index = index

            if (
                timestamp_index is None
                or
                value_index is None
            ):

                continue

            timestamps = values[
                timestamp_index
            ]

            metric_values = values[
                value_index
            ]

            for timestamp, value in zip(
                timestamps,
                metric_values
            ):

                if timestamp is None:
                    continue

                if value is None:
                    continue

                series.append(
                    {
                        "timestamp":
                            timestamp,

                        "value":
                            value,
                    }
                )

    if not series:

        raise RuntimeError(
            "Nenhuma série temporal "
            "foi identificada."
        )

    return series


# ============================================================
# REPRESENTAÇÃO DOS DADOS
# ============================================================

def compact_series(
    series
):

    """
    Converte:

        {
            timestamp: ...,
            value: ...
        }

    para:

        [
            timestamp,
            value
        ]

    Nenhum ponto é removido.
    """

    return [
        [
            point["timestamp"],
            point["value"]
        ]
        for point in series
    ]


def detailed_series(
    series
):

    """
    Representação textual mais explícita dos dados.

    Ajuda modelos menores como Gemma 3 4B
    a entender que cada linha representa
    um ponto temporal independente.
    """

    lines = []

    for point in series:

        lines.append(
            f'timestamp={point["timestamp"]} '
            f'valor={point["value"]}'
        )

    return "\n".join(
        lines
    )


# ============================================================
# PROMPT DE ANÁLISE
# ============================================================

def build_analysis_prompt(
    series,
    attempt=1
):

    compact_data = compact_series(
        series
    )

    data_json = json.dumps(
        compact_data,
        ensure_ascii=False,
        separators=(",", ":")
    )

    #detailed_data = detailed_series(
    #    series
    #)

    point_count = len(
        series
    )

    first_point = series[0]
    last_point = series[-1]

    prompt = f"""
Você é um especialista sênior em observabilidade,
monitoramento de infraestrutura e análise de séries temporais.

Você recebeu uma série temporal REAL diretamente do Grafana
através de um MCP.

A série possui EXATAMENTE {point_count} pontos.

PRIMEIRO PONTO:

timestamp={first_point["timestamp"]}
valor={first_point["value"]}

ÚLTIMO PONTO:

timestamp={last_point["timestamp"]}
valor={last_point["value"]}

Esta é a tentativa de análise número {attempt}.

============================================================
REGRA FUNDAMENTAL
============================================================

ANALISE TODA A SÉRIE.

Você DEVE considerar os {point_count} pontos.

NÃO analise somente o primeiro ponto.

NÃO analise somente o último ponto.

NÃO selecione alguns pontos aleatórios.

NÃO descarte pontos.

NÃO diga que existe apenas um ponto.

NÃO confunda a quantidade de pontos com o conteúdo
de uma única observação.

Cada linha abaixo representa um ponto real da série.

============================================================
IDIOMA
============================================================

Responda EXCLUSIVAMENTE em PORTUGUÊS DO BRASIL.

============================================================
RESPONSABILIDADE DA ANÁLISE
============================================================

A interpretação da série deve ser realizada pela IA.

O Python NÃO calculou:

- média;
- mediana;
- mínimo;
- máximo;
- desvio padrão;
- variância;
- correlação;
- tendência estatística;
- anomalias;
- ciclos;
- regressão;
- estatísticas.

Não invente números estatísticos.

Utilize somente os valores existentes na série.

============================================================
OBJETIVO
============================================================

Faça uma análise de observabilidade da série.

Procure identificar:

1. comportamento geral;
2. estabilidade;
3. oscilações;
4. ciclos;
5. recorrências;
6. períodos de subida;
7. períodos de descida;
8. picos;
9. vales;
10. mudanças bruscas;
11. mudanças persistentes de comportamento;
12. possíveis anomalias;
13. períodos que merecem atenção.

============================================================
ANÁLISE TEMPORAL
============================================================

Observe a ordem cronológica dos pontos.

Não conclua que existe tendência de alta somente porque
o último valor é maior que o primeiro.

Não conclua que existe tendência de baixa somente porque
o último valor é menor que o primeiro.

Uma série pode apresentar:

- ciclos;
- oscilações;
- comportamento repetitivo;
- alternância entre níveis;
- períodos estáveis;
- mudanças de regime.

Se houver comportamento recorrente, descreva-o.

Exemplo:

"Observa-se recorrência de períodos de elevação seguidos
por quedas e posterior recuperação."

Não invente periodicidade.

Só mencione periodicidade se ela for claramente observável
nos dados.

============================================================
EVENTOS RELEVANTES
============================================================

Quando identificar um evento relevante, utilize SEMPRE
os timestamps reais presentes nos dados.

NUNCA escreva:

- "ponto 130";
- "ponto 150";
- "pontos 130 a 160";
- "índice 50";
- "observação 20".

Em vez disso, informe:

- timestamp inicial;
- timestamp final, quando aplicável;
- valor aproximado observado;
- descrição do comportamento.

Exemplo:

"Entre timestamp X e timestamp Y ocorreu uma queda
progressiva do valor aproximadamente A para B."

Não invente timestamps.

Utilize somente timestamps presentes nos dados.

============================================================
PICOS E VALES
============================================================

Um pico ou vale isolado NÃO deve ser automaticamente
classificado como anomalia.

Primeiro compare mentalmente o comportamento com o restante
da série.

Se valores semelhantes ocorrerem repetidamente,
considere que eles podem fazer parte do comportamento normal.

============================================================
ANOMALIAS
============================================================

Uma anomalia deve representar um comportamento que se
destaca do padrão observado na própria série.

Considere:

- intensidade;
- duração;
- mudança brusca;
- isolamento;
- recorrência;
- diferença em relação ao comportamento predominante;
- mudança de regime.

Não classifique automaticamente:

- valores altos como anomalia;
- valores baixos como anomalia;
- picos como anomalia;
- quedas como anomalia.

Se não houver evidência suficiente para afirmar que existe
uma anomalia, escreva claramente:

"Não há evidência suficiente na série temporal para
classificar um evento como anomalia."

============================================================
CAUSAS
============================================================

NÃO INVENTE CAUSAS.

A série contém apenas:

timestamp
valor

Portanto NÃO atribua causas como:

- aumento de demanda;
- queda de demanda;
- problema de CPU;
- problema de memória;
- problema de disco;
- problema de rede;
- falha de servidor;
- falha de aplicação;
- usuários;
- tráfego;
- incidente externo;
- sobrecarga;
- manutenção;
- indisponibilidade.

A menos que isso esteja explicitamente representado
nos dados, não faça essas afirmações.

Quando uma causa não puder ser determinada, utilize:

"A causa não pode ser determinada somente pela série temporal."

============================================================
IMPACTO OPERACIONAL
============================================================

Não invente impacto operacional.

Não afirme:

- indisponibilidade;
- degradação;
- perda de usuários;
- perda financeira;
- falha de aplicação;
- incidente;
- indisponibilidade de serviço;

sem evidência direta na série.

Se não houver evidência suficiente:

"O impacto operacional não pode ser determinado
somente pela série temporal."

============================================================
IMPORTANTE SOBRE O PRIMEIRO E ÚLTIMO PONTO
============================================================

O primeiro valor é:

{first_point["value"]}

O último valor é:

{last_point["value"]}

Eles são apenas referências.

Não utilize somente esses dois pontos para determinar
o comportamento completo da série.

============================================================
QUALIDADE DA ANÁLISE
============================================================

A análise deve ser específica.

EVITE frases genéricas como:

"A série apresenta comportamento complexo."

"A série apresenta volatilidade."

"A série precisa ser monitorada."

Essas frases somente são úteis quando acompanhadas
de evidências observadas na série.

Prefira:

"Observa-se uma sequência recorrente de elevação,
seguida por queda e posterior recuperação."

ou:

"Entre timestamp X e timestamp Y observa-se uma mudança
brusca do valor A para aproximadamente B."

============================================================
NÃO FAÇA
============================================================

Não:

- peça uma nova pergunta;
- explique como analisar séries temporais;
- escreva código;
- crie gráficos;
- crie tabelas;
- repita todos os pontos;
- invente causas;
- invente métricas;
- invente timestamps;
- invente eventos;
- use números de posição dos pontos;
- responda em inglês;
- diga que recebeu apenas um ponto.

REALIZE A ANÁLISE.

============================================================
FORMATO DA RESPOSTA
============================================================

Retorne SOMENTE JSON válido.

Não use Markdown.

Não use:

```json

Não escreva texto antes do JSON.

Não escreva texto depois do JSON.

Use exatamente esta estrutura:

{{
    "resumo_executivo": "...",
    "comportamento_da_serie": "...",
    "eventos_relevantes": "...",
    "possiveis_anomalias": "...",
    "pontos_de_atencao": "...",
    "conclusao": "..."
}}

Todos os campos são obrigatórios.

Todos os campos devem conter texto.

============================================================
DADOS COMPLETOS DA SÉRIE
============================================================

Existem exatamente {point_count} pontos.

Representação compacta:

{data_json}

============================================================
FIM DOS DADOS
============================================================

Agora analise a série completa e retorne SOMENTE o JSON.
"""

    return prompt


# ============================================================
# CHAMADA OLLAMA
# ============================================================

def call_ollama(
    prompt
):

    payload = {

        "model":
            OLLAMA_MODEL,

        "prompt":
            prompt,

        "stream":
            False,

        "format":
            "json",

        "options": {

            "temperature":
                OLLAMA_TEMPERATURE,

            "num_ctx":
                OLLAMA_CONTEXT,
        },
    }

    print(
        f"Enviando dados BRUTOS para "
        f"Ollama / {OLLAMA_MODEL}..."
    )

    print(
        "A análise será realizada "
        "exclusivamente pela IA."
    )

    print()

    response = requests.post(

        OLLAMA_URL,

        json=payload,

        timeout=300,
    )

    response.raise_for_status()

    result = response.json()

    return result.get(
        "response",
        ""
    ).strip()


# ============================================================
# CAMPOS OBRIGATÓRIOS
# ============================================================

REQUIRED_FIELDS = [

    "resumo_executivo",

    "comportamento_da_serie",

    "eventos_relevantes",

    "possiveis_anomalias",

    "pontos_de_atencao",

    "conclusao",
]


# ============================================================
# VALIDAÇÃO DO JSON
# ============================================================

def parse_structured_response(
    response
):

    if not response:
        return None

    text = response.strip()

    # --------------------------------------------------------
    # JSON direto
    # --------------------------------------------------------

    try:

        obj = json.loads(
            text
        )

        if isinstance(
            obj,
            dict
        ):

            if all(
                field in obj
                for field in REQUIRED_FIELDS
            ):

                return obj

    except json.JSONDecodeError:

        pass

    # --------------------------------------------------------
    # JSON dentro de texto
    # --------------------------------------------------------

    first = text.find(
        "{"
    )

    last = text.rfind(
        "}"
    )

    if (
        first >= 0
        and
        last > first
    ):

        candidate = text[
            first:last + 1
        ]

        try:

            obj = json.loads(
                candidate
            )

            if isinstance(
                obj,
                dict
            ):

                if all(
                    field in obj
                    for field in REQUIRED_FIELDS
                ):

                    return obj

        except json.JSONDecodeError:

            pass

    return None


# ============================================================
# VALIDAÇÃO DO CONTEÚDO
# ============================================================

def validate_analysis_content(
    report,
    series
):

    if not report:
        return False

    point_count = len(
        series
    )

    combined = " ".join(

        str(
            report.get(
                field,
                ""
            )
        )

        for field in REQUIRED_FIELDS

    ).lower()

    # --------------------------------------------------------
    # Respostas claramente erradas
    # --------------------------------------------------------

    invalid_patterns = [

        "apenas um ponto",

        "apenas 1 ponto",

        "um único ponto",

        "um unico ponto",

        "um único dado",

        "um unico dado",

        "single data point",

        "only one data point",

        "only 1 data point",

        "only one point",

        "somente um ponto",

        "somente 1 ponto",
    ]

    for pattern in invalid_patterns:

        if pattern in combined:

            return False

    # --------------------------------------------------------
    # Não permitir referência a posições fictícias
    # --------------------------------------------------------

    forbidden_patterns = [

        "ponto 130",

        "ponto 140",

        "ponto 150",

        "ponto 160",

        "pontos 130",

        "pontos 140",

        "pontos 150",

        "pontos 160",

        "índice 130",

        "indice 130",

        "índice 140",

        "indice 140",

        "índice 150",

        "indice 150",
    ]

    for pattern in forbidden_patterns:

        if pattern in combined:

            return False

    # --------------------------------------------------------
    # Verificar conteúdo mínimo
    # --------------------------------------------------------

    for field in REQUIRED_FIELDS:

        value = report.get(
            field
        )

        if not isinstance(
            value,
            str
        ):

            return False

        if len(
            value.strip()
        ) < 20:

            return False

    # --------------------------------------------------------
    # Garantir que o relatório não seja genérico demais
    # --------------------------------------------------------

    generic_patterns = [

        "a série apresenta um comportamento complexo",

        "a série apresenta volatilidade",

        "é importante monitorar",

        "monitoramento contínuo é necessário",
    ]

    generic_count = 0

    for pattern in generic_patterns:

        if pattern in combined:

            generic_count += 1

    if generic_count >= 3:

        return False

    # --------------------------------------------------------
    # A quantidade real de pontos deve ser conhecida
    # pelo modelo através do prompt.
    #
    # Aqui não fazemos nenhuma estatística.
    # Apenas garantimos que a série possui dados.
    # --------------------------------------------------------

    if point_count < 2:

        return False

    return True


# ============================================================
# SEGUNDA ANÁLISE
# ============================================================

def second_analysis(
    series
):

    """
    Executa uma NOVA análise.

    Os dados completos são enviados novamente.

    A resposta anterior não é utilizada como fonte.
    """

    print()

    print(
        "A primeira resposta foi considerada inválida."
    )

    print(
        "Executando uma NOVA análise "
        "com os dados completos..."
    )

    print()

    prompt = build_analysis_prompt(

        series,

        attempt=2
    )

    return call_ollama(
        prompt
    )


# ============================================================
# FORMATAÇÃO
# ============================================================

def format_report(
    report
):

    return f"""
RESUMO EXECUTIVO

{report["resumo_executivo"]}


COMPORTAMENTO DA SÉRIE

{report["comportamento_da_serie"]}


EVENTOS RELEVANTES

{report["eventos_relevantes"]}


POSSÍVEIS ANOMALIAS

{report["possiveis_anomalias"]}


PONTOS DE ATENÇÃO

{report["pontos_de_atencao"]}


CONCLUSÃO

{report["conclusao"]}
""".strip()


# ============================================================
# ANÁLISE PRINCIPAL
# ============================================================

def analyze_with_ollama(
    series
):

    # --------------------------------------------------------
    # PRIMEIRA ANÁLISE
    # --------------------------------------------------------

    prompt = build_analysis_prompt(

        series,

        attempt=1
    )

    raw_response = call_ollama(
        prompt
    )

    structured = parse_structured_response(
        raw_response
    )

    if structured:

        if validate_analysis_content(
            structured,
            series
        ):

            return format_report(
                structured
            )

    # --------------------------------------------------------
    # SEGUNDA ANÁLISE
    # --------------------------------------------------------

    raw_response_2 = second_analysis(
        series
    )

    structured_2 = parse_structured_response(
        raw_response_2
    )

    if structured_2:

        if validate_analysis_content(
            structured_2,
            series
        ):

            return format_report(
                structured_2
            )

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    print()

    print(
        "AVISO: O Gemma não retornou "
        "uma análise estruturada válida."
    )

    print(
        "Resposta recebida para diagnóstico:"
    )

    print()

    if raw_response_2:

        print(
            raw_response_2
        )

        return raw_response_2

    if raw_response:

        print(
            raw_response
        )

        return raw_response

    raise RuntimeError(
        "O Gemma não retornou nenhuma resposta."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()

    print(
        "=" * 60
    )

    print(
        "IA + MCP + GRAFANA"
    )

    print(
        "=" * 60
    )

    print()

    # ========================================================
    # 1. MCP
    # ========================================================

    print(
        "1. Consultando dados diretamente "
        "do Grafana via MCP..."
    )

    print()

    mcp_result = asyncio.run(
        get_grafana_panel_data()
    )

    print(
        "Dados recebidos com sucesso."
    )

    print()

    # ========================================================
    # 2. EXTRAÇÃO
    # ========================================================

    series = extract_raw_series(
        mcp_result
    )

    point_count = len(
        series
    )

    print(
        f"Pontos brutos recebidos: "
        f"{point_count}"
    )

    print()

    print(
        "O Python NÃO está realizando "
        "análise estatística."
    )

    print(
        "Os dados serão enviados "
        "integralmente para o Gemma."
    )

    print()

    # ========================================================
    # DIAGNÓSTICO DOS DADOS
    # ========================================================

    print(
        "Primeiro ponto:"
    )

    print(
        series[0]
    )

    print()

    print(
        "Último ponto:"
    )

    print(
        series[-1]
    )

    print()

    print(
        f"Pontos enviados para a IA: "
        f"{point_count}"
    )

    print()

    # ========================================================
    # 3. IA
    # ========================================================

    report = analyze_with_ollama(
        series
    )

    # ========================================================
    # 4. RESULTADO
    # ========================================================

    print()

    print(
        "=" * 60
    )

    print(
        "RELATÓRIO EXECUTIVO GERADO PELA IA"
    )

    print(
        "=" * 60
    )

    print()

    print(
        report
    )

    print()

    print(
        "=" * 60
    )

    print(
        "ANÁLISE CONCLUÍDA"
    )

    print(
        "=" * 60
    )

    print()


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    main()
