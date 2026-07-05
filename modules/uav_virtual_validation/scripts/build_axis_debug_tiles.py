from __future__ import annotations

import json
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_virtual_validation.tiles.gltf_tiles import _enu_transform


def pad4(data: bytes) -> bytes:
    return data + b"\x00" * ((4 - len(data) % 4) % 4)


def main() -> None:
    out = ROOT / "outputs/debug/axis_tiles"
    out.mkdir(parents=True, exist_ok=True)
    center = {"lat": 40.7549, "lon": -73.984}
    # glTF Y-up local axes: X=east red, Y=up green, Z=-north blue.
    positions = [
        0, 0, 0, 500, 0, 0,
        0, 0, 0, 0, 500, 0,
        0, 0, 0, 0, 0, -500,
    ]
    colors = [
        1, 0, 0, 1, 1, 0, 0, 1,
        0, 1, 0, 1, 0, 1, 0, 1,
        0, 0, 1, 1, 0, 0, 1, 1,
    ]
    pos_bytes = struct.pack("<" + "f" * len(positions), *positions)
    color_bytes = struct.pack("<" + "f" * len(colors), *colors)
    blob = pad4(pos_bytes) + pad4(color_bytes)
    import base64
    encoded = base64.b64encode(blob).decode("ascii")
    gltf = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "COLOR_0": 1}, "mode": 1}]}],
        "buffers": [{"uri": f"data:application/octet-stream;base64,{encoded}", "byteLength": len(blob)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": len(pad4(pos_bytes)), "byteLength": len(color_bytes), "target": 34962},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 6, "type": "VEC3"},
            {"bufferView": 1, "componentType": 5126, "count": 6, "type": "VEC4"},
        ],
    }
    (out / "axis.gltf").write_text(json.dumps(gltf, separators=(",", ":")), encoding="utf-8")
    tileset = {
        "asset": {"version": "1.1"},
        "geometricError": 100,
        "root": {
            "boundingVolume": {"box": [0, 250, 0, 500, 0, 0, 0, 250, 0, 0, 0, 500]},
            "geometricError": 0,
            "refine": "ADD",
            "transform": _enu_transform(center["lat"], center["lon"], 0),
            "content": {"uri": "axis.gltf"},
        },
    }
    (out / "tileset.json").write_text(json.dumps(tileset, indent=2), encoding="utf-8")
    print(out / "tileset.json")


if __name__ == "__main__":
    main()
