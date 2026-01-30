"""FastAPI application entry point.

This is the main module that creates and configures the FastAPI application.
Run with: uvicorn lumehaven.main:app --reload
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lumehaven import __version__
from lumehaven.adapters import AdapterManager, create_adapter
from lumehaven.api.routes import router as api_router
from lumehaven.api.sse import router as sse_router
from lumehaven.config import get_settings, load_adapter_configs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Application Lifespan
# -----------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan manager.

    Handles startup and shutdown tasks:
    - Startup: Create adapters, load signals, start sync tasks
    - Shutdown: Cancel tasks, close connections
    """
    # Load adapter configurations
    adapter_configs = load_adapter_configs()
    logger.info(f"Loaded {len(adapter_configs)} adapter configuration(s)")

    # Create adapter manager
    manager = AdapterManager()
    for config in adapter_configs:
        adapter = create_adapter(config)
        manager.add(adapter)

    # Store manager for access in routes
    app.state.adapter_manager = manager

    try:
        # Start all adapters (failures are handled gracefully)
        await manager.start_all()

        if not manager.connected_adapters:
            logger.warning("No adapters connected - starting in degraded mode")
        else:
            logger.info(
                f"Started with {len(manager.connected_adapters)}/"
                f"{len(manager.adapters)} adapter(s) connected"
            )

        yield

    finally:
        logger.info("Shutting down...")
        await manager.stop_all()
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
