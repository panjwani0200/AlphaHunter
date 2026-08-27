from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.trading_service import trading_service

router = APIRouter(prefix="/exports")


@router.get("")
def list_exports() -> list[dict[str, object]]:
    exporter = trading_service.exporter
    if exporter is None:
        return []
    exports: list[dict[str, object]] = []
    for path in exporter.list_exports():
        exports.append(
            {
                "filename": path.name,
                "size_bytes": path.stat().st_size,
                "modified_at": Path(path).stat().st_mtime,
            }
        )
    return exports


@router.get("/latest")
def download_latest_export() -> FileResponse:
    export_path = trading_service.latest_analysis_export()
    if export_path is None or not export_path.exists():
        raise HTTPException(status_code=404, detail="No analysis CSV has been generated yet.")
    return FileResponse(
        path=export_path,
        filename=export_path.name,
        media_type="text/csv",
    )

