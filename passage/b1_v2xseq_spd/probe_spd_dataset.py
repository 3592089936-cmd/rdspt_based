import argparse
import inspect
import os
import sys

import numpy as np


def _mark(status_file, message):
    if not status_file:
        return
    with open(status_file, "a", encoding="utf-8") as fh:
        fh.write(message + "\n")


def _extract_status_file(argv):
    for idx, value in enumerate(argv[:-1]):
        if value == "--status-file":
            return argv[idx + 1]
    return ""


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
    status_file = _extract_status_file(sys.argv)
    _mark(status_file, "stage=bootstrap_start")
    _bootstrap_v2x_paths(dair_v2x_root)
    _mark(status_file, "stage=bootstrap_done")

    _mark(status_file, "stage=imports_start")
    _mark(status_file, "stage=import_config_start")
    from config import add_arguments
    _mark(status_file, "stage=import_config_done")
    _mark(status_file, "stage=import_dataset_start")
    from dataset import SUPPROTED_DATASETS
    _mark(status_file, "stage=import_dataset_done")
    _mark(status_file, "stage=import_v2x_utils_start")
    from v2x_utils import range2box
    _mark(status_file, "stage=import_v2x_utils_done")
    _mark(status_file, "stage=imports_done")

    parser = argparse.ArgumentParser(conflict_handler="resolve")
    add_arguments(parser)
    parser.add_argument(
        "--input",
        default="../data/V2X-Seq-SPD",
    )
    parser.add_argument(
        "--split-data-path",
        default="../data/split_datas/cooperative-split-data-spd.json",
    )
    parser.add_argument(
        "--dataset",
        default="vic-sync-spd",
    )
    parser.add_argument(
        "--index",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--status-file",
        default="",
    )
    args = parser.parse_args()

    extended_range = range2box(np.array(args.extended_range))
    dataset_cls = SUPPROTED_DATASETS[args.dataset]
    dataset_kwargs = {
        "split": args.split,
        "sensortype": args.sensortype,
        "extended_range": extended_range,
    }
    if "val_data_path" in inspect.signature(dataset_cls.__init__).parameters:
        dataset_kwargs["val_data_path"] = args.val_data_path

    print("stage=build_dataset", flush=True)
    _mark(args.status_file, "stage=build_dataset")
    dataset = dataset_cls(args.input, args, **dataset_kwargs)
    print(f"stage=dataset_ready len={len(dataset)}", flush=True)
    _mark(args.status_file, f"stage=dataset_ready len={len(dataset)}")

    frame, label, filt = dataset[args.index]
    if "vic" in args.dataset:
        frame_msg = f"stage=frame_ready veh={frame.vehicle_frame().id['camera']} inf={frame.infrastructure_frame().id['camera']}"
        print(
            frame_msg,
            flush=True,
        )
    else:
        frame_msg = f"stage=frame_ready frame={frame.id['camera']}"
        print(frame_msg, flush=True)
    _mark(args.status_file, frame_msg)


if __name__ == "__main__":
    main()
