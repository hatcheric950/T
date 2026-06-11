from __future__ import annotations

from dataclasses import dataclass

from .config import Config, BUILTIN_TOOLSETS
from .mcp import ToolRegistry, load_mcp_config
from .providers import AnthropicProvider, make_provider, normalize_model_id
from .session import Session
from .skills import load_skills

MAX_TOOL_ITERATIONS = 10


@dataclass
class Agent:
    config: Config
    session: Session

    @classmethod
    def start(cls, config: Config, session: Session | None = None) -> "Agent":
        if session is None:
            session = Session.new(model=config.model, provider=config.resolve_provider())
        return cls(config=config, session=session)

    def _system(self) -> str:
        parts = [self.config.system_prompt]
        if self.config.toolsets:
            parts.append(f"Available toolsets: {', '.join(self.config.toolsets)}.")
        if self.config.skills:
            parts.append(load_skills(list(self.config.skills)))
        return "\n\n".join(p for p in parts if p)

    def _registry(self) -> ToolRegistry | None:
        mcp_toolsets = [t for t in self.config.toolsets if t not in BUILTIN_TOOLSETS]
        if not mcp_toolsets:
            return None
        reg = ToolRegistry(load_mcp_config(), mcp_toolsets)
        if reg.missing and self.config.verbose:
            print(f"[hermes] unknown toolsets: {', '.join(reg.missing)}")
        if not reg.server_names():
            return None
        return reg

    def send(self, user_input: str) -> str:
        provider_name = self.config.resolve_provider()
        model_id = normalize_model_id(provider_name, self.config.model)
        self.session.add("user", user_input)

        registry = self._registry()
        if registry is None or provider_name != "anthropic":
            provider = make_provider(provider_name)
            messages = [{"role": m.role, "content": m.content}
                        for m in self.session.messages]
            reply = provider.complete(model_id, messages, self._system())
            self.session.add("assistant", reply)
            self.session.save()
            return reply

        try:
            return self._run_anthropic_tool_loop(model_id, registry)
        finally:
            registry.close()

    def _run_anthropic_tool_loop(self, model_id: str, registry: ToolRegistry) -> str:
        provider = AnthropicProvider()
        tool_specs = registry.discover()
        if self.config.verbose:
            print(f"[hermes] tools: {[t.qualified_name for t in tool_specs]}")
        anthropic_tools = [
            {"name": t.qualified_name, "description": t.description,
             "input_schema": t.input_schema or {"type": "object", "properties": {}}}
            for t in tool_specs
        ]

        messages = [_to_provider_msg(m) for m in self.session.messages]
        final_text = ""
        for _ in range(MAX_TOOL_ITERATIONS):
            resp = provider.complete_with_tools(model_id, messages, self._system(), anthropic_tools)
            assistant_content = [_block_to_dict(b) for b in resp.content]
            messages.append({"role": "assistant", "content": assistant_content})
            self.session.add("assistant", assistant_content)

            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            if resp.stop_reason != "tool_use" or not tool_uses:
                final_text = "".join(b.text for b in resp.content if b.type == "text")
                break

            tool_results = []
            for use in tool_uses:
                try:
                    output = registry.call(use.name, dict(use.input or {}))
                    tool_results.append({"type": "tool_result", "tool_use_id": use.id,
                                         "content": output})
                except Exception as e:
                    tool_results.append({"type": "tool_result", "tool_use_id": use.id,
                                         "content": f"error: {e}", "is_error": True})
            messages.append({"role": "user", "content": tool_results})
            self.session.add("user", tool_results)
        else:
            final_text = "[hermes] tool loop hit MAX_TOOL_ITERATIONS"

        self.session.save()
        return final_text


def _to_provider_msg(m) -> dict:
    return {"role": m.role, "content": m.content}


def _block_to_dict(b) -> dict:
    if b.type == "text":
        return {"type": "text", "text": b.text}
    if b.type == "tool_use":
        return {"type": "tool_use", "id": b.id, "name": b.name, "input": dict(b.input or {})}
    return {"type": b.type, **{k: v for k, v in b.model_dump().items() if k != "type"}}
