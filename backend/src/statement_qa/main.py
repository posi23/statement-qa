"""FastAPI application entry point."""

from fastapi import FastAPI

from statement_qa.api import health


def create_app() -> FastAPI:
    """Build a new FastAPI app with every router attached.

    A factory rather than a shared global so each test gets a fresh app.
    """
    app = FastAPI(title="statement-qa")
    app.include_router(health.router)
    return app


# Module-level instance for `uvicorn statement_qa.main:app`.
app = create_app()
