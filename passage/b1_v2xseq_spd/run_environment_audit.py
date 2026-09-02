#!/usr/bin/env python3
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def run_text(command):
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    return {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def main():
    report_path = Path(r"D:\Dproject_coop3d\DATA\reports\v2x_seq_spd_environment_audit.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    pip_show = run_text("py -3.11 -m pip show mmcv-lite mmengine mmdet mmdet3d torch torchvision pypcd python-lzf")
    nvidia = run_text("nvidia-smi")

    report = {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "module_presence": {
            "torch": has_module("torch"),
            "torchvision": has_module("torchvision"),
            "mmcv": has_module("mmcv"),
            "mmcv.runner": has_module("mmcv.runner"),
            "mmengine": has_module("mmengine"),
            "mmdet": has_module("mmdet"),
            "mmdet3d": has_module("mmdet3d"),
            "pypcd": has_module("pypcd"),
            "open3d": has_module("open3d"),
        },
        "nvidia_smi": nvidia,
        "pip_show": pip_show,
        "summary": {
            "ready_for_official_dair_eval": False,
            "blocking_items": [
                "mmdet3d missing",
                "mmdet missing",
                "mmcv.runner missing because current env uses mmcv-lite 2.x",
                "official pretrained checkpoints are not present locally",
                "installed pypcd package is legacy and not Python 3.11 compatible for direct upstream use",
            ],
            "current_fastest_working_scope": [
                "SPD raw data preparation",
                "integrity and sanity checks",
                "detection KITTI conversion",
                "tracking KITTI label conversion",
                "dataset smoke checks",
            ],
        },
    }

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Environment audit written to: {report_path}")


if __name__ == "__main__":
    main()
