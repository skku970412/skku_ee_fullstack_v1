# Re-export FastAPI app for uvicorn entrypoints
from .main import create_app

app = create_app()

__all__ = ["app", "create_app"]
