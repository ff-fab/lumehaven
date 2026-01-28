"""FastAPI application entry point.

This is the main module that creates and configures the FastAPI application.
Run with: uvicorn lumehaven.main:app --reload
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lumehaven import __version__
from lumehaven.adapters.openhab import OpenHABAdapter
from lumehaven.adapters.protocol import SmartHomeAdapter
from lumehaven.api.routes import router as api_router
from lumehaven.api.sse import router as sse_router
from lumehaven.config import SmartHomeType, get_settings
from lumehaven.state.store import get_signal_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def sync_from_smart_home(adapter: SmartHomeAdapter) -> None:
    """Background task to sync signals from smart home system.

    Subscribes to the adapter's event stream and publishes updates
    to the signal store.
    """
    store = get_signal_store()

    try:
        async for signal in adapter.subscribe_events():
            await store.publish(signal)
    except Exception:
        logger.exception(f"Error in smart home sync task for adapter '{adapter.name}'")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan manager.

    Handles startup and shutdown tasks:
    - Startup: Load initial signals, start event sync
    - Shutdown: Cancel background tasks, close connections
    """
    settings = get_settings()
    store = get_signal_store()

    # Create adapter based on configuration
    if settings.smart_home_type == SmartHomeType.OPENHAB:
        adapter: SmartHomeAdapter = OpenHABAdapter(
            base_url=settings.openhab_url,
            tag=settings.openhab_tag,
            name="openhab",
        )
    else:
        raise NotImplementedError(
            f"Smart home type not supported: {settings.smart_home_type}"
        )

    # Store adapter for access in routes if needed
    app.state.adapter = adapter

    sync_task: asyncio.Task[None] | None = None
    try:
        # Load initial signals
        logger.info(f"Connecting to {settings.smart_home_type.value}...")
        signals = await adapter.get_signals()
        await store.set_many(signals)
        logger.info(f"Loaded {len(signals)} signals")

        # Start background sync task
        sync_task = asyncio.create_task(sync_from_smart_home(adapter))
        logger.info("Started smart home event sync")

        yield

    finally:
        # Cleanup
        logger.info("Shutting down...")
        if sync_task is not None:
            sync_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await sync_task
        await adapter.close()
        logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance.
    """
    settings = get_settings()

    app = FastAPI(
        title="lumehaven",
        description="Smart home dashboard backend",
        version=__version__,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(api_router)
    app.include_router(sse_router)

    return app


# Application instance for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "lumehaven.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
