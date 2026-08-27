from http.server import BaseHTTPRequestHandler, HTTPServer
import random

value = 50.0
request_count = 0


def generate_value():
    global value
    global request_count

    request_count += 1

    # Reinicia o ciclo a cada 40 coletas
    cycle = request_count % 40

    # 1. Comportamento normal
    if cycle <= 12:
        value += random.uniform(-1.5, 1.5)
        value = max(40, min(value, 60))

    # 2. Subida gradual
    elif cycle <= 20:
        value += random.uniform(3, 5)
        value = min(value, 90)

    # 3. ANOMALIA
    elif cycle <= 28:
        value += random.uniform(-1, 1)
        value = max(90, min(value, 98))

    # 4. Recuperação
    else:
        value -= random.uniform(4, 6)
        value = max(value, 45)

    return round(value, 2)


class MetricsHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        if self.path == "/metrics":

            current_value = generate_value()

            response = f"""# HELP system_utilization_percent Simulated system utilization
# TYPE system_utilization_percent gauge
system_utilization_percent {current_value}
"""

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/plain; version=0.0.4"
            )
            self.end_headers()

            self.wfile.write(response.encode())

        else:
            self.send_response(404)
            self.end_headers()


server = HTTPServer(("0.0.0.0", 8000), MetricsHandler)

print("Exporter iniciado na porta 8000")

server.serve_forever()
