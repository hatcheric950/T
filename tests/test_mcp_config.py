import json

from hermes.mcp.config import load_mcp_config, resolve_inputs


def _write_cfg(tmp_path):
    p = tmp_path / "mcp.json"
    p.write_text(json.dumps({
        "inputs": [{"id": "api_token", "description": "token"}],
        "servers": {
            "hostinger": {
                "type": "stdio",
                "command": "npx",
                "args": ["hostinger-api-mcp@latest"],
                "env": {"API_TOKEN": "${input:api_token}"},
            }
        },
    }))
    return p


def test_load_and_parse(tmp_path):
    p = _write_cfg(tmp_path)
    cfg = load_mcp_config([p])
    assert "hostinger" in cfg.servers
    srv = cfg.servers["hostinger"]
    assert srv.command == "npx"
    assert srv.args == ["hostinger-api-mcp@latest"]
    assert cfg.inputs[0].id == "api_token"


def test_resolve_inputs_from_env(tmp_path, monkeypatch):
    cfg = load_mcp_config([_write_cfg(tmp_path)])
    monkeypatch.setenv("HERMES_INPUT_API_TOKEN", "secret123")
    resolved = resolve_inputs(cfg.servers["hostinger"], cfg.inputs, interactive=False)
    assert resolved.env["API_TOKEN"] == "secret123"


def test_missing_config_returns_empty():
    cfg = load_mcp_config([])
    assert cfg.servers == {}
