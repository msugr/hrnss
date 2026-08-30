import asyncio, anthropic
from mcp import ClientSession, StdioServerParameters, stdio_client

client = anthropic.Anthropic()

# Tools the model must not run without an explicit yes from a human.
# This is the actual harness-engineering decision: which actions are
# allowed to happen automatically, and which require a human in the loop.
SENSITIVE_TOOLS = {"write_file"}

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

                        # --- permission gate ---
                        # Sensitive tools stop here and wait for a human
                        # decision before the harness lets them run.
                        if b.name in SENSITIVE_TOOLS:
                            answer = input(
                                f"  -> allow {b.name}({b.input})? (y/n): "
                            ).strip().lower()
                            if answer != "y":
                                results.append({
                                    "type": "tool_result",
                                    "tool_use_id": b.id,
                                    "content": "Denied by the human operator.",
                                    "is_error": True,
                                })
                                continue

                        # --- error recovery ---
                        # A failing tool call becomes a message the model can
                        # see and react to, instead of crashing the process.
                        try:
                            out = await session.call_tool(b.name, b.input)
                            content = out.content[0].text
                            is_error = bool(getattr(out, "isError", False))
                        except Exception as e:
                            content = f"Tool call failed: {e!r}"
                            is_error = True

                        result = {"type": "tool_result",
                                  "tool_use_id": b.id,
                                  "content": content}
                        if is_error:
                            result["is_error"] = True
                        results.append(result)
                messages.append({"role": "user", "content": results})

asyncio.run(main())
