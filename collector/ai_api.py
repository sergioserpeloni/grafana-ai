import asyncio
import json

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ai_report import (
    get_grafana_panel_data,
    extract_raw_series,
    analyze_with_ollama,
)


HOST = "0.0.0.0"
PORT = 8001


class AIReportHandler(BaseHTTPRequestHandler):


    def send_json(self, data, status=200):

        response = json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ).encode("utf-8")


        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(response))
        )

        self.send_header(
            "Connection",
            "close"
        )

        self.end_headers()


        self.wfile.write(response)



    def send_html(self, html, status=200):

        response = html.encode("utf-8")


        self.send_response(status)

        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(response))
        )

        self.send_header(
            "Connection",
            "close"
        )

        self.end_headers()


        self.wfile.write(response)



    def do_GET(self):

        print()
        print(f"[API] GET {self.path}")


        # ==================================================
        # HEALTH
        # ==================================================

        if self.path == "/health":

            self.send_json(
                {
                    "status": "OK",
                    "service": "grafana-ai-api",
                    "port": PORT
                }
            )

            return



        # ==================================================
        # ROOT
        # ==================================================

        if self.path == "/":

            self.send_json(
                {
                    "status": "OK",
                    "service": "IA + MCP + Grafana",
                    "endpoints": [
                        "/api/ai-report",
                        "/api/ai-report-latest",
                        "/api/ai-report-html"
                    ]
                }
            )

            return



        # ==================================================
        # EXECUTA IA E GERA NOVO RELATORIO
        # ==================================================

        if self.path == "/api/ai-report":


            try:

                print()
                print("=" * 60)
                print("NOVA SOLICITAÇÃO DE ANÁLISE IA")
                print("=" * 60)


                print(
                    "Consultando Grafana via MCP..."
                )


                mcp_result = asyncio.run(
                    get_grafana_panel_data()
                )


                series = extract_raw_series(
                    mcp_result
                )


                print(
                    f"Pontos recebidos: {len(series)}"
                )


                if not series:

                    raise Exception(
                        "Nenhum dado recebido do Grafana"
                    )


                print(
                    "Enviando dados para Gemma..."
                )


                report = analyze_with_ollama(
                    series
                )


                response = {

                    "status": "OK",

                    "points": len(series),

                    "report": report

                }


                # salva cache

                with open(
                    "collector/latest_report.json",
                    "w",
                    encoding="utf-8"
                ) as file:

                    json.dump(
                        response,
                        file,
                        ensure_ascii=False,
                        indent=2
                    )


                self.send_json(
                    response
                )


                print(
                    "Relatório salvo com sucesso."
                )


                return



            except Exception as exc:


                print(
                    "ERRO:",
                    str(exc)
                )


                self.send_json(
                    {
                        "status": "ERROR",
                        "error": str(exc)
                    },
                    500
                )


                return





        # ==================================================
        # RETORNA ULTIMO RELATORIO (SEM IA)
        # ==================================================

        if self.path == "/api/ai-report-latest":


            try:

                with open(
                    "collector/latest_report.json",
                    "r",
                    encoding="utf-8"
                ) as file:

                    data = json.load(file)



                self.send_json(
                    data
                )


                return



            except Exception as exc:


                self.send_json(
                    {
                        "status":"ERROR",
                        "error":str(exc)
                    },
                    500
                )


                return





        # ==================================================
        # HTML PARA GRAFANA TEXT PANEL
        # ==================================================

        if self.path == "/api/ai-report-html":


            try:


                with open(
                    "collector/latest_report.json",
                    "r",
                    encoding="utf-8"
                ) as file:

                    data = json.load(file)



                report = data.get(
                    "report",
                    "Nenhum relatório disponível."
                )



                html = f"""

<!DOCTYPE html>

<html>

<head>

<meta charset="utf-8">


<style>

body {{

font-family: Arial;

background:#111;

color:#ddd;

padding:20px;

}}


h1 {{

color:#4fc3f7;

}}


.card {{

background:#1e1e1e;

padding:20px;

border-radius:10px;

}}


pre {{

white-space:pre-wrap;

font-size:14px;

}}

</style>


</head>


<body>


<h1>
🤖 IA + Grafana Observability
</h1>


<div class="card">

<pre>

{report}

</pre>


</div>


</body>


</html>

"""


                self.send_html(
                    html
                )


                return



            except Exception as exc:


                self.send_json(
                    {
                        "status":"ERROR",
                        "error":str(exc)
                    },
                    500
                )


                return





        # ==================================================
        # ERRO
        # ==================================================

        self.send_json(
            {
                "status":"ERROR",
                "error":"Endpoint não encontrado"
            },
            404
        )





    def log_message(
        self,
        format,
        *args
    ):

        print(
            f"[HTTP] {format % args}"
        )





def main():


    print()

    print("=" * 60)

    print(
        "IA + MCP + GRAFANA - API"
    )

    print("=" * 60)

    print()


    print(
        f"Servidor iniciado em http://localhost:{PORT}"
    )


    server = ThreadingHTTPServer(
        (HOST, PORT),
        AIReportHandler
    )


    try:

        server.serve_forever()


    except KeyboardInterrupt:


        print(
            "Servidor encerrado."
        )


    finally:


        server.server_close()





if __name__ == "__main__":

    main()
