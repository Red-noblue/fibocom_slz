#!/usr/bin/env python3
# 中文说明：该脚本生成 reflect Pad、constant Pad 和 Conv 内置 padding 三种最小 ONNX，用于定位 HTP/CDSP 对 Pad 表达的支持差异。

import argparse
from pathlib import Path

import torch
from torch import nn


class ReflectPadConv(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.pad = nn.ReflectionPad2d(1)
        self.conv = nn.Conv2d(1, 1, kernel_size=3, padding=0, bias=True)
        self._init_weights()

    def _init_weights(self) -> None:
        with torch.no_grad():
            self.conv.weight.fill_(0.125)
            self.conv.bias.fill_(0.25)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(self.pad(x))


class ConstantPadConv(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.pad = nn.ConstantPad2d(1, 0.0)
        self.conv = nn.Conv2d(1, 1, kernel_size=3, padding=0, bias=True)
        self._init_weights()

    def _init_weights(self) -> None:
        with torch.no_grad():
            self.conv.weight.fill_(0.125)
            self.conv.bias.fill_(0.25)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(self.pad(x))


class BuiltinPadConv(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.conv = nn.Conv2d(1, 1, kernel_size=3, padding=1, bias=True)
        self._init_weights()

    def _init_weights(self) -> None:
        with torch.no_grad():
            self.conv.weight.fill_(0.125)
            self.conv.bias.fill_(0.25)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(x)


def export_model(model: nn.Module, output_path: Path, opset: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.eval()
    dummy = torch.arange(1 * 1 * 8 * 8, dtype=torch.float32).reshape(1, 1, 8, 8) / 64.0
    torch.onnx.export(
        model,
        dummy,
        str(output_path),
        opset_version=opset,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes=None,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成 Pad 最小复现 ONNX")
    parser.add_argument("--output-dir", default="modules/fiboaistack_229_env/inputs/pad_minimal", help="输出目录")
    parser.add_argument("--opset", type=int, default=17, help="ONNX opset")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    cases = {
        "reflect_pad_conv": ReflectPadConv(),
        "constant_pad_conv": ConstantPadConv(),
        "builtin_pad_conv": BuiltinPadConv(),
    }
    for name, model in cases.items():
        out_path = output_dir / f"{name}.onnx"
        export_model(model, out_path, args.opset)
        print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
