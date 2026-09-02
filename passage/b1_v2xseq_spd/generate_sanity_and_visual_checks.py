#!/usr/bin/env python3
import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def to_np_rotation(rotation):
    return np.array(rotation, dtype=np.float64).reshape(3, 3)


def to_np_translation(translation):
    return np.array(translation, dtype=np.float64).reshape(3, 1)


def compose(rt_a, rt_b):
    r1, t1 = rt_a
    r2, t2 = rt_b
    return r2 @ r1, r2 @ t1 + t2


def inverse(rt):
    r, t = rt
    r_inv = np.linalg.inv(r)
    t_inv = -r_inv @ t
    return r_inv, t_inv


def transform_point(point, rt):
    r, t = rt
    p = np.array(point, dtype=np.float64).reshape(3, 1)
    return (r @ p + t).reshape(3)


def box_corners_xy(label):
    dims = label["3d_dimensions"]
    location = label["3d_location"]
    l = float(dims["l"])
    w = float(dims["w"])
    x = float(location["x"])
    y = float(location["y"])
    yaw = float(label["rotation"])
    corners = np.array(
        [
            [l / 2, w / 2],
            [l / 2, -w / 2],
            [-l / 2, -w / 2],
            [-l / 2, w / 2],
            [l / 2, w / 2],
        ],
        dtype=np.float64,
    )
    rot = np.array(
        [
            [math.cos(yaw), -math.sin(yaw)],
            [math.sin(yaw), math.cos(yaw)],
        ],
        dtype=np.float64,
    )
    return corners @ rot.T + np.array([x, y], dtype=np.float64)


def transform_label_to_vehicle(label, rt):
    center = [
        float(label["3d_location"]["x"]),
        float(label["3d_location"]["y"]),
        float(label["3d_location"]["z"]),
    ]
    new_center = transform_point(center, rt)
    label_copy = json.loads(json.dumps(label))
    label_copy["3d_location"]["x"] = float(new_center[0])
    label_copy["3d_location"]["y"] = float(new_center[1])
    label_copy["3d_location"]["z"] = float(new_center[2])

    # Use transformed forward vector to refresh yaw in vehicle frame.
    yaw = float(label["rotation"])
    forward = np.array([math.cos(yaw), math.sin(yaw), 0.0], dtype=np.float64)
    new_forward = rt[0] @ forward.reshape(3, 1)
    label_copy["rotation"] = float(math.atan2(new_forward[1, 0], new_forward[0, 0]))
    return label_copy


def draw_boxes(image_path: Path, labels):
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    palette = {
        "Car": (0, 255, 0),
        "Truck": (255, 165, 0),
        "Bus": (255, 0, 0),
        "Van": (0, 200, 255),
    }
    for label in labels:
        box = label["2d_box"]
        color = palette.get(label["type"], (255, 255, 0))
        draw.rectangle(
            [box["xmin"], box["ymin"], box["xmax"], box["ymax"]],
            outline=color,
            width=2,
        )
    return np.asarray(image)


def select_evenly(items, count):
    if len(items) <= count:
        return items
    indices = np.linspace(0, len(items) - 1, count, dtype=int)
    return [items[i] for i in indices]


@dataclass
class PairContext:
    vehicle_frame: dict
    infrastructure_frame: dict
    pair_info: dict
    infra_to_vehicle: tuple


def build_contexts(root: Path):
    vehicle_infos = read_json(root / "vehicle-side" / "data_info.json")
    infra_infos = read_json(root / "infrastructure-side" / "data_info.json")
    coop_infos = read_json(root / "cooperative" / "data_info.json")
    vehicle_map = {item["frame_id"]: item for item in vehicle_infos}
    infra_map = {item["frame_id"]: item for item in infra_infos}

    contexts = []
    for pair in coop_infos:
        veh_frame = vehicle_map[pair["vehicle_frame"]]
        inf_frame = infra_map[pair["infrastructure_frame"]]
        infra_l2w = read_json(root / "infrastructure-side" / inf_frame["calib_virtuallidar_to_world_path"])
        veh_l2n = read_json(root / "vehicle-side" / veh_frame["calib_lidar_to_novatel_path"])
        veh_n2w = read_json(root / "vehicle-side" / veh_frame["calib_novatel_to_world_path"])

        rt_infra_world = (
            to_np_rotation(infra_l2w["rotation"]),
            to_np_translation(infra_l2w["translation"]) + np.array(
                [
                    [float(pair["system_error_offset"]["delta_x"])],
                    [float(pair["system_error_offset"]["delta_y"])],
                    [0.0],
                ]
            ),
        )
        rt_veh_nov = (
            to_np_rotation(veh_l2n["transform"]["rotation"]),
            to_np_translation(veh_l2n["transform"]["translation"]),
        )
        rt_nov_world = (
            to_np_rotation(veh_n2w["rotation"]),
            to_np_translation(veh_n2w["translation"]),
        )
        rt_veh_world = compose(rt_veh_nov, rt_nov_world)
        rt_world_veh = inverse(rt_veh_world)
        rt_infra_veh = compose(rt_infra_world, rt_world_veh)

        contexts.append(PairContext(veh_frame, inf_frame, pair, rt_infra_veh))
    return contexts


def compute_report(root: Path, contexts, label_sample_count: int):
    pointcloud_deltas_ms = []
    image_deltas_ms = []
    vehicle_sensor_skew_ms = []
    infra_sensor_skew_ms = []
    transform_det = []
    transform_orth_err = []
    label_residuals_vehicle = []
    label_residuals_infra = []

    sample_contexts = select_evenly(contexts, label_sample_count)
    for ctx in contexts:
        pointcloud_deltas_ms.append(
            abs(int(ctx.vehicle_frame["pointcloud_timestamp"]) - int(ctx.infrastructure_frame["pointcloud_timestamp"])) / 1000.0
        )
        image_deltas_ms.append(
            abs(int(ctx.vehicle_frame["image_timestamp"]) - int(ctx.infrastructure_frame["image_timestamp"])) / 1000.0
        )
        vehicle_sensor_skew_ms.append(
            abs(int(ctx.vehicle_frame["image_timestamp"]) - int(ctx.vehicle_frame["pointcloud_timestamp"])) / 1000.0
        )
        infra_sensor_skew_ms.append(
            abs(int(ctx.infrastructure_frame["image_timestamp"]) - int(ctx.infrastructure_frame["pointcloud_timestamp"])) / 1000.0
        )
        r = ctx.infra_to_vehicle[0]
        transform_det.append(float(np.linalg.det(r)))
        transform_orth_err.append(float(np.max(np.abs(r.T @ r - np.eye(3)))))

    for ctx in sample_contexts:
        vehicle_labels = read_json(root / "vehicle-side" / "label" / "lidar" / f'{ctx.vehicle_frame["frame_id"]}.json')
        infra_labels = read_json(root / "infrastructure-side" / "label" / "virtuallidar" / f'{ctx.infrastructure_frame["frame_id"]}.json')
        coop_labels = read_json(root / "cooperative" / "label" / f'{ctx.vehicle_frame["frame_id"]}.json')

        vehicle_by_token = {item["token"]: item for item in vehicle_labels}
        infra_by_token = {item["token"]: item for item in infra_labels}

        for label in coop_labels:
            center = np.array(
                [
                    float(label["3d_location"]["x"]),
                    float(label["3d_location"]["y"]),
                    float(label["3d_location"]["z"]),
                ],
                dtype=np.float64,
            )
            if label.get("veh_token") not in {"-1", None} and label["veh_token"] in vehicle_by_token:
                ref = vehicle_by_token[label["veh_token"]]
                ref_center = np.array(
                    [
                        float(ref["3d_location"]["x"]),
                        float(ref["3d_location"]["y"]),
                        float(ref["3d_location"]["z"]),
                    ],
                    dtype=np.float64,
                )
                label_residuals_vehicle.append(float(np.linalg.norm(center - ref_center)))
            if label.get("inf_token") not in {"-1", None} and label["inf_token"] in infra_by_token:
                ref = infra_by_token[label["inf_token"]]
                ref_center = np.array(
                    transform_point(
                        [
                            float(ref["3d_location"]["x"]),
                            float(ref["3d_location"]["y"]),
                            float(ref["3d_location"]["z"]),
                        ],
                        ctx.infra_to_vehicle,
                    ),
                    dtype=np.float64,
                )
                label_residuals_infra.append(float(np.linalg.norm(center - ref_center)))

    def summarize(values):
        values = np.array(values, dtype=np.float64)
        return {
            "count": int(values.size),
            "min": float(values.min()) if values.size else None,
            "p50": float(np.median(values)) if values.size else None,
            "p90": float(np.percentile(values, 90)) if values.size else None,
            "max": float(values.max()) if values.size else None,
            "mean": float(values.mean()) if values.size else None,
        }

    return {
        "dataset_root": str(root),
        "pair_count": len(contexts),
        "label_alignment_sample_pair_count": len(sample_contexts),
        "timestamp_ms": {
            "vehicle_vs_infrastructure_pointcloud": summarize(pointcloud_deltas_ms),
            "vehicle_vs_infrastructure_image": summarize(image_deltas_ms),
            "vehicle_image_vs_pointcloud": summarize(vehicle_sensor_skew_ms),
            "infrastructure_image_vs_pointcloud": summarize(infra_sensor_skew_ms),
        },
        "transformation_checks": {
            "infra_to_vehicle_rotation_det": summarize(transform_det),
            "infra_to_vehicle_orthogonality_max_abs_error": summarize(transform_orth_err),
        },
        "label_alignment_m": {
            "vehicle_token_to_cooperative": summarize(label_residuals_vehicle),
            "infrastructure_token_to_cooperative_after_transform": summarize(label_residuals_infra),
        },
    }


def render_visuals(root: Path, contexts, output_dir: Path, count: int):
    ensure_dir(output_dir)
    sampled = select_evenly(contexts, count)
    saved_files = []
    for index, ctx in enumerate(sampled):
        veh_frame_id = ctx.vehicle_frame["frame_id"]
        inf_frame_id = ctx.infrastructure_frame["frame_id"]
        vehicle_cam = read_json(root / "vehicle-side" / "label" / "camera" / f"{veh_frame_id}.json")
        infra_cam = read_json(root / "infrastructure-side" / "label" / "camera" / f"{inf_frame_id}.json")
        vehicle_lidar = read_json(root / "vehicle-side" / "label" / "lidar" / f"{veh_frame_id}.json")
        infra_lidar = read_json(root / "infrastructure-side" / "label" / "virtuallidar" / f"{inf_frame_id}.json")
        coop_lidar = read_json(root / "cooperative" / "label" / f"{veh_frame_id}.json")

        veh_img = draw_boxes(root / "vehicle-side" / "image" / f"{veh_frame_id}.jpg", vehicle_cam)
        inf_img = draw_boxes(root / "infrastructure-side" / "image" / f"{inf_frame_id}.jpg", infra_cam)
        infra_lidar_vehicle = [transform_label_to_vehicle(label, ctx.infra_to_vehicle) for label in infra_lidar]

        fig, axes = plt.subplots(1, 3, figsize=(18, 6), dpi=150)
        axes[0].imshow(veh_img)
        axes[0].set_title(f"Vehicle camera {veh_frame_id}")
        axes[0].axis("off")

        axes[1].imshow(inf_img)
        axes[1].set_title(f"Infrastructure camera {inf_frame_id}")
        axes[1].axis("off")

        ax = axes[2]
        for label in vehicle_lidar:
            xy = box_corners_xy(label)
            ax.plot(xy[:, 0], xy[:, 1], color="#1f77b4", linewidth=1.5, alpha=0.9)
        for label in infra_lidar_vehicle:
            xy = box_corners_xy(label)
            ax.plot(xy[:, 0], xy[:, 1], color="#ff7f0e", linewidth=1.2, alpha=0.75)
        for label in coop_lidar:
            xy = box_corners_xy(label)
            ax.plot(xy[:, 0], xy[:, 1], color="#2ca02c", linewidth=1.2, alpha=0.8)
        ax.set_title(
            "BEV labels in vehicle frame\n"
            f"dt_pc={abs(int(ctx.vehicle_frame['pointcloud_timestamp']) - int(ctx.infrastructure_frame['pointcloud_timestamp'])) / 1000.0:.2f}ms"
        )
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
        ax.grid(True, alpha=0.25)
        ax.axis("equal")
        ax.legend(
            ["vehicle lidar", "infra->vehicle", "cooperative"],
            loc="upper right",
            fontsize=8,
        )

        fig.suptitle(
            f"Sample {index:02d} | veh={veh_frame_id} inf={inf_frame_id} "
            f"| veh_seq={ctx.pair_info['vehicle_sequence']} inf_seq={ctx.pair_info['infrastructure_sequence']}",
            fontsize=12,
        )
        fig.tight_layout()
        output_file = output_dir / f"sample_{index:02d}_veh_{veh_frame_id}_inf_{inf_frame_id}.png"
        fig.savefig(output_file)
        plt.close(fig)
        saved_files.append(str(output_file))
    return saved_files


def main():
    parser = argparse.ArgumentParser(description="Generate SPD calibration/time sanity report and visual spot checks.")
    parser.add_argument(
        "--dataset-root",
        default=r"D:\Dproject_coop3d\DATA\raw\V2X-Seq-SPD",
        help="Raw SPD dataset root.",
    )
    parser.add_argument(
        "--report-path",
        default=r"D:\Dproject_coop3d\DATA\reports\v2x_seq_spd_sanity_report.json",
        help="Sanity report output path.",
    )
    parser.add_argument(
        "--visual-dir",
        default=r"D:\Dproject_coop3d\DATA\reports\v2x_seq_spd_visual_checks",
        help="Directory for saved visual spot checks.",
    )
    parser.add_argument("--visual-count", type=int, default=20, help="Number of visual samples to export.")
    parser.add_argument("--label-sample-count", type=int, default=200, help="Number of cooperative pairs for label-alignment sampling.")
    args = parser.parse_args()

    root = Path(args.dataset_root)
    report_path = Path(args.report_path)
    visual_dir = Path(args.visual_dir)
    ensure_dir(report_path.parent)
    ensure_dir(visual_dir)

    contexts = build_contexts(root)
    report = compute_report(root, contexts, args.label_sample_count)
    report["visual_samples"] = render_visuals(root, contexts, visual_dir, args.visual_count)

    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Sanity report written to: {report_path}")
    print(f"Visual samples directory: {visual_dir}")
    print(json.dumps(report["timestamp_ms"], ensure_ascii=False, indent=2))
    print(json.dumps(report["label_alignment_m"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
