# -*- coding: utf-8 -*-
# API 客户端说明：封装 MinerU v4 接口调用，并对敏感请求头做脱敏输出。
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests


class MinerUError(RuntimeError):
    """MinerU 相关错误。"""


@dataclass(frozen=True)
class MinerUAuth:
    bearer_jwt: str
    user_token: str


def _redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    redacted = dict(headers)
    if "Authorization" in redacted:
        redacted["Authorization"] = "Bearer ***"
    if "token" in redacted:
        redacted["token"] = "***"
    return redacted


class MinerUClient:
    """面向 MinerU API v4 的最小客户端。"""

    def __init__(self, auth: MinerUAuth, base_url: str = "https://mineru.net/api/v4", timeout_s: int = 60) -> None:
        self._auth = auth
        self._base_url = base_url.rstrip("/")
        self._timeout_s = int(timeout_s)
        self._session = requests.Session()

    def _json_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._auth.bearer_jwt}",
            "token": self._auth.user_token,
            "Content-Type": "application/json",
            "Accept": "*/*",
        }

    def _request_json(self, method: str, path: str, *, json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        headers = self._json_headers()
        try:
            response = self._session.request(method, url, headers=headers, json=json_body, timeout=self._timeout_s)
        except Exception as exc:
            raise MinerUError(f"请求失败：{method} {url}: {exc}") from exc

        if response.status_code != 200:
            raise MinerUError(
                "HTTP {status} for {method} {url}. headers={headers} body={body} resp={resp}".format(
                    status=response.status_code,
                    method=method,
                    url=url,
                    headers=_redact_headers(headers),
                    body=json.dumps(json_body, ensure_ascii=False),
                    resp=response.text[:500],
                )
            )
        try:
            return response.json()
        except Exception as exc:
            raise MinerUError(f"返回不是 JSON：{method} {url}: {response.text[:500]}") from exc

    def quota(self) -> Dict[str, Any]:
        return self._request_json("GET", "/quota", json_body=None)

    def create_extract_task_url(
        self,
        *,
        url: str,
        model_version: str = "pipeline",
        data_id: Optional[str] = None,
        is_ocr: Optional[bool] = None,
        enable_formula: Optional[bool] = None,
        enable_table: Optional[bool] = None,
        language: Optional[str] = None,
        page_ranges: Optional[str] = None,
        extra_formats: Optional[List[str]] = None,
        no_cache: Optional[bool] = None,
        cache_tolerance: Optional[int] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"url": url, "model_version": model_version}
        if data_id is not None:
            body["data_id"] = data_id
        if is_ocr is not None:
            body["is_ocr"] = bool(is_ocr)
        if enable_formula is not None:
            body["enable_formula"] = bool(enable_formula)
        if enable_table is not None:
            body["enable_table"] = bool(enable_table)
        if language is not None:
            body["language"] = language
        if page_ranges is not None:
            body["page_ranges"] = page_ranges
        if extra_formats:
            body["extra_formats"] = extra_formats
        if no_cache is not None:
            body["no_cache"] = bool(no_cache)
        if cache_tolerance is not None:
            body["cache_tolerance"] = int(cache_tolerance)
        return self._request_json("POST", "/extract/task", json_body=body)

    def get_extract_task(self, task_id: str) -> Dict[str, Any]:
        return self._request_json("GET", f"/extract/task/{task_id}", json_body=None)

    def get_extract_results_batch(self, batch_id: str) -> Dict[str, Any]:
        return self._request_json("GET", f"/extract-results/batch/{batch_id}", json_body=None)

    def apply_file_upload_urls_batch(
        self,
        *,
        files: List[Dict[str, Any]],
        model_version: str = "pipeline",
        enable_formula: Optional[bool] = None,
        enable_table: Optional[bool] = None,
        language: Optional[str] = None,
        extra_formats: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"files": files, "model_version": model_version}
        if enable_formula is not None:
            body["enable_formula"] = bool(enable_formula)
        if enable_table is not None:
            body["enable_table"] = bool(enable_table)
        if language is not None:
            body["language"] = language
        if extra_formats:
            body["extra_formats"] = extra_formats
        return self._request_json("POST", "/file-urls/batch", json_body=body)

    def upload_file_to_presigned_url(self, upload_url: str, file_path: str, *, timeout_s: int = 1800) -> Tuple[int, str]:
        try:
            with open(file_path, "rb") as handle:
                response = self._session.put(upload_url, data=handle, timeout=timeout_s)
        except Exception as exc:
            raise MinerUError(f"上传失败：PUT {upload_url} <- {file_path}: {exc}") from exc
        return response.status_code, response.text[:200]
