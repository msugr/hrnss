import asyncio, anthropic
from mcp import ClientSession, StdioServerParameters, stdio_client

client = anthropic.Anthropic()

async def main():
    params = StdioServerParameters(command="python3", args=["server.py"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            resp = await session.list_tools()
            tools = [{"name": t.name,
                      "description": t.description,
                      "input_schema": t.input_schema} for t in resp.tools]

            messages = [{"role": "user",
                         "content": "How many .py files are in this directory?"}]

            while True:
                r = client.messages.create(
                    model="claude-sonnet-4-6", max_tokens=1024,
                    tools=tools, messages=messages)
                messages.append({"role": "assistant", "content": r.content})

                if r.stop_reason != "tool_use":
                    print(r.content[0].text)
                    break

                results = []
                for b in r.content:
                    if b.type == "tool_use":
                        print(f"[calling mcp] {b.name} {b.input}")
                        out = await session.call_tool(b.name, b.input)
                        results.append({"type": "tool_result",
                                        "tool_use_id": b.id,
                                        "content": out.content[0].text})
                messages.append({"role": "user", "content": results})

asyncio.run(main())
