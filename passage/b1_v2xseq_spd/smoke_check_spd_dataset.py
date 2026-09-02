#!/usr/bin/env python3
import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
import types

import numpy as np


def install_pypcd_stub():
    if "pypcd" in sys.modules:
        return
    package = types.ModuleType("pypcd")
    submodule = types.ModuleType("pypcd.pypcd")

    class _PointCloudStub:
        @staticmethod
        def from_path(path):
            raise RuntimeError(f"pypcd stub should not be used to read point clouds during smoke check: {path}")

    submodule.PointCloud = _PointCloudStub
    package.pypcd = submodule
    sys.modules["pypcd"] = package
    sys.modules["pypcd.pypcd"] = submodule


def patch_os_system_for_windows():
    original = os.system

    def wrapped(command: str):
        if command.startswith("mkdir -p "):
            target = command[len("mkdir -p "):].strip().strip('"')
            Path(target).mkdir(parents=True, exist_ok=True)
            return 0
        return original(command)

    os.system = wrapped


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_dataset_module(dair_root: Path):
    install_pypcd_stub()
    patch_os_system_for_windows()
    sys.path.insert(0, str(dair_root / "v2x"))
    sys.path.insert(0, str(dair_root / "v2x" / "dataset"))
    sys.path.insert(0, str(dair_root / "v2x" / "dataset" / "dataset_utils"))
    dataset_pkg = types.ModuleType("dataset")
    dataset_pkg.__path__ = [str(dair_root / "v2x" / "dataset")]
    sys.modules["dataset"] = dataset_pkg
    dataset_utils = load_module(
        "dataset.dataset_utils",
        dair_root / "v2x" / "dataset" / "dataset_utils" / "__init__.py",
    )
    dataset_pkg.dataset_utils = dataset_utils
    detection_module = load_module(
        "dair_v2x_for_detection",
        dair_root / "v2x" / "dataset" / "dair_v2x_for_detection.py",
    )
    return detection_module


def summarize_sample(item):
    frame_obj, label, _ = item
    sample = {"frame_type": type(frame_obj).__name__}
    try:
        sample["keys"] = list(frame_obj.keys())[:8]
    except Exception:
        sample["keys"] = []
    try:
        if "boxes_3d" in label:
            sample["label_count"] = int(len(label["boxes_3d"]))
        elif "lidar" in label and "boxes_3d" in label["lidar"]:
            sample["label_count"] = int(len(label["lidar"]["boxes_3d"]))
        else:
            sample["label_count"] = None
    except Exception:
        sample["label_count"] = None
    return sample


def build_extended_range():
    box_range = np.array([-10.0, -49.68, -3.0, 79.12, 49.68, 1.0], dtype=np.float64)
    indexs = [
        [0, 1, 2],
        [3, 1, 2],
        [3, 4, 2],
        [0, 4, 2],
        [0, 1, 5],
        [3, 1, 5],
        [3, 4, 5],
        [0, 4, 5],
    ]
    return np.array([[box_range[index] for index in indexs]], dtype=np.float64)


def main():
    parser = argparse.ArgumentParser(description="Smoke check DAIR-V2X SPD dataset classes.")
    parser.add_argument("--dair-root", default=r"D:\Dproject_coop3d\DAIR-V2X", help="DAIR-V2X repo root.")
    parser.add_argument("--dataset-root", default=r"D:\Dproject_coop3d\DATA\raw\V2X-Seq-SPD", help="SPD dataset root.")
    parser.add_argument(
        "--split-path",
        default=r"D:\Dproject_coop3d\DAIR-V2X\data\split_datas\cooperative-split-data-spd.json",
        help="SPD split file path.",
    )
    parser.add_argument("--output", default=r"D:\Dproject_coop3d\DATA\reports\v2x_seq_spd_smoke_check.json", help="Smoke report path.")
    args = parser.parse_args()

    dair_root = Path(args.dair_root)
    dataset_root = Path(args.dataset_root)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    detection_module = load_dataset_module(dair_root)
    datasets = {
        "dair-v2x-v-spd": detection_module.DAIRV2XVSPD,
        "dair-v2x-i-spd": detection_module.DAIRV2XISPD,
        "vic-sync-spd": detection_module.VICSyncDatasetSPD,
    }
    opts = SimpleNamespace(split_data_path=args.split_path, model="baseline")
    extended_range = build_extended_range()

    report = {}
    for name in ["dair-v2x-v-spd", "dair-v2x-i-spd", "vic-sync-spd"]:
        dataset = datasets[name](str(dataset_root), opts, split="train", sensortype="lidar", extended_range=extended_range)
        report[name] = {
            "length": int(len(dataset)),
            "sample": summarize_sample(dataset[0]),
        }

    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
