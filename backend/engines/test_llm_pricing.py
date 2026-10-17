"""LLM pricing stretch: the estimate math, nothing more."""

from engines.llm_pricing import estimate_llm_cost


def test_estimate_scales_with_loc():
    small = estimate_llm_cost(1000)
    big = estimate_llm_cost(10000)
    assert small["est_input_tokens"] == 10000  # 1000 lines x 40 chars / 4
    assert big["est_cost_usd"] == round(small["est_cost_usd"] * 10, 4)
    assert "verify" in small["note"]


def test_zero_loc_costs_zero():
    assert estimate_llm_cost(0)["est_cost_usd"] == 0.0
