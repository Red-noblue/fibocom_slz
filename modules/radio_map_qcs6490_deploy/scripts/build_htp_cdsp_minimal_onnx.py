#!/usr/bin/env python3
# 中文说明：该脚本生成 HTP/CDSP 专项最小 ONNX，用于分别验证普通 Conv、DepthWiseConv2d 与 INT8 Q/DQ 图在 QNN CPU/GPU/DSP 后端上的兼容性。

import argparse
from pathlib import Path
from typing import Tuple

import numpy as np
import torch
from onnx import TensorProto, helper, numpy_helper, save_model
from torch import nn


class PlainConv(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.conv = nn.Conv2d(3, 5, kernel_size=3, padding=1, bias=True)
        self._init_weights()

    def _init_weights(self) -> None:
        with torch.no_grad():
            self.conv.weight.fill_(0.03125)
            self.conv.bias.fill_(0.125)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(x)


class DepthwiseConv(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.conv = nn.Conv2d(4, 4, kernel_size=3, padding=1, groups=4, bias=True)
        self._init_weights()

    def _init_weights(self) -> None:
        with torch.no_grad():
            self.conv.weight.fill_(0.0625)
            self.conv.bias.fill_(0.125)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(x)


def export_torch_model(model: nn.Module, output_path: Path, input_shape: Tuple[int, ...], opset: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.eval()
    dummy = torch.arange(np.prod(input_shape), dtype=torch.float32).reshape(input_shape) / 64.0
    torch.onnx.export(
        model,
        dummy,
        str(output_path),
        opset_version=opset,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes=None,
    )


def export_qdq_int8_conv(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    input_shape = [1, 3, 8, 8]
    output_shape = [1, 5, 8, 8]
    weight = np.full((5, 3, 3, 3), 4, dtype=np.int8)
    bias = np.full((5,), 8, dtype=np.int32)
    initializers = [
        numpy_helper.from_array(np.array([0.03125], dtype=np.float32), "input_scale"),
        numpy_helper.from_array(np.array([0], dtype=np.int8), "input_zero_point"),
        numpy_helper.from_array(weight, "weight_q"),
        numpy_helper.from_array(np.array([0.015625], dtype=np.float32), "weight_scale"),
        numpy_helper.from_array(np.array([0], dtype=np.int8), "weight_zero_point"),
        numpy_helper.from_array(bias, "bias"),
    ]
    nodes = [
        helper.make_node("QuantizeLinear", ["input", "input_scale", "input_zero_point"], ["input_q"], name="input_quant"),
        helper.make_node("DequantizeLinear", ["input_q", "input_scale", "input_zero_point"], ["input_dq"], name="input_dequant"),
        helper.make_node("DequantizeLinear", ["weight_q", "weight_scale", "weight_zero_point"], ["weight_dq"], name="weight_dequant"),
        helper.make_node("Conv", ["input_dq", "weight_dq", "bias"], ["output"], name="qdq_conv", pads=[1, 1, 1, 1]),
    ]
    graph = helper.make_graph(
        nodes,
        "qdq_int8_conv",
        [helper.make_tensor_value_info("input", TensorProto.FLOAT, input_shape)],
        [helper.make_tensor_value_info("output", TensorProto.FLOAT, output_shape)],
        initializer=initializers,
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    save_model(model, output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成 HTP/CDSP 专项最小 ONNX")
    parser.add_argument("--output-dir", default="modules/fiboaistack_229_env/inputs/htp_cdsp_minimal", help="输出目录")
    parser.add_argument("--opset", type=int, default=17, help="PyTorch 导出 ONNX opset")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    cases = {
        "plain_conv": (PlainConv(), (1, 3, 8, 8)),
        "depthwise_conv": (DepthwiseConv(), (1, 4, 8, 8)),
    }
    for name, (model, input_shape) in cases.items():
        out_path = output_dir / f"{name}.onnx"
        export_torch_model(model, out_path, input_shape, args.opset)
        print(out_path)
    qdq_path = output_dir / "qdq_int8_conv.onnx"
    export_qdq_int8_conv(qdq_path)
    print(qdq_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
