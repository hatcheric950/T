import pytest

from hermes.providers import normalize_model_id


def test_normalize_model_id_strips_prefix_for_non_anthropic():
    assert normalize_model_id("openrouter", "openrouter/anthropic/claude") == "anthropic/claude"
    assert normalize_model_id("nous", "nous/hermes-4") == "hermes-4"


def test_normalize_model_id_keeps_anthropic_untouched():
    assert normalize_model_id("anthropic", "anthropic/claude-sonnet-4-6") == "anthropic/claude-sonnet-4-6"


def test_make_provider_base_urls(monkeypatch):
    from hermes.providers import make_provider

    monkeypatch.setenv("OPENROUTER_API_KEY", "k1")
    monkeypatch.setenv("NOUS_API_KEY", "k2")
    oro = make_provider("openrouter")
    nous = make_provider("nous")
    assert oro.base_url == "https://openrouter.ai/api/v1"
    assert nous.base_url == "https://inference-api.nousresearch.com/v1"

    with pytest.raises(ValueError):
        make_provider("bogus")
