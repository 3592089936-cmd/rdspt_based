# V2X-Seq-SPD B1 一期执行记录

本目录放的是方案 B1 的一期辅助脚本，尽量不修改上游 `DAIR-V2X`。

当前默认数据根目录：

- `D:\Dproject_coop3d\DATA\raw\V2X-Seq-SPD`

当前已落地内容：

- 原始元数据已解压到标准 `V2X-Seq-SPD/` 结构
- `vehicle-side` 图像与点云已补齐
- `infrastructure-side` 图像与点云已补齐
- 可生成完整性报告
- 可生成标定/同步 sanity report
- 可导出 20 组相机框 + BEV 抽检图
- 可在 Windows 下执行单侧 SPD detection -> KITTI 转换

常用命令：

```powershell
py -3.11 D:\Dproject_coop3d\passage\b1_v2xseq_spd\generate_integrity_report.py
```

```powershell
py -3.11 D:\Dproject_coop3d\passage\b1_v2xseq_spd\generate_sanity_and_visual_checks.py
```

```powershell
py -3.11 D:\Dproject_coop3d\passage\b1_v2xseq_spd\convert_detection_to_kitti_win.py `
  --source-root D:\Dproject_coop3d\DATA\raw\V2X-Seq-SPD\vehicle-side `
  --target-root D:\Dproject_coop3d\DATA\processed\V2X-Seq-SPD-KITTI\vehicle-side `
  --sensor-view vehicle `
  --label-type lidar
```

```powershell
py -3.11 D:\Dproject_coop3d\passage\b1_v2xseq_spd\convert_detection_to_kitti_win.py `
  --source-root D:\Dproject_coop3d\DATA\raw\V2X-Seq-SPD\infrastructure-side `
  --target-root D:\Dproject_coop3d\DATA\processed\V2X-Seq-SPD-KITTI\infrastructure-side `
  --sensor-view infrastructure `
  --label-type lidar
```

```powershell
py -3.11 D:\Dproject_coop3d\passage\b1_v2xseq_spd\smoke_check_spd_dataset.py
```

关键输出：

- `D:\Dproject_coop3d\DATA\reports\v2x_seq_spd_integrity_report.json`
- `D:\Dproject_coop3d\DATA\reports\v2x_seq_spd_sanity_report.json`
- `D:\Dproject_coop3d\DATA\reports\v2x_seq_spd_visual_checks\`
- `D:\Dproject_coop3d\DATA\reports\v2x_seq_spd_smoke_check.json`
