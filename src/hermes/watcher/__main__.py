from __future__ import annotations

import asyncio
import logging
import signal
import sys

import uvicorn

from .classifier import Classifier
from .gmail import GmailListener
from .pipeline import Pipeline
from .policy import Policy
from .settings import load_settings
from .state import State
from .twilio_webhook import build_app


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )


async def _main() -> int:
    _setup_logging()
    log = logging.getLogger("hermes.watcher")

    settings = load_settings()
    log.info("starting hermes watcher mode=%s host=%s", settings.mode, settings.hostname)

    state = State(settings.state_db)
    await state.open()
    policy = Policy(settings, state)
    classifier = Classifier(settings, state)
    pipeline = Pipeline(settings, state, policy, classifier)

    app = build_app(settings, pipeline)
    config = uvicorn.Config(
        app, host=settings.http_host, port=settings.http_port,
        log_level="info", access_log=False,
    )
    server = uvicorn.Server(config)

    tasks: list[asyncio.Task] = [asyncio.create_task(server.serve(), name="http")]
    if settings.gmail_address and settings.gmail_app_password:
        listener = GmailListener(settings, pipeline)
        tasks.append(asyncio.create_task(listener.run(), name="imap"))
    else:
        log.warning("gmail credentials missing; IMAP listener disabled")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    done_task = asyncio.create_task(stop.wait())
    await asyncio.wait([done_task, *tasks], return_when=asyncio.FIRST_COMPLETED)

    server.should_exit = True
    for t in tasks:
        t.cancel()
    for t in tasks:
        try:
            await t
        except (asyncio.CancelledError, Exception):
            pass
    await state.close()
    return 0


def main() -> int:
    return asyncio.run(_main())


if __name__ == "__main__":
    sys.exit(main())
