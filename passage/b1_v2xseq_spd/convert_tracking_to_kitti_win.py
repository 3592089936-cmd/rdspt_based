#!/usr/bin/env python3
import argparse
import json
import math
import shutil
from pathlib import Path

import numpy as np


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def trans_point(input_point, rotation, translation=None):
    if translation is None:
        translation = [0.0, 0.0, 0.0]
    input_point = np.array(input_point, dtype=np.float64).reshape(3, 1)
    translation = np.array(translation, dtype=np.float64).reshape(3, 1)
    rotation = np.array(rotation, dtype=np.float64).reshape(3, 3)
    output_point = rotation @ input_point + translation
    return output_point.reshape(3).tolist()


def get_lidar_3d_8points(label_3d_dimensions, lidar_3d_location, rotation_z):
    lidar_rotation = np.array(
        [
            [math.cos(rotation_z), -math.sin(rotation_z), 0],
            [math.sin(rotation_z), math.cos(rotation_z), 0],
            [0, 0, 1],
        ],
        dtype=np.float64,
    )
    l, w, h = label_3d_dimensions
    corners_3d_lidar = np.array(
        [
            [l / 2, l / 2, -l / 2, -l / 2, l / 2, l / 2, -l / 2, -l / 2],
            [w / 2, -w / 2, -w / 2, w / 2, w / 2, -w / 2, -w / 2, w / 2],
            [-h / 2, -h / 2, -h / 2, -h / 2, h / 2, h / 2, h / 2, h / 2],
        ],
        dtype=np.float64,
    )
    corners = lidar_rotation @ corners_3d_lidar + np.array(lidar_3d_location, dtype=np.float64).reshape(3, 1)
    return corners.T.tolist()


def get_camera_3d_alpha_rotation(camera_3d_8_points, camera_3d_location):
    x0, z0 = camera_3d_8_points[0][0], camera_3d_8_points[0][2]
    x3, z3 = camera_3d_8_points[3][0], camera_3d_8_points[3][2]
    dx, dz = x0 - x3, z0 - z3
    rotation_y = -math.atan2(dz, dx)
    alpha = rotation_y - (-math.atan2(-camera_3d_location[2], -camera_3d_location[0])) + math.pi / 2
    if alpha > math.pi:
        alpha -= 2.0 * math.pi
    if alpha <= -math.pi:
        alpha += 2.0 * math.pi
    return alpha, rotation_y


def get_lidar2camera(path_lidar2camera: Path):
    lidar2camera = read_json(path_lidar2camera)
    rotation = np.array(lidar2camera["rotation"], dtype=np.float64).reshape(3, 3)
    translation = np.array(lidar2camera["translation"], dtype=np.float64).reshape(3, 1)
    return rotation, translation


def concat_txt(input_path: Path, output_path: Path, output_file_name: str):
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / f"{output_file_name}.txt"
    lines = []
    for file in sorted(input_path.iterdir()):
        if file.is_file():
            lines.extend(file.read_text(encoding="utf-8").splitlines())
    output_file.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def label_dair2kitti_by_frame(dair_label_file_path: Path, kitti_label_file_path: Path, rotation, translation, frame, pointcloud_timestamp, no_classmerge):
    labels = read_json(dair_label_file_path)
    lines = []
    for label in labels:
        obj_type = label["type"]
        if not no_classmerge:
            obj_type = obj_type.replace("Truck", "Car").replace("Van", "Car").replace("Bus", "Car")
        label_3d_dimensions = [
            float(label["3d_dimensions"]["l"]),
            float(label["3d_dimensions"]["w"]),
            float(label["3d_dimensions"]["h"]),
        ]
        lidar_3d_location = [
            float(label["3d_location"]["x"]),
            float(label["3d_location"]["y"]),
            float(label["3d_location"]["z"]),
        ]
        rotation_z = float(label["rotation"])
        lidar_3d_8_points = get_lidar_3d_8points(label_3d_dimensions, lidar_3d_location, rotation_z)

        lidar_3d_bottom_location = [
            lidar_3d_location[0],
            lidar_3d_location[1],
            lidar_3d_location[2] - label_3d_dimensions[2] / 2,
        ]
        camera_3d_location = trans_point(lidar_3d_bottom_location, rotation, translation)
        camera_3d_8_points = [trans_point(point, rotation, translation) for point in lidar_3d_8_points]
        alpha, rotation_y = get_camera_3d_alpha_rotation(camera_3d_8_points, camera_3d_location)

        line_items = [
            frame,
            str(obj_type),
            str(label["track_id"]),
            str(label["truncated_state"]),
            str(label["occluded_state"]),
            str(alpha),
            str(label["2d_box"]["xmin"]),
            str(label["2d_box"]["ymin"]),
            str(label["2d_box"]["xmax"]),
            str(label["2d_box"]["ymax"]),
            str(label_3d_dimensions[2]),
            str(label_3d_dimensions[1]),
            str(label_3d_dimensions[0]),
            str(camera_3d_location[0]),
            str(camera_3d_location[1]),
            str(camera_3d_location[2]),
            str(rotation_y),
            str(lidar_3d_location[0]),
            str(lidar_3d_location[1]),
            str(lidar_3d_location[2]),
            str(rotation_z),
            str(pointcloud_timestamp),
            "1",
            "1",
            str(label["token"]),
        ]
        lines.append(" ".join(line_items))
    kitti_label_file_path.parent.mkdir(parents=True, exist_ok=True)
    kitti_label_file_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Windows-friendly SPD cooperative tracking to KITTI converter.")
    parser.add_argument("--source-root", default=r"D:\Dproject_coop3d\DATA\raw\V2X-Seq-SPD", help="SPD dataset root.")
    parser.add_argument("--target-root", default=r"D:\Dproject_coop3d\DATA\processed\V2X-Seq-SPD-KITTI\cooperative", help="Tracking KITTI output root.")
    parser.add_argument(
        "--split-path",
        default=r"D:\Dproject_coop3d\DAIR-V2X\data\split_datas\cooperative-split-data-spd.json",
        help="Official SPD split file.",
    )
    parser.add_argument("--no-classmerge", action="store_true")
    parser.add_argument("--temp-root", default=r"D:\Dproject_coop3d\DATA\processed\_tmp_spd_tracking", help="Temporary split tracking label root.")
    args = parser.parse_args()

    source_root = Path(args.source_root)
    target_root = Path(args.target_root)
    temp_root = Path(args.temp_root)
    split_info = read_json(Path(args.split_path))
    frame_info = read_json(source_root / "cooperative" / "data_info.json")

    dict_sequence2tvt = {}
    for src, dst in (("train", "training"), ("val", "validation"), ("test", "testing")):
        for seq in split_info["batch_split"][src]:
            dict_sequence2tvt[seq] = dst

    if temp_root.exists():
        shutil.rmtree(temp_root)
    temp_root.mkdir(parents=True, exist_ok=True)
    target_root.mkdir(parents=True, exist_ok=True)

    for item in frame_info:
        rotation, translation = get_lidar2camera(
            source_root / "vehicle-side" / "calib" / "lidar_to_camera" / f'{item["vehicle_frame"]}.json'
        )
        tvt = dict_sequence2tvt[item["vehicle_sequence"]]
        temp_label_path = temp_root / tvt / item["vehicle_sequence"] / "label_02_split"
        temp_label_file_path = temp_label_path / f'{item["vehicle_frame"]}.txt'
        label_dair2kitti_by_frame(
            source_root / "cooperative" / "label" / f'{item["vehicle_frame"]}.json',
            temp_label_file_path,
            rotation,
            translation,
            item["vehicle_frame"],
            "-1",
            args.no_classmerge,
        )

    for tvt_dir in sorted(temp_root.iterdir()):
        if not tvt_dir.is_dir():
            continue
        for seq_dir in sorted(tvt_dir.iterdir()):
            if not seq_dir.is_dir():
                continue
            concat_txt(seq_dir / "label_02_split", target_root / tvt_dir.name / seq_dir.name / "label_02", seq_dir.name)

    shutil.rmtree(temp_root, ignore_errors=True)
    print(f"Tracking conversion finished: {target_root}")


if __name__ == "__main__":
    main()
