import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def testeaza_conexiunea():
    server_params = StdioServerParameters(command="npx",args=["-y","@lydt/geogebra-mcp-server"])

    print("incerc sa ma conectez la geogebra mcp\n")
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print("conectat la mcp\n")

                unelte = await session.list_tools()
                print("unelte disponibile pentru claude:")
                for tool in unelte.tools:
                    print(f" -{tool.name}: {tool.description}")

    except Exception as e:
        print(f"a aparut o eroare: {e}")

if __name__ == "__main__":
    asyncio.run(testeaza_conexiunea())
