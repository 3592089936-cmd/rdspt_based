# coop3d B1 workspace

这个仓库用于落地 `scheme_b1_v2xseq_spd_only_spec.md` 的一期执行内容。

当前提交范围只保留本次新增的可复现资产：

- `specs/` 里的方案说明
- `passage/b1_v2xseq_spd/` 里的数据准备与转换脚本
- 生成后的阶段文档与报告

本地大体量目录不会提交：

- `DATA/source/`
- `DATA/raw/`
- `DATA/processed/V2X-Seq-SPD-KITTI/`
- `DAIR-V2X/` 上游仓库工作副本

当前数据默认根目录：

- `D:\Dproject_coop3d\DATA\raw\V2X-Seq-SPD`

当前关键产物：

- 完整性报告：`DATA/reports/v2x_seq_spd_integrity_report.json`
- split 清单：`DATA/processed/manifests/cooperative-split-data-spd.json`
- Windows 检测转换脚本：`passage/b1_v2xseq_spd/convert_detection_to_kitti_win.py`
- 完整性检查脚本：`passage/b1_v2xseq_spd/generate_integrity_report.py`

建议先准备上游环境：

1. 单独克隆 `DAIR-V2X`
2. 将 `V2X-Seq-SPD` 挂到 `DAIR-V2X/data/V2X-Seq-SPD`
3. 运行本仓库中的 B1 脚本完成一期数据准备与格式转换
