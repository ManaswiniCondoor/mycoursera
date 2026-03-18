import os, json
from types import SimpleNamespace

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
TAVILY_KEY    = os.environ.get("TAVILY_API_KEY")

# ── Web search (real Tavily or simulated) ────────────────────────────────────
if TAVILY_KEY:
    from tavily import TavilyClient
    _tv = TavilyClient(api_key=TAVILY_KEY)
    def web_search(query): return "\n".join(r["content"] for r in _tv.search(query)["results"][:3])
else:
    def web_search(_):
        return ("NVDA -4.1% today, RSI oversold at 28 — analysts see strong buy. "
                "META -3.2% on ad miss but long-term fundamentals intact. "
                "AMZN -2.8% on macro; AWS +17% YoY growth. "
                "MSFT -2.1%; Azure outperforming. Analysts recommend DCA on NVDA/AMZN.")

tools = [{"name": "web_search",
          "description": "Search the web for current stock market data",
          "input_schema": {"type": "object",
                           "properties": {"query": {"type": "string"}},
                           "required": ["query"]}}]

# ── Anthropic client (real or simulated) ─────────────────────────────────────
def make_call(messages):
    if ANTHROPIC_KEY:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        return client.messages.create(model="claude-opus-4-6", max_tokens=1024,
                                      tools=tools, messages=messages)
    # Simulated two-turn agent: turn 1 = tool call, turn 2 = final answer
    if len(messages) == 1:
        block = SimpleNamespace(type="tool_use", id="tool_1",
                                name="web_search",
                                input={"query": "stock market dips to buy today 2026"})
        return SimpleNamespace(stop_reason="tool_use", content=[block])
    data = messages[-1]["content"][0]["content"]
    text = (f"Based on today's market data:\n\n"
            f"📉 **Top dip-buy candidates:**\n"
            f"• **NVDA** — down 4.1%, RSI=28 (oversold). Strong AI/data-center catalyst.\n"
            f"• **AMZN** — down 2.8%, AWS growth intact at 17% YoY. Macro dip, not fundamental.\n"
            f"• **META** — down 3.2%, ad-revenue miss is short-term; long-term ad moat solid.\n\n"
            f"⚠️  Not financial advice — always do your own due diligence.")
    block = SimpleNamespace(type="text", text=text)
    return SimpleNamespace(stop_reason="end_turn", content=[block])

# ── Agentic loop ─────────────────────────────────────────────────────────────
def run_agent(question):
    print(f"\n❓ User: {question}\n")
    messages = [{"role": "user", "content": question}]
    while True:
        resp = make_call(messages)
        if resp.stop_reason == "end_turn":
            for b in resp.content:
                if hasattr(b, "text"):
                    print(f"✅ Final Answer:\n{b.text}\n")
            break
        for b in resp.content:
            if b.type == "tool_use":
                print(f"🔧 Tool call : {b.name}(query='{b.input['query']}')")
                data = web_search(b.input["query"])
                print(f"📦 Result    : {data[:300]}...\n")
                messages.append({"role": "assistant", "content": [b]})
                messages.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": b.id, "content": data}]})

run_agent("What stock dips should I buy today?")
