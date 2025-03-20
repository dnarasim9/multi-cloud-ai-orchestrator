"""Application entrypoint."""

from __future__ import annotations

import uvicorn

from orchestrator.api.app import create_app
from orchestrator.config import get_settings
from orchestrator.infrastructure.observability.logging import setup_logging


app = create_app()


def main() -> None:
    """Run the application."""
    settings = get_settings()
    setup_logging(settings.observability.log_level)

    uvicorn.run(
        "orchestrator.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.debug,
        log_level=settings.observability.log_level.lower(),
    )


if __name__ == "__main__":
    main()
