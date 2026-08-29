from mcp.server.mcpserver import MCPServer
from pathlib import Path

mcp = MCPServer("safe-tools")
ROOT = Path("/home/mudsg/agent").resolve()

def _safe(name: str) -> Path:
    p = (ROOT / name).resolve()
    if not p.is_relative_to(ROOT):
        raise ValueError("outside the allowed directory")
    return p

@mcp.tool()
def list_files(pattern: str = "*") -> str:
    """List files in the agent directory matching a glob pattern"""
    return "\n".join(sorted(p.name for p in ROOT.glob(pattern))) or "(none)"

@mcp.tool()
def read_file(name: str) -> str:
    """Read a text file from the agent directory"""
    p = _safe(name)
    if not p.is_file():
        return f"no such file: {name}"
    return p.read_text()[:5000]

@mcp.tool()
def count_lines(name: str) -> str:
    """Count the lines in a text file in the agent directory"""
    p = _safe(name)
    if not p.is_file():
        return f"no such file: {name}"
    return str(len(p.read_text().splitlines()))

if __name__ == "__main__":
    mcp.run(transport="stdio")
