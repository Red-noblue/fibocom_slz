"""环境测量硬件的 Web 服务入口，负责实时显示、偏好配置、资源状态与文档预览。"""

from __future__ import annotations

import subprocess
import time
import os
import json
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from environmental_sensing_hardware.registry.device_registry import DeviceRegistry
from environmental_sensing_hardware.runtime.monitor_service import MonitorService
from environmental_sensing_hardware.storage.history_store import HistoryStore
from environmental_sensing_hardware.web.docs_preview import DocumentPreviewService

MODULE_ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = MODULE_ROOT / "src" / "environmental_sensing_hardware" / "web" / "static"
DOCS_ROOT = MODULE_ROOT / "docs" / "设备"
CACHE_ROOT = MODULE_ROOT / ".cache" / "doc_previews"
HISTORY_DB_PATH = MODULE_ROOT / ".cache" / "history" / "readings.sqlite3"
CONFIG_PATH = MODULE_ROOT / "configs" / "devices" / "local_devices.json"
PREFERENCES_PATH = MODULE_ROOT / ".cache" / "preferences" / "ui_preferences.json"

DEFAULT_PREFERENCES = {
    "polling_interval_seconds": 3,
    "history_range_key": "30m",
    "chart_columns": 3,
}

app = FastAPI(title="环境测量硬件可视化")
registry = DeviceRegistry(CONFIG_PATH)
doc_service = DocumentPreviewService(DOCS_ROOT, CACHE_ROOT)
history_store = HistoryStore(HISTORY_DB_PATH)
monitor_service = MonitorService(registry, history_store, interval_options=[1, 3, 5, 10, 30], default_interval_seconds=3)


class PollingConfigRequest(BaseModel):
    """轮询周期更新请求体。"""

    interval_seconds: int


class PreferencesRequest(BaseModel):
    """用户界面偏好配置请求体。"""

    polling_interval_seconds: Optional[int] = None
    history_range_key: Optional[str] = None
    chart_columns: Optional[int] = None


@app.on_event("startup")
def on_startup() -> None:
    """应用启动时拉起后台采样线程。"""

    preferences = _load_preferences()
    monitor_service.set_interval_seconds(preferences["polling_interval_seconds"])
    monitor_service.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    """应用停止时关闭后台采样线程。"""

    monitor_service.stop()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """返回单页应用页面。"""

    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/readings")
def get_readings() -> dict:
    """返回当前全部设备读数。"""

    return monitor_service.get_readings_snapshot()


@app.get("/api/system")
def get_system_status() -> dict:
    """返回本模块相关的轻量系统压力指标。"""

    return {
        "module": _du_bytes(MODULE_ROOT),
        "cache": _du_bytes(MODULE_ROOT / ".cache"),
        "history_db": _file_stat(HISTORY_DB_PATH),
        "process": _current_process_status(),
    }


@app.post("/api/system/cleanup")
def cleanup_system_cache() -> dict:
    """立即清理历史数据库，防止长时间运行后占用持续增长。"""

    cleanup_result = history_store.enforce_limits()
    return {"history": cleanup_result, "history_db": _file_stat(HISTORY_DB_PATH)}


@app.get("/api/history")
def get_history(
    range_key: str = Query("30m", description="历史范围键，例如 5m、30m、6h、24h、3d"),
) -> dict:
    """返回指定时间范围的历史曲线数据。"""

    try:
        return monitor_service.get_history_snapshot(range_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/preferences")
def get_preferences() -> dict:
    """返回用户界面偏好配置。"""

    return _load_preferences()


@app.put("/api/preferences")
def update_preferences(payload: PreferencesRequest) -> dict:
    """保存用户界面偏好配置，配置保存在服务端以适应设备 IP 变化。"""

    preferences = _load_preferences()
    incoming = payload.dict(exclude_none=True)
    if "polling_interval_seconds" in incoming:
        interval = incoming["polling_interval_seconds"]
        if interval not in monitor_service.interval_options:
            raise HTTPException(status_code=400, detail=f"不支持的轮询周期: {interval}")
        preferences["polling_interval_seconds"] = interval
        monitor_service.set_interval_seconds(interval)
    if "history_range_key" in incoming:
        range_key = incoming["history_range_key"]
        if range_key not in {"5m", "30m", "6h", "24h", "3d"}:
            raise HTTPException(status_code=400, detail=f"不支持的历史范围: {range_key}")
        preferences["history_range_key"] = range_key
    if "chart_columns" in incoming:
        columns = incoming["chart_columns"]
        if columns not in {1, 2, 3}:
            raise HTTPException(status_code=400, detail=f"不支持的曲线列数: {columns}")
        preferences["chart_columns"] = columns
    _save_preferences(preferences)
    return preferences


@app.delete("/api/preferences")
def reset_preferences() -> dict:
    """重置用户界面偏好配置。"""

    if PREFERENCES_PATH.exists():
        PREFERENCES_PATH.unlink()
    monitor_service.set_interval_seconds(DEFAULT_PREFERENCES["polling_interval_seconds"])
    return dict(DEFAULT_PREFERENCES)


@app.post("/api/settings/polling")
def update_polling_settings(payload: PollingConfigRequest) -> dict:
    """更新后台采样轮询周期。"""

    try:
        interval_seconds = monitor_service.set_interval_seconds(payload.interval_seconds)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    preferences = _load_preferences()
    preferences["polling_interval_seconds"] = interval_seconds
    _save_preferences(preferences)
    return {
        "interval_seconds": interval_seconds,
        "interval_options": monitor_service.interval_options,
    }


@app.get("/api/docs")
def get_documents() -> dict:
    """返回文档清单及对应预览地址。"""

    return {"items": doc_service.list_documents()}


@app.get("/api/docs/source")
def get_document_source(path: str = Query(..., description="文档相对路径")) -> FileResponse:
    """返回原始文档文件。"""

    try:
        source_path = doc_service.get_source_path(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(source_path)


@app.get("/api/docs/pdf")
def get_document_pdf(path: str = Query(..., description="文档相对路径")) -> FileResponse:
    """返回文档的 PDF 预览版本。"""

    try:
        pdf_path = doc_service.ensure_pdf(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except subprocess.CalledProcessError as exc:  # type: ignore[name-defined]
        raise HTTPException(status_code=500, detail=exc.stderr or "文档转换失败") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(pdf_path, media_type="application/pdf")


@app.get("/api/docs/text")
def get_document_text(path: str = Query(..., description="文档相对路径")) -> PlainTextResponse:
    """返回文档的文本提取内容。"""

    try:
        text_path = doc_service.ensure_text(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except subprocess.CalledProcessError as exc:  # type: ignore[name-defined]
        raise HTTPException(status_code=500, detail=exc.stderr or "文档转换失败") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PlainTextResponse(text_path.read_text(encoding="utf-8", errors="ignore"))


def _file_stat(path: Path) -> dict:
    """返回文件大小和修改时间；文件不存在时返回空状态。"""

    if not path.exists():
        return {"exists": False, "bytes": 0, "modified_at": None}
    stat = path.stat()
    return {"exists": True, "bytes": stat.st_size, "modified_at": stat.st_mtime}


def _du_bytes(path: Path) -> dict:
    """递归计算目录大小，避免依赖外部 du 命令。"""

    if not path.exists():
        return {"exists": False, "bytes": 0}
    if path.is_file():
        return {"exists": True, "bytes": path.stat().st_size}
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return {"exists": True, "bytes": total}


def _current_process_status() -> dict:
    """读取当前服务进程的 CPU 时间、RSS 和运行时长。"""

    stat_path = Path("/proc/self/stat")
    status_path = Path("/proc/self/status")
    boot_ticks = time.time()
    clock_ticks = 100
    try:
        clock_ticks = int(subprocess.check_output(["getconf", "CLK_TCK"], text=True).strip())
    except Exception:  # noqa: BLE001
        pass

    started_seconds = None
    cpu_seconds = None
    if stat_path.exists():
        parts = stat_path.read_text(encoding="utf-8").split()
        utime = int(parts[13])
        stime = int(parts[14])
        starttime = int(parts[21])
        uptime = float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0])
        cpu_seconds = (utime + stime) / clock_ticks
        started_seconds = boot_ticks - (uptime - starttime / clock_ticks)

    rss_kb = 0
    if status_path.exists():
        for line in status_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                rss_kb = int(line.split()[1])
                break
    return {
        "pid": os.getpid(),
        "rss_bytes": rss_kb * 1024,
        "cpu_seconds": cpu_seconds,
        "started_at": started_seconds,
    }


def _load_preferences() -> dict[str, Any]:
    """从服务端缓存加载用户偏好配置，避免设备 IP 变化导致配置丢失。"""

    try:
        payload = json.loads(PREFERENCES_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        payload = {}
    preferences = dict(DEFAULT_PREFERENCES)
    preferences.update({key: payload[key] for key in preferences if key in payload})
    if preferences["polling_interval_seconds"] not in monitor_service.interval_options:
        preferences["polling_interval_seconds"] = DEFAULT_PREFERENCES["polling_interval_seconds"]
    if preferences["history_range_key"] not in {"5m", "30m", "6h", "24h", "3d"}:
        preferences["history_range_key"] = DEFAULT_PREFERENCES["history_range_key"]
    if preferences["chart_columns"] not in {1, 2, 3}:
        preferences["chart_columns"] = DEFAULT_PREFERENCES["chart_columns"]
    return preferences


def _save_preferences(preferences: dict[str, Any]) -> None:
    """保存用户偏好配置到服务端缓存目录。"""

    PREFERENCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREFERENCES_PATH.write_text(
        json.dumps(preferences, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
