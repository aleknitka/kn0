"""FastAPI web application for kn0."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from kn0.config import settings

_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def create_app() -> FastAPI:
    app = FastAPI(title="kn0", docs_url=None, redoc_url=None)

    # ------------------------------------------------------------------
    # Upload page
    # ------------------------------------------------------------------

    @app.get("/", response_class=HTMLResponse)
    async def upload_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse("upload.html", {"request": request})

    # ------------------------------------------------------------------
    # Ingest endpoint — accepts one file per request, called by JS
    # ------------------------------------------------------------------

    @app.post("/ingest")
    async def ingest_file(
        file: UploadFile = File(...),
        backend: str = Form(default="spacy"),
        source_reliability: float = Form(default=0.5),
    ) -> JSONResponse:
        if backend not in ("spacy", "llm"):
            return JSONResponse({"error": f"Unknown backend: {backend}"}, status_code=400)

        # Save upload to a temp file so the pipeline can read it
        suffix = Path(file.filename or "upload").suffix or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)

        try:
            from kn0.extraction.base import ExtractionBackend
            from kn0.persistence.database import get_connection
            from kn0.pipeline import ingest_document

            extraction_backend: ExtractionBackend | None = None
            if backend == "llm":
                from kn0.llm import get_llm_backend
                extraction_backend = get_llm_backend()

            # Use original filename for the pipeline so it appears correctly in the DB
            named_path = tmp_path.parent / (file.filename or tmp_path.name)
            tmp_path.rename(named_path)
            tmp_path = named_path

            with get_connection() as conn:
                result = ingest_document(
                    tmp_path,
                    conn,
                    backend=extraction_backend,
                    source_reliability=source_reliability,
                )
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)
        finally:
            tmp_path.unlink(missing_ok=True)

        return JSONResponse({
            "document_id": result.document_id,
            "filename": result.filename,
            "was_duplicate": result.was_duplicate,
            "pages_processed": result.pages_processed,
            "entities_created": result.entities_created,
            "entities_merged": result.entities_merged,
            "relationships_created": result.relationships_created,
            "relationships_updated": result.relationships_updated,
            "error": result.error,
        })

    return app


app = create_app()
