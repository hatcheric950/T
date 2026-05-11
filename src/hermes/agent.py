from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .providers import make_provider, normalize_model_id
from .session import Session
from .skills import load_skills


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

    def send(self, user_input: str) -> str:
        provider_name = self.config.resolve_provider()
        provider = make_provider(provider_name)
        self.session.add("user", user_input)
        messages = [{"role": m.role, "content": m.content} for m in self.session.messages]
        model_id = normalize_model_id(provider_name, self.config.model)
        reply = provider.complete(model_id, messages, self._system())
        self.session.add("assistant", reply)
        self.session.save()
        return reply
