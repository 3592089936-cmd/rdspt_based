#!/usr/bin/env python3
import argparse
import json
from collections import Counter
from pathlib import Path


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def count_files(path: Path, pattern: str) -> int:
    return sum(1 for _ in path.glob(pattern)) if path.exists() else 0


def check_entries(base_dir: Path, entries, keys):
    missing = []
    for entry in entries:
        frame_id = entry.get("frame_id", "unknown")
        for key in keys:
            rel = entry.get(key)
            if not rel:
                missing.append({"frame_id": frame_id, "key": key, "path": None})
                continue
            full = base_dir / rel
            if not full.exists():
                missing.append({"frame_id": frame_id, "key": key, "path": str(full)})
    return missing


def summarize_sequences(entries, key: str):
    counter = Counter(item[key] for item in entries if key in item)
    return {
        "sequence_count": len(counter),
        "top5": dict(counter.most_common(5)),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate V2X-Seq-SPD integrity report for B1 stage.")
    parser.add_argument(
        "--dataset-root",
        default=r"D:\Dproject_coop3d\DATA\raw\V2X-Seq-SPD",
        help="Raw V2X-Seq-SPD dataset root.",
    )
    parser.add_argument(
        "--output",
        default=r"D:\Dproject_coop3d\DATA\reports\v2x_seq_spd_integrity_report.json",
        help="Integrity report output path.",
    )
    args = parser.parse_args()

    root = Path(args.dataset_root)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    vehicle_dir = root / "vehicle-side"
    infra_dir = root / "infrastructure-side"
    coop_dir = root / "cooperative"

    vehicle_info = read_json(vehicle_dir / "data_info.json")
    infra_info = read_json(infra_dir / "data_info.json")
    coop_info = read_json(coop_dir / "data_info.json")

    vehicle_missing = check_entries(
        vehicle_dir,
        vehicle_info,
        [
            "image_path",
            "pointcloud_path",
            "calib_camera_intrinsic_path",
            "calib_lidar_to_camera_path",
            "calib_lidar_to_novatel_path",
            "calib_novatel_to_world_path",
            "label_camera_std_path",
            "label_lidar_std_path",
        ],
    )
    infra_missing = check_entries(
        infra_dir,
        infra_info,
        [
            "image_path",
            "pointcloud_path",
            "calib_camera_intrinsic_path",
            "calib_virtuallidar_to_camera_path",
            "calib_virtuallidar_to_world_path",
            "label_camera_std_path",
            "label_lidar_std_path",
        ],
    )

    coop_label_missing = []
    vehicle_frames = {item["frame_id"] for item in vehicle_info}
    infra_frames = {item["frame_id"] for item in infra_info}
    for item in coop_info:
        vehicle_frame = item["vehicle_frame"]
        infrastructure_frame = item["infrastructure_frame"]
        label_path = coop_dir / "label" / f"{vehicle_frame}.json"
        if not label_path.exists():
            coop_label_missing.append({"vehicle_frame": vehicle_frame, "path": str(label_path)})
        if vehicle_frame not in vehicle_frames:
            coop_label_missing.append({"vehicle_frame": vehicle_frame, "missing_ref": "vehicle-side"})
        if infrastructure_frame not in infra_frames:
            coop_label_missing.append({"infrastructure_frame": infrastructure_frame, "missing_ref": "infrastructure-side"})

    report = {
        "dataset_root": str(root),
        "summary": {
            "vehicle_data_info_entries": len(vehicle_info),
            "infrastructure_data_info_entries": len(infra_info),
            "cooperative_data_info_entries": len(coop_info),
            "vehicle_image_files": count_files(vehicle_dir / "image", "*.jpg"),
            "vehicle_velodyne_files": count_files(vehicle_dir / "velodyne", "*.pcd"),
            "infrastructure_image_files": count_files(infra_dir / "image", "*.jpg"),
            "infrastructure_velodyne_files": count_files(infra_dir / "velodyne", "*.pcd"),
            "cooperative_label_files": count_files(coop_dir / "label", "*.json"),
            "vehicle_camera_label_files": count_files(vehicle_dir / "label" / "camera", "*.json"),
            "vehicle_lidar_label_files": count_files(vehicle_dir / "label" / "lidar", "*.json"),
            "infrastructure_camera_label_files": count_files(infra_dir / "label" / "camera", "*.json"),
            "infrastructure_lidar_label_files": count_files(infra_dir / "label" / "virtuallidar", "*.json"),
        },
        "sequence_summary": {
            "vehicle": summarize_sequences(vehicle_info, "sequence_id"),
            "infrastructure": summarize_sequences(infra_info, "sequence_id"),
            "cooperative_vehicle": summarize_sequences(coop_info, "vehicle_sequence"),
            "cooperative_infrastructure": summarize_sequences(coop_info, "infrastructure_sequence"),
        },
        "missing": {
            "vehicle_missing_count": len(vehicle_missing),
            "infrastructure_missing_count": len(infra_missing),
            "cooperative_missing_count": len(coop_label_missing),
            "vehicle_examples": vehicle_missing[:20],
            "infrastructure_examples": infra_missing[:20],
            "cooperative_examples": coop_label_missing[:20],
        },
        "status": "ok" if not vehicle_missing and not infra_missing and not coop_label_missing else "has_missing",
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Integrity report written to: {output_path}")
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    print(json.dumps(report["missing"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
