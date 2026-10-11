import asyncio
import sys
import json
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT = Path(__file__).resolve().parent
async def main():
    print("ASO_DIAGNOSTICS=START", flush=True)
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "server.py")],
        cwd=str(ROOT)
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=10)
            print("MCP_INITIALIZE=PASS", flush=True)
            tests = [
                ("health", {}),
                ("git_status", {}),
                ("git_recent_commits", {"count": 3}),
                ("list_files", {
                    "root_name": "andreslav",
                    "relative_path": ".",
                    "limit": 15
                })
            ]
            for name, args in tests:
                print(f"TEST={name}", flush=True)
                try:
                    result = await asyncio.wait_for(
                        session.call_tool(name, args),
                        timeout=10
                    )
                    if result.isError:
                        print(f"{name}=FAIL", flush=True)
                    else:
                        print(f"{name}=PASS", flush=True)
                    for item in result.content:
                        if hasattr(item, "text"):
                            print(item.text[:1000], flush=True)
                except TimeoutError:
                    print(f"{name}=TIMEOUT", flush=True)
                    break
    print("ASO_DIAGNOSTICS=COMPLETE", flush=True)
asyncio.run(main())
