#!/usr/bin/env python3
# 中文说明：该脚本生成 QNN HTP/CDSP 专项用的 radio-map ONNX 变体，当前第一版只把 reflect Pad 改写为 constant zero Pad。

import argparse
import json
from pathlib import Path
from typing import Dict, List

import onnx


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成 QNN HTP/CDSP 友好的 radio-map ONNX 变体")
    parser.add_argument(
        "--input-onnx",
        default="modules/fiboaistack_229_env/inputs/radio_map_liteunet.onnx",
        help="原始 radio-map ONNX 路径",
    )
    parser.add_argument(
        "--output-onnx",
        default="modules/fiboaistack_229_env/inputs/qnn_htp_rewrite/radio_map_liteunet_pad_constant.onnx",
        help="改写后的 ONNX 输出路径",
    )
    parser.add_argument(
        "--report",
        default="modules/fiboaistack_229_env/inputs/qnn_htp_rewrite/radio_map_liteunet_pad_constant.report.json",
        help="改写报告 JSON 路径",
    )
    parser.add_argument(
        "--pad-mode",
        default="constant",
        choices=["constant"],
        help="当前只支持把 reflect Pad 改为 constant zero Pad",
    )
    return parser


def get_attr_dict(node: onnx.NodeProto) -> Dict[str, object]:
    return {attr.name: onnx.helper.get_attribute_value(attr) for attr in node.attribute}


def set_pad_mode_constant(node: onnx.NodeProto) -> None:
    kept_attrs = [attr for attr in node.attribute if attr.name != "mode"]
    del node.attribute[:]
    node.attribute.extend(kept_attrs)
    node.attribute.append(onnx.helper.make_attribute("mode", "constant"))


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input_onnx)
    output_path = Path(args.output_onnx)
    report_path = Path(args.report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    model = onnx.load(str(input_path))
    changed: List[Dict[str, object]] = []
    unchanged_pad: List[Dict[str, object]] = []

    for node in model.graph.node:
        if node.op_type != "Pad":
            continue
        attrs = get_attr_dict(node)
        mode = attrs.get("mode", b"constant")
        if isinstance(mode, bytes):
            mode_text = mode.decode("utf-8")
        else:
            mode_text = str(mode)
        record = {
            "name": node.name,
            "inputs": list(node.input),
            "outputs": list(node.output),
            "old_mode": mode_text,
        }
        if mode_text == "reflect":
            set_pad_mode_constant(node)
            record["new_mode"] = "constant"
            changed.append(record)
        else:
            unchanged_pad.append(record)

    onnx.checker.check_model(model)
    onnx.save(model, str(output_path))

    report = {
        "input_onnx": str(input_path),
        "output_onnx": str(output_path),
        "rewrite": "reflect Pad -> constant zero Pad",
        "changed_pad_count": len(changed),
        "unchanged_pad_count": len(unchanged_pad),
        "changed_pad_nodes": changed,
        "unchanged_pad_nodes": unchanged_pad,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
