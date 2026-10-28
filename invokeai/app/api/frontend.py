from pathlib import Path

from starlette.applications import Starlette

from invokeai.app.api.no_cache_staticfiles import NoCacheStaticFiles


def mount_frontend(app: Starlette, frontend_root: Path, *, legacy: bool = False) -> None:
    """Mount the built SPA.

    API-only build: the legacy webv1 UI was removed, so both modes serve the webv2 bundle.
    Raises RuntimeError when no bundle is present (dev checkouts build it separately).
    """
    app.mount("/", NoCacheStaticFiles(directory=frontend_root / "dist", html=True), name="ui")
