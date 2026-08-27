import asyncio
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():

    if not os.environ.get("GRAFANA_TOKEN"):
        print("ERRO: GRAFANA_TOKEN não está configurado.")
        return

    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        env={
            **os.environ,
            "GRAFANA_TOKEN": os.environ["GRAFANA_TOKEN"],
            "GRAFANA_URL": os.environ.get(
                "GRAFANA_URL",
                "http://localhost:3000"
            ),
        },
    )

    print("======================================")
    print(" TESTE DO MCP GRAFANA")
    print("======================================")
    print()

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            print("MCP conectado.")
            print()

            tools = await session.list_tools()

            print("Ferramentas disponíveis:")
            print()

            for tool in tools.tools:
                print(f"- {tool.name}")
                print(f"  {tool.description}")
                print()

            print("Executando get_panel_data...")
            print()

            result = await session.call_tool(
                "get_panel_data",
                {
                    "dashboard_uid": "ad7xgr9",
                    "panel_id": 1,
                },
            )

            print("RESULTADO:")
            print()

            for content in result.content:
                if hasattr(content, "text"):
                    print(content.text)

            print()
            print("======================================")
            print(" TESTE CONCLUÍDO")
            print("======================================")


if __name__ == "__main__":
    asyncio.run(main())
