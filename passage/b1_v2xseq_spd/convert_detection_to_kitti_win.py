#!/usr/bin/env python3
import argparse
import json
import math
import shutil
import struct
from pathlib import Path

import numpy as np
import lzf


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_pcd(path: Path):
    with path.open("rb") as f:
        header = {}
        while True:
            line = f.readline()
            if not line:
                raise ValueError(f"Incomplete PCD header: {path}")
            decoded = line.decode("ascii", errors="ignore").strip()
            if not decoded or decoded.startswith("#"):
                continue
            parts = decoded.split()
            key = parts[0].upper()
            values = parts[1:]
            header[key] = values
            if key == "DATA":
                break
        data = f.read()

    fields = header["FIELDS"]
    sizes = [int(x) for x in header["SIZE"]]
    types = header["TYPE"]
    counts = [int(x) for x in header.get("COUNT", ["1"] * len(fields))]
    points = int(header.get("POINTS", [header["WIDTH"][0]])[0])
    data_type = header["DATA"][0].lower()

    if data_type != "binary_compressed":
        raise ValueError(f"Unsupported PCD data mode: {data_type}")

    compressed_size, uncompressed_size = struct.unpack("<II", data[:8])
    compressed = data[8:8 + compressed_size]
    raw = lzf.decompress(compressed, uncompressed_size)
    if raw is None:
        raise ValueError(f"LZF decompression returned None for {path}")
    if len(raw) != uncompressed_size:
        raise ValueError(f"Unexpected decompressed size for {path}")

    field_values = {}
    offset = 0
    for field, size, typ, count in zip(fields, sizes, types, counts):
        block_size = points * size * count
        block = raw[offset:offset + block_size]
        offset += block_size
        dtype = pcd_dtype(typ, size)
        arr = np.frombuffer(block, dtype=dtype)
        if count > 1:
            arr = arr.reshape(points, count)
        field_values[field] = arr
    return field_values


def pcd_dtype(type_code: str, size: int):
    type_code = type_code.upper()
    mapping = {
        ("F", 4): np.float32,
        ("F", 8): np.float64,
        ("U", 1): np.uint8,
        ("U", 2): np.uint16,
        ("U", 4): np.uint32,
        ("I", 1): np.int8,
        ("I", 2): np.int16,
        ("I", 4): np.int32,
    }
    dtype = mapping.get((type_code, size))
    if dtype is None:
        raise ValueError(f"Unsupported PCD field type: {(type_code, size)}")
    return dtype


def pcd_to_bin(pcd_path: Path, bin_path: Path):
    data = parse_pcd(pcd_path)
    intensity = data["intensity"]
    if intensity.dtype == np.uint8:
        intensity = intensity.astype(np.float32) / 255.0
    else:
        intensity = intensity.astype(np.float32)
    points = np.column_stack(
        [
            data["x"].astype(np.float32),
            data["y"].astype(np.float32),
            data["z"].astype(np.float32),
            intensity,
        ]
    )
    bin_path.parent.mkdir(parents=True, exist_ok=True)
    points.tofile(bin_path)


def trans_point(input_point, rotation, translation=None):
    if translation is None:
        translation = [0.0, 0.0, 0.0]
    input_point = np.array(input_point).reshape(3, 1)
    translation = np.array(translation).reshape(3, 1)
    rotation = np.array(rotation).reshape(3, 3)
    output_point = np.dot(rotation, input_point).reshape(3, 1) + translation
    return output_point.reshape(1, 3).tolist()[0]


def get_lidar_3d_8points(label_3d_dimensions, lidar_3d_location, rotation_z):
    lidar_rotation = np.matrix(
        [
            [math.cos(rotation_z), -math.sin(rotation_z), 0],
            [math.sin(rotation_z), math.cos(rotation_z), 0],
            [0, 0, 1],
        ]
    )
    l, w, h = label_3d_dimensions
    corners_3d_lidar = np.matrix(
        [
            [l / 2, l / 2, -l / 2, -l / 2, l / 2, l / 2, -l / 2, -l / 2],
            [w / 2, -w / 2, -w / 2, w / 2, w / 2, -w / 2, -w / 2, w / 2],
            [-h / 2, -h / 2, -h / 2, -h / 2, h / 2, h / 2, h / 2, h / 2],
        ]
    )
    lidar_3d_8points = lidar_rotation * corners_3d_lidar + np.matrix(lidar_3d_location).T
    return lidar_3d_8points.T.tolist()


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


def get_cam_calib_intrinsic(calib_path: Path):
    cam_k = read_json(calib_path)["cam_K"]
    calib = np.zeros([3, 4], dtype=np.float64)
    calib[:3, :3] = np.array(cam_k).reshape([3, 3], order="C")
    return calib


def get_lidar2camera(path_lidar2camera: Path):
    lidar2camera = read_json(path_lidar2camera)
    rotation = np.array(lidar2camera["rotation"]).reshape(3, 3)
    translation = np.array(lidar2camera["translation"]).reshape(3, 1)
    return rotation, translation


def build_split_map(split_info):
    seq_to_split = {}
    for src, dst in (("train", "training"), ("val", "training"), ("test", "testing")):
        for seq in split_info["batch_split"][src]:
            seq_to_split[seq] = dst
    return seq_to_split


def copy_raw_data(source_root: Path, target_root: Path, split_map, frame_info):
    for item in frame_info:
        split_name = split_map[item["sequence_id"]]
        image_target = target_root / split_name / "image_2" / f'{item["frame_id"]}.jpg'
        velodyne_target = target_root / split_name / "velodyne" / f'{item["frame_id"]}.bin'
        image_target.parent.mkdir(parents=True, exist_ok=True)
        velodyne_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_root / item["image_path"], image_target)
        pcd_to_bin(source_root / item["pointcloud_path"], velodyne_target)


def convert_labels(source_root: Path, target_root: Path, split_map, frame_info, label_type: str, sensor_view: str, no_classmerge: bool):
    calib_key = "calib_lidar_to_camera_path" if sensor_view in {"vehicle", "cooperative"} else "calib_virtuallidar_to_camera_path"
    label_key = f"label_{label_type}_std_path"
    for item in frame_info:
        split_name = split_map[item["sequence_id"]]
        label_target = target_root / split_name / "label_2" / f'{item["frame_id"]}.txt'
        label_target.parent.mkdir(parents=True, exist_ok=True)
        rotation, translation = get_lidar2camera(source_root / item[calib_key])
        labels = read_json(source_root / item[label_key])
        with label_target.open("w", encoding="utf-8") as f:
            for label in labels:
                obj_type = label["type"]
                if not no_classmerge:
                    obj_type = obj_type.replace("Truck", "Car").replace("Van", "Car").replace("Bus", "Car")
                dims = [
                    float(label["3d_dimensions"]["l"]),
                    float(label["3d_dimensions"]["w"]),
                    float(label["3d_dimensions"]["h"]),
                ]
                loc = [
                    float(label["3d_location"]["x"]),
                    float(label["3d_location"]["y"]),
                    float(label["3d_location"]["z"]),
                ]
                rotation_z = float(label["rotation"])
                lidar_3d_8_points = get_lidar_3d_8points(dims, loc, rotation_z)
                lidar_bottom = [loc[0], loc[1], loc[2] - dims[2] / 2]
                camera_loc = trans_point(lidar_bottom, rotation, translation)
                camera_3d_8_points = [trans_point(point, rotation, translation) for point in lidar_3d_8_points]
                alpha, rotation_y = get_camera_3d_alpha_rotation(camera_3d_8_points, camera_loc)
                fields = [
                    str(obj_type),
                    str(label["truncated_state"]),
                    str(label["occluded_state"]),
                    str(alpha),
                    str(label["2d_box"]["xmin"]),
                    str(label["2d_box"]["ymin"]),
                    str(label["2d_box"]["xmax"]),
                    str(label["2d_box"]["ymax"]),
                    str(dims[2]),
                    str(dims[1]),
                    str(dims[0]),
                    str(camera_loc[0]),
                    str(camera_loc[1]),
                    str(camera_loc[2]),
                    str(rotation_y),
                ]
                f.write(" ".join(fields) + "\n")


def convert_calibs(source_root: Path, target_root: Path, split_map, frame_info, sensor_view: str):
    calib_key = "calib_lidar_to_camera_path" if sensor_view in {"vehicle", "cooperative"} else "calib_virtuallidar_to_camera_path"
    for item in frame_info:
        split_name = split_map[item["sequence_id"]]
        calib_target = target_root / split_name / "calib" / f'{item["frame_id"]}.txt'
        calib_target.parent.mkdir(parents=True, exist_ok=True)
        cam_intrinsic = get_cam_calib_intrinsic(source_root / item["calib_camera_intrinsic_path"])
        r_velo2cam, t_velo2cam = get_lidar2camera(source_root / item[calib_key])
        p2 = cam_intrinsic.reshape(12, order="C")
        tr_velo_to_cam = np.concatenate((r_velo2cam, t_velo2cam), axis=1).reshape(12, order="C")
        str_p2 = "P2: " + " ".join(str(x) for x in p2)
        str_tr = "Tr_velo_to_cam: " + " ".join(str(x) for x in tr_velo_to_cam)
        content = "\n".join(
            [
                str_p2.replace("P2:", "P0:"),
                str_p2.replace("P2:", "P1:"),
                str_p2,
                str_p2.replace("P2:", "P3:"),
                "R0_rect: 1 0 0 0 1 0 0 0 1",
                str_tr,
                str_tr.replace("Tr_velo_to_cam:", "Tr_imu_to_velo:"),
            ]
        )
        write_text(calib_target, content)


def gen_imagesets(target_root: Path, split_info, sensor_view: str):
    split_key = f"{sensor_view}_split"
    split_data = split_info[split_key]
    image_sets = target_root / "ImageSets"
    image_sets.mkdir(parents=True, exist_ok=True)
    train_text = "".join(f"{name}\n" for name in split_data["train"])
    val_text = "".join(f"{name}\n" for name in split_data["val"])
    write_text(image_sets / "train.txt", train_text)
    write_text(image_sets / "val.txt", val_text)
    write_text(image_sets / "trainval.txt", train_text + val_text)
    write_text(image_sets / "test.txt", "")


def main():
    parser = argparse.ArgumentParser(description="Windows-friendly SPD detection to KITTI converter.")
    parser.add_argument("--source-root", required=True, help="SPD side root, e.g. .../V2X-Seq-SPD/vehicle-side")
    parser.add_argument("--target-root", required=True, help="KITTI output root for one side")
    parser.add_argument(
        "--split-path",
        default=r"D:\Dproject_coop3d\DAIR-V2X\data\split_datas\cooperative-split-data-spd.json",
        help="Official SPD split file.",
    )
    parser.add_argument("--label-type", default="lidar", choices=["lidar", "camera"])
    parser.add_argument("--sensor-view", default="vehicle", choices=["vehicle", "infrastructure", "cooperative"])
    parser.add_argument("--no-classmerge", action="store_true")
    args = parser.parse_args()

    source_root = Path(args.source_root)
    target_root = Path(args.target_root)
    split_info = read_json(Path(args.split_path))
    split_map = build_split_map(split_info)
    frame_info = read_json(source_root / "data_info.json")

    copy_raw_data(source_root, target_root, split_map, frame_info)
    convert_labels(source_root, target_root, split_map, frame_info, args.label_type, args.sensor_view, args.no_classmerge)
    convert_calibs(source_root, target_root, split_map, frame_info, args.sensor_view)
    gen_imagesets(target_root, split_info, args.sensor_view)
    print(f"Conversion finished: {target_root}")


if __name__ == "__main__":
    main()
