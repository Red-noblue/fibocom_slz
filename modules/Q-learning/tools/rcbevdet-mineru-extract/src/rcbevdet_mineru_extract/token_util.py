# -*- coding: utf-8 -*-
# 鉴权解析说明：统一加载工具包内的 key/token 文件，并兼容历史 JWT 单行文件。
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .layout import default_legacy_token_file, default_token_file, toolkit_root


@dataclass(frozen=True)
class MinerUToken:
    bearer_jwt: str
    user_token: str
    payload: Dict[str, Any]


def _jwt_payload(jwt: str) -> Dict[str, Any]:
    parts = (jwt or "").strip().split(".")
    if len(parts) < 2:
        return {}
    payload_b64 = parts[1]
    payload_b64 += "=" * ((4 - (len(payload_b64) % 4)) % 4)
    try:
        raw = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
        return json.loads(raw.decode("utf-8", errors="replace"))
    except Exception:
        return {}


def derive_user_token_from_payload(payload: Dict[str, Any]) -> Optional[str]:
    for key in ("uuid", "clientId", "jti"):
        value = payload.get(key)
        if value:
            return str(value)
    return None


def _resolve_token_path(token_file: Optional[str]) -> Path:
    raw = (token_file or "").strip()
    candidates = []
    if not raw:
        candidates = [default_token_file(), default_legacy_token_file()]
    else:
        path_obj = Path(raw).expanduser()
        if path_obj.is_absolute():
            candidates.append(path_obj)
        else:
            candidates.append((Path.cwd() / path_obj).resolve())
            candidates.append((toolkit_root() / path_obj).resolve())
            if raw.startswith("RCBEVDet/"):
                candidates.append((toolkit_root() / raw[len("RCBEVDet/") :]).resolve())

    seen = set()
    for candidate in candidates:
        normalized = str(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)
        if candidate.exists():
            return candidate
    tried = ", ".join(str(path_obj) for path_obj in candidates) or str(default_token_file())
    raise ValueError(f"未找到 token 文件，尝试过：{tried}")


def load_token(token_file: Optional[str], user_token: Optional[str] = None) -> MinerUToken:
    token_path = _resolve_token_path(token_file)
    text = token_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"token 文件为空：{token_path}")

    jwt: Optional[str] = None
    file_user_token: Optional[str] = None
    if text.startswith("{"):
        try:
            payload_obj = json.loads(text)
        except Exception as exc:
            raise ValueError(f"token JSON 非法：{token_path}: {exc}") from exc
        jwt = payload_obj.get("bearer_jwt") or payload_obj.get("jwt") or payload_obj.get("authorization") or payload_obj.get("Authorization")
        file_user_token = payload_obj.get("user_token") or payload_obj.get("token")
    else:
        jwt = text

    if not jwt:
        raise ValueError(f"token 文件缺少 bearer_jwt：{token_path}")

    payload = _jwt_payload(jwt)
    resolved_user_token = user_token or (str(file_user_token) if file_user_token else None) or derive_user_token_from_payload(payload) or jwt
    return MinerUToken(bearer_jwt=jwt, user_token=resolved_user_token, payload=payload)
