"""
Claude GitHub Chat
Type natural language questions about your GitHub repo.
Claude will call the MCP server tools to get real data and answer.

Examples:
  "Show me recent commits"
  "Any open pull requests?"
  "Search for authentication code"
  "List open issues"
  "Show me the contents of README.md"
"""

import anthropic
import httpx
import json

MCP_SERVER_URL = "http://localhost:8000"
CLAUDE_MODEL = "claude-sonnet-4-6"

# ── Fetch tools from MCP server ──────────────────────────────────────────────

def get_tools():
    r        = httpx.get(f"{MCP_SERVER_URL}/tools", timeout=5)
    registry = r.json()["tools"]
    result   = []
    for name, info in registry.items():
        props, required = {}, []
        for pname, pdesc in info["parameters"].items():
            is_opt  = "optional" in pdesc.lower()
            ptype   = "integer" if "int" in pdesc.lower() else "string"
            props[pname] = {"type": ptype, "description": pdesc}
            if not is_opt:
                required.append(pname)
        result.append({
            "name":         name,
            "description":  info["description"],
            "input_schema": {"type": "object", "properties": props, "required": required}
        })
    return result

# ── Execute tool on MCP server ───────────────────────────────────────────────

def run_tool(name, params):
    r = httpx.post(f"{MCP_SERVER_URL}/tools/call", json={"tool": name, "parameters": params}, timeout=15)
    d = r.json()
    return json.dumps(d["result"], indent=2) if d["success"] else f"Error: {d['error']}"

# ── Chat loop with Claude ────────────────────────────────────────────────────

def chat(query):
    client   = anthropic.Anthropic()
    tools    = get_tools()
    messages = [{"role": "user", "content": query}]
    system   = (
        "You are a GitHub assistant. You help developers understand their codebase. "
        "When asked about code, commits, PRs, or issues - always use tools to fetch real data. "
        "Be concise and developer-friendly in your responses."
    )

    while True:
        resp = client.messages.create(
            model=CLAUDE_MODEL, max_tokens=2048,
            system=system, tools=tools, messages=messages
        )

        if resp.stop_reason == "end_turn":
            return "".join(b.text for b in resp.content if hasattr(b, "text"))

        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    print(f"  [{block.name}] searching...")
                    out = run_tool(block.name, block.input)
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": out})
            messages.append({"role": "user", "content": results})

# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Check server is running
    try:
        h = httpx.get(f"{MCP_SERVER_URL}/health", timeout=3).json()
        print(f"\nConnected to repo: {h['repo']}")
        print(f"Tools available:   {', '.join(h['tools'])}")
    except Exception:
        print("ERROR: MCP server not running. Start it first: python server.py")
        exit(1)

    print("\nAsk anything about your GitHub repo. Type 'quit' to exit.")
    print("Examples:")
    print("  - Show me the last 5 commits")
    print("  - Any open pull requests?")
    print("  - Search for login code")
    print("  - List open issues\n")

    while True:
        q = input("You: ").strip()
        if q.lower() in ("quit", "exit", "q"):
            break
        if q:
            print()
            answer = chat(q)
            print(f"Claude: {answer}\n")
            print("-" * 50)