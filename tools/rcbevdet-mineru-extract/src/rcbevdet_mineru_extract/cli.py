# -*- coding: utf-8 -*-
# 命令行说明：统一处理 MinerU 配额查询、文档抽取和工具包路径解析，避免再依赖旧仓库固定路径。
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import __version__
from .layout import default_output_root, default_token_file, default_legacy_token_file, toolkit_root
from .materialize import download_url, extract_zip, materialize_from_raw
from .mineru_api import MinerUAuth, MinerUClient, MinerUError
from .token_util import load_token


def _now_id() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def _slug(s: str) -> str:
    s = (s or "").strip()
    out = []
    for ch in s:
        if ch.isalnum() or ch in "._+-":
            out.append(ch)
        else:
            out.append("_")
    ss = "".join(out).strip("_")
    while "__" in ss:
        ss = ss.replace("__", "_")
    return ss or "doc"


def _safe_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _add_bool_optional_argument(
    parser: argparse.ArgumentParser,
    name: str,
    *,
    default: Optional[bool],
    help_text: str,
) -> None:
    """兼容 Python 3.8 的布尔开关，提供 --name 与 --no-name 两种形式。"""

    dest = name.lstrip("-").replace("-", "_")
    parser.add_argument(name, dest=dest, action="store_true", default=default, help=help_text)
    parser.add_argument(f"--no-{name.lstrip('-')}", dest=dest, action="store_false", help=argparse.SUPPRESS)


def _poll_task(
    client: MinerUClient,
    task_id: str,
    *,
    poll_interval_s: int,
    timeout_s: int,
) -> Dict[str, Any]:
    start_ts = time.time()
    last_state = None
    while True:
        obj = client.get_extract_task(task_id)
        data = obj.get("data") or {}
        state = data.get("state")
        if state != last_state:
            last_state = state
            print(f"[mineru] task {task_id} state={state}")
        if state in ("done", "failed"):
            return obj
        if time.time() - start_ts > timeout_s:
            raise MinerUError(f"等待任务 {task_id} 超时（>{timeout_s}s）")
        time.sleep(poll_interval_s)


def _poll_batch(
    client: MinerUClient,
    batch_id: str,
    *,
    poll_interval_s: int,
    timeout_s: int,
) -> Dict[str, Any]:
    start_ts = time.time()
    last_sig = None
    while True:
        obj = client.get_extract_results_batch(batch_id)
        data = obj.get("data") or {}
        results = data.get("extract_result") or []
        sig = [(r.get("file_name"), r.get("state")) for r in results]
        if sig != last_sig:
            last_sig = sig
            done = sum(1 for _name, state in sig if state == "done")
            failed = sum(1 for _name, state in sig if state == "failed")
            total = len(sig)
            print(f"[mineru] batch {batch_id} progress: done={done} failed={failed} total={total}")
        if results and all((item.get("state") in ("done", "failed")) for item in results):
            return obj
        if time.time() - start_ts > timeout_s:
            raise MinerUError(f"等待批量任务 {batch_id} 超时（>{timeout_s}s）")
        time.sleep(poll_interval_s)


def _download_and_materialize_zip(
    *,
    zip_url: str,
    out_dir: Path,
    keep_zip: bool,
) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / "mineru_full.zip"
    try:
        download_url(zip_url, zip_path)
    except Exception as exc:
        raise MinerUError(f"下载 full_zip_url 失败：{zip_url}: {exc}") from exc

    raw_dir = out_dir / "raw"
    images_dir = out_dir / "images"
    if raw_dir.exists():
        shutil.rmtree(raw_dir, ignore_errors=True)
    if images_dir.exists():
        shutil.rmtree(images_dir, ignore_errors=True)
    raw_root = extract_zip(zip_path, raw_dir)
    normalized = materialize_from_raw(raw_root, out_dir=out_dir)

    if not keep_zip:
        try:
            zip_path.unlink()
        except OSError:
            pass
    return {"zip_url": zip_url, "raw_root": str(raw_root), "normalized": normalized}


def cmd_paths(_args: argparse.Namespace) -> int:
    payload = {
        "toolkit_root": str(toolkit_root()),
        "default_token_file": str(default_token_file()),
        "default_legacy_token_file": str(default_legacy_token_file()),
        "default_output_root": str(default_output_root()),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_quota(args: argparse.Namespace) -> int:
    token = load_token(args.token_file, user_token=args.user_token)
    client = MinerUClient(MinerUAuth(bearer_jwt=token.bearer_jwt, user_token=token.user_token), timeout_s=args.http_timeout)
    obj = client.quota()
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    token = load_token(args.token_file, user_token=args.user_token)
    client = MinerUClient(MinerUAuth(bearer_jwt=token.bearer_jwt, user_token=token.user_token), timeout_s=args.http_timeout)

    extra_formats = list(args.extra_formats or [])
    model_version = args.model_version

    local_paths = [Path(p) for p in (args.inputs or []) if not p.startswith("http://") and not p.startswith("https://")]
    url_inputs = list(args.url or [])
    for item in (args.inputs or []):
        if item.startswith("http://") or item.startswith("https://"):
            url_inputs.append(item)

    out_root = (args.out_root or "").strip()
    out_dir_arg = (args.out_dir or "").strip() if getattr(args, "out_dir", None) else ""

    def _default_out_dir_for_local(path_obj: Path) -> Path:
        return path_obj.parent / f"{_slug(path_obj.stem)}__mineru"

    def _default_out_dir_for_url(url: str) -> Path:
        return default_output_root() / f"{_slug(Path(url).stem)}__mineru"

    def _safe_run_meta(input_obj: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "model_version": model_version,
            "extra_formats": extra_formats,
            "token": {"exp": token.payload.get("exp")},
            "input": input_obj,
            "started_at": dt.datetime.now().isoformat(),
        }

    def _extract_local_single(path_obj: Path, *, case_dir: Path) -> None:
        if not path_obj.exists() or not path_obj.is_file():
            raise MinerUError(f"输入文件不存在：{path_obj}")
        case_dir.mkdir(parents=True, exist_ok=True)
        run_meta = _safe_run_meta({"type": "local", "path": str(path_obj)})

        req_file: Dict[str, Any] = {"name": path_obj.name}
        if args.auto_data_id:
            req_file["data_id"] = _slug(path_obj.stem)[:128]
        if args.is_ocr is not None:
            req_file["is_ocr"] = bool(args.is_ocr)
        if args.page_ranges is not None:
            req_file["page_ranges"] = args.page_ranges

        obj_apply = client.apply_file_upload_urls_batch(
            files=[req_file],
            model_version=model_version,
            enable_formula=bool(args.enable_formula) if args.enable_formula is not None else None,
            enable_table=bool(args.enable_table) if args.enable_table is not None else None,
            language=args.language,
            extra_formats=extra_formats or None,
        )
        if (obj_apply.get("code") or 0) != 0:
            raise MinerUError(f"申请上传地址失败：{obj_apply}")
        data = obj_apply.get("data") or {}
        batch_id = data.get("batch_id")
        upload_urls = data.get("file_urls") or data.get("files") or []
        if not batch_id or not isinstance(upload_urls, list) or len(upload_urls) != 1:
            raise MinerUError(f"上传地址返回格式异常：{obj_apply}")

        print(f"[mineru] uploading {path_obj} -> presigned_url")
        status_code, _text = client.upload_file_to_presigned_url(str(upload_urls[0]), str(path_obj), timeout_s=args.upload_timeout)
        if status_code != 200:
            raise MinerUError(f"上传失败：{path_obj}（HTTP {status_code}）")

        obj_batch = _poll_batch(client, str(batch_id), poll_interval_s=args.poll_interval, timeout_s=args.timeout)
        results = (obj_batch.get("data") or {}).get("extract_result") or []
        if not results:
            raise MinerUError(f"批量结果为空：{obj_batch}")
        result = results[0]

        _safe_write_json(case_dir / "meta.json", result)
        if result.get("state") == "done" and result.get("full_zip_url"):
            out = _download_and_materialize_zip(zip_url=str(result["full_zip_url"]), out_dir=case_dir, keep_zip=args.keep_zip)
            _safe_write_json(case_dir / "materialize.json", out)

        run_meta["finished_at"] = dt.datetime.now().isoformat()
        run_meta["state"] = result.get("state")
        _safe_write_json(case_dir / "run_meta.json", run_meta)

    def _extract_url_single(url: str, *, case_dir: Path) -> None:
        case_dir.mkdir(parents=True, exist_ok=True)
        run_meta = _safe_run_meta({"type": "url", "url": url})

        obj_create = client.create_extract_task_url(
            url=url,
            model_version=model_version,
            data_id=_slug(Path(url).stem)[:128] if args.auto_data_id else None,
            is_ocr=args.is_ocr,
            enable_formula=args.enable_formula,
            enable_table=args.enable_table,
            language=args.language,
            page_ranges=args.page_ranges,
            extra_formats=extra_formats or None,
            no_cache=args.no_cache,
            cache_tolerance=args.cache_tolerance,
        )
        if (obj_create.get("code") or 0) != 0:
            raise MinerUError(f"创建 URL 任务失败：{obj_create}")
        task_id = (obj_create.get("data") or {}).get("task_id")
        if not task_id:
            raise MinerUError(f"创建任务缺少 task_id：{obj_create}")
        obj_done = _poll_task(client, str(task_id), poll_interval_s=args.poll_interval, timeout_s=args.timeout)

        _safe_write_json(case_dir / "meta.json", obj_done)
        data = obj_done.get("data") or {}
        if data.get("state") == "done" and data.get("full_zip_url"):
            out = _download_and_materialize_zip(zip_url=str(data["full_zip_url"]), out_dir=case_dir, keep_zip=args.keep_zip)
            _safe_write_json(case_dir / "materialize.json", out)

        run_meta["finished_at"] = dt.datetime.now().isoformat()
        run_meta["state"] = data.get("state")
        _safe_write_json(case_dir / "run_meta.json", run_meta)

    if out_dir_arg:
        total_inputs = [str(path_obj) for path_obj in local_paths] + list(url_inputs)
        if len(total_inputs) != 1:
            raise MinerUError("--out-dir 只能配合单个输入使用。")
        case_dir = Path(out_dir_arg).expanduser()
        if not case_dir.is_absolute():
            case_dir = (Path.cwd() / case_dir).resolve()
        if local_paths:
            _extract_local_single(local_paths[0], case_dir=case_dir)
        else:
            _extract_url_single(url_inputs[0], case_dir=case_dir)
        print(f"[mineru] done. outputs at: {case_dir}")
        return 0

    if out_root:
        run_dir = Path(out_root).expanduser()
        if not run_dir.is_absolute():
            run_dir = (Path.cwd() / run_dir).resolve()
        run_dir = run_dir / f"mineru_extract_{_now_id()}"
        run_dir.mkdir(parents=True, exist_ok=True)
        for path_obj in local_paths:
            _extract_local_single(path_obj, case_dir=run_dir / _slug(path_obj.stem))
        for url in url_inputs:
            _extract_url_single(url, case_dir=run_dir / _slug(Path(url).stem))
        _safe_write_json(
            run_dir / "run_meta.json",
            {
                "run_dir": str(run_dir),
                "model_version": model_version,
                "extra_formats": extra_formats,
                "token": {"exp": token.payload.get("exp")},
                "inputs": {"local": [str(path_obj) for path_obj in local_paths], "url": list(url_inputs)},
                "finished_at": dt.datetime.now().isoformat(),
            },
        )
        print(f"[mineru] done. outputs at: {run_dir}")
        return 0

    for path_obj in local_paths:
        _extract_local_single(path_obj, case_dir=_default_out_dir_for_local(path_obj))
    for url in url_inputs:
        _extract_url_single(url, case_dir=_default_out_dir_for_url(url))
    print("[mineru] done.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rcbevdet-mineru-extract")
    parser.add_argument(
        "--token-file",
        default=None,
        help=(
            "MinerU 鉴权文件路径。默认优先使用工具包内的 "
            f"`{default_token_file()}`，若不存在则回退到 `{default_legacy_token_file()}`。"
        ),
    )
    parser.add_argument("--user-token", default=None, help="手动覆盖请求头中的 `token` 字段。")
    parser.add_argument("--http-timeout", type=int, default=60, help="MinerU API 请求超时（秒）。")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="cmd", required=True)

    sub_paths = sub.add_parser("paths", help="打印工具包路径解析结果。")
    sub_paths.set_defaults(func=cmd_paths)

    sub_quota = sub.add_parser("quota", help="查询 MinerU 配额。")
    sub_quota.set_defaults(func=cmd_quota)

    sub_extract = sub.add_parser("extract", help="通过 MinerU 解析本地文件或 URL，并落盘成可复用目录。")
    sub_extract.add_argument("inputs", nargs="*", help="本地文件路径或 URL。")
    sub_extract.add_argument("--url", action="append", default=[], help="额外追加一个 URL 输入，可重复传入。")
    sub_extract.add_argument(
        "--out-root",
        default="",
        help="集中输出根目录；若不传，本地文件默认输出到输入文件旁边，URL 默认输出到工具包 `out/` 目录。",
    )
    sub_extract.add_argument(
        "--out-dir",
        default=None,
        help="单个输入的固定输出目录；仅允许搭配一个输入使用。",
    )
    sub_extract.add_argument("--model-version", default="pipeline", help="MinerU model_version，例如 pipeline / vlm / MinerU-HTML。")
    sub_extract.add_argument(
        "--extra-format",
        "--extra-formats",
        dest="extra_formats",
        action="append",
        default=[],
        choices=["docx", "html", "latex"],
        help="额外导出格式，可重复传入。",
    )
    _add_bool_optional_argument(sub_extract, "--is-ocr", default=None, help_text="是否启用 OCR。")
    _add_bool_optional_argument(sub_extract, "--enable-formula", default=None, help_text="是否启用公式识别。")
    _add_bool_optional_argument(sub_extract, "--enable-table", default=None, help_text="是否启用表格识别。")
    sub_extract.add_argument("--language", default=None, help="文档语言提示，例如 `ch`。")
    sub_extract.add_argument("--page-ranges", default=None, help="页码范围，例如 `2,4-6`。")
    _add_bool_optional_argument(sub_extract, "--no-cache", default=None, help_text="URL 模式下是否跳过缓存。")
    sub_extract.add_argument("--cache-tolerance", type=int, default=None, help="URL 模式下缓存容忍秒数。")
    sub_extract.add_argument("--poll-interval", type=int, default=5, help="轮询间隔秒数。")
    sub_extract.add_argument("--timeout", type=int, default=3600, help="等待任务完成的最长秒数。")
    sub_extract.add_argument("--upload-timeout", type=int, default=1800, help="上传单个文件的超时秒数。")
    sub_extract.add_argument("--keep-zip", action="store_true", help="保留下载的 `mineru_full.zip`。")
    sub_extract.add_argument(
        "--auto-data-id",
        action="store_true",
        default=True,
        help="是否按输入文件名自动生成 `data_id`，默认开启；可用 --no-auto-data-id 关闭。",
    )
    sub_extract.add_argument("--no-auto-data-id", dest="auto_data_id", action="store_false", help=argparse.SUPPRESS)
    sub_extract.set_defaults(func=cmd_extract)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (MinerUError, ValueError) as exc:
        print(f"[mineru][ERROR] {exc}")
        return 2
