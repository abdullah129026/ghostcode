"""Stretch: rough Groq cost to run an LLM pass over the dead code.

The heuristic cost model ships; this answers the follow-up question a
manager asks: "what would it cost to have an LLM double-check these
deletes?" Tokens are estimated at chars/4, prices are per-1M input
tokens and go stale fast. Verify current Groq pricing before quoting
anyone a number.
"""

# $ per 1M input tokens. Last checked Oct 2026; treat as stale on sight.
GROQ_PRICES = {
    "llama-3.3-70b-versatile": 0.59,
}

CHARS_PER_TOKEN = 4


def estimate_llm_cost(ghost_loc, chars_per_line=40,
                      model="llama-3.3-70b-versatile"):
    """Planning estimate for one LLM review pass over the ghost code."""
    tokens = ghost_loc * chars_per_line // CHARS_PER_TOKEN
    cost = tokens / 1_000_000 * GROQ_PRICES[model]
    return {
        "model": model,
        "est_input_tokens": tokens,
        "est_cost_usd": round(cost, 4),
        "note": "rough planning estimate; verify current Groq pricing",
    }
