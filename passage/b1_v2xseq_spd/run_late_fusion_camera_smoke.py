import argparse
import inspect
import os
import sys
import types
from pathlib import Path

import numpy as np


def _install_pypcd_stub():
    if "pypcd" in sys.modules:
        return
    package = types.ModuleType("pypcd")
    submodule = types.ModuleType("pypcd.pypcd")

    class _PointCloudStub:
        @staticmethod
        def from_path(path):
            raise RuntimeError(f"pypcd stub should not be used to read point clouds during camera smoke: {path}")

    submodule.PointCloud = _PointCloudStub
    package.pypcd = submodule
    sys.modules["pypcd"] = package
    sys.modules["pypcd.pypcd"] = submodule


def _patch_os_system_for_windows():
    original = os.system

    def wrapped(command):
        if command.startswith("mkdir -p "):
            target = command[len("mkdir -p "):].strip().strip('"')
            Path(target).mkdir(parents=True, exist_ok=True)
            return 0
        return original(command)

    os.system = wrapped


def _bootstrap_v2x_paths(dair_v2x_root):
    v2x_root = os.path.join(dair_v2x_root, "v2x")
    os.chdir(v2x_root)
    extra_paths = [
        os.path.abspath(".."),
        os.path.abspath("."),
        os.path.abspath("./dataset"),
        os.path.abspath("./dataset/dataset_utils"),
        os.path.abspath("./models"),
        os.path.abspath("./models/detection_models"),
        os.path.abspath("./models/model_utils"),
        os.path.abspath("./v2x_utils"),
    ]
    for path in extra_paths:
        if path not in sys.path:
            sys.path.append(path)


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    dair_v2x_root = os.path.join(root, "DAIR-V2X")
    _install_pypcd_stub()
    _patch_os_system_for_windows()
    _bootstrap_v2x_paths(dair_v2x_root)

    from config import add_arguments
    from dataset import SUPPROTED_DATASETS
    from models import SUPPROTED_MODELS
    from models.model_utils import Channel
    from v2x_utils import Evaluator, range2box

    parser = argparse.ArgumentParser(conflict_handler="resolve")
    add_arguments(parser)
    parser.add_argument(
        "--input",
        default="../data/V2X-Seq-SPD",
    )
    parser.add_argument(
        "--output",
        default="../output/spd_late_fusion_camera_oneframe",
    )
    parser.add_argument(
        "--split-data-path",
        default="../data/split_datas/cooperative-split-data-spd.json",
    )
    parser.add_argument(
        "--inf-config-path",
        default="../configs/vic3d-spd/late-fusion-image/imvoxelnet/trainval_config_i.py",
    )
    parser.add_argument(
        "--inf-model-path",
        default="../configs/vic3d-spd/late-fusion-image/imvoxelnet/vic3d_latefusion_imvoxelnet_i.pth",
    )
    parser.add_argument(
        "--veh-config-path",
        default="../configs/vic3d-spd/late-fusion-image/imvoxelnet/trainval_config_v.py",
    )
    parser.add_argument(
        "--veh-model-path",
        default="../configs/vic3d-spd/late-fusion-image/imvoxelnet/vic3d_latefusion_imvoxelnet_v.pth",
    )
    parser.add_argument(
        "--index",
        type=int,
        default=0,
    )
    base_cli = [
        "--model",
        "late_fusion",
        "--dataset",
        "vic-sync-spd",
        "--split",
        "val",
        "--pred-classes",
        "car",
        "--sensortype",
        "camera",
        "--overwrite-cache",
        "--no-comp",
        "--inf-config-path",
        "../configs/vic3d-spd/late-fusion-image/imvoxelnet/trainval_config_i.py",
        "--inf-model-path",
        "../configs/vic3d-spd/late-fusion-image/imvoxelnet/vic3d_latefusion_imvoxelnet_i.pth",
        "--veh-config-path",
        "../configs/vic3d-spd/late-fusion-image/imvoxelnet/trainval_config_v.py",
        "--veh-model-path",
        "../configs/vic3d-spd/late-fusion-image/imvoxelnet/vic3d_latefusion_imvoxelnet_v.pth",
    ]
    base_args, _ = parser.parse_known_args(base_cli)
    SUPPROTED_MODELS[base_args.model].add_arguments(parser)
    args = parser.parse_args(base_cli + sys.argv[1:])

    extended_range = range2box(np.array(args.extended_range))
    print("stage=build_dataset", flush=True)
    dataset_cls = SUPPROTED_DATASETS[args.dataset]
    dataset_kwargs = {
        "split": args.split,
        "sensortype": args.sensortype,
        "extended_range": extended_range,
    }
    if "val_data_path" in inspect.signature(dataset_cls.__init__).parameters:
        dataset_kwargs["val_data_path"] = args.val_data_path
    dataset = dataset_cls(args.input, args, **dataset_kwargs)
    print(f"stage=dataset_ready len={len(dataset)}", flush=True)

    pipe = Channel()
    print("stage=build_model", flush=True)
    model = SUPPROTED_MODELS[args.model](args, pipe)
    evaluator = Evaluator(args.pred_classes)
    print("stage=model_ready", flush=True)

    vic_frame, label, filt = dataset[args.index]
    print(
        f"stage=frame_ready veh={vic_frame.vehicle_frame().id['camera']} inf={vic_frame.infrastructure_frame().id['camera']}",
        flush=True,
    )
    pred = model(vic_frame, filt, dataset.prev_inf_frame if hasattr(dataset, "prev_inf_frame") else None)
    print("stage=pred_ready", flush=True)
    evaluator.add_frame(pred, label)

    print(f"veh_frame={vic_frame.vehicle_frame().id['camera']}")
    print(f"inf_frame={vic_frame.infrastructure_frame().id['camera']}")
    print(f"pred_boxes={len(pred['boxes_3d'])}")
    evaluator.print_ap("3d")
    evaluator.print_ap("bev")


if __name__ == "__main__":
    main()
