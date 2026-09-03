# RDSPT Based

这个仓库保存 `V2X-Seq-SPD` 一期落地所需的源码、文档和阶段成果，目标是把 `scheme_b1_v2xseq_spd_only_spec.md` 对应的 B1 路线沉淀成可复现资产。

## 仓库内容

- `specs/`
  - B1 方案说明与验收口径
- `passage/b1_v2xseq_spd/`
  - 数据完整性检查、sanity 检查、KITTI 转换、环境审计、smoke 脚本
  - 一期阶段 README 与结果摘要
- `DATA/reports/`
  - 完整性报告、sanity 报告、环境审计、smoke 检查、`20` 组可视化样例
- `DATA/processed/manifests/`
  - 官方 `SPD` split 清单副本

## 本次上传的成果

- `V2X-Seq-SPD` 完整性报告
- 标定与时序 sanity 报告
- 运行环境审计报告
- `20` 组相机 + BEV 抽检图
- 单端 `vehicle-side camera-only val` 结果摘要
- cooperative `late fusion camera-only val` 结果摘要
- B1 方案 spec 与阶段交付总结

## 当前关键结果

### 单端 vehicle-side camera-only val

- 结果文件数：`3748 / 3748`
- `3d AP`：`17.39 / 4.13 / 0.09`
- `bev AP`：`20.24 / 8.72 / 0.71`

### Cooperative late fusion camera-only val

- 结果文件数：`3316 / 3316`
- `3d AP`：`33.43 / 17.97 / 4.51`
- `bev AP`：`36.64 / 23.10 / 8.93`
- 平均通信开销：`301.09 Bytes`

## 未上传的大体量目录

以下目录保持本地，不进入 Git 仓库：

- `DATA/source/`
- `DATA/raw/`
- `DATA/processed/V2X-Seq-SPD-KITTI/`
- `DAIR-V2X/`
- `_legacy_wheels/`
- `_scratch/`
- `_tmp_pkgcheck/`

## 使用说明

当前默认数据根目录为：

- `D:\Dproject_coop3d\DATA\raw\V2X-Seq-SPD`

建议按下面顺序复现：

1. 单独克隆 `DAIR-V2X`
2. 将 `V2X-Seq-SPD` 挂到 `DAIR-V2X/data/V2X-Seq-SPD`
3. 运行 `passage/b1_v2xseq_spd/` 下的数据准备与检查脚本
4. 参考 `passage/b1_v2xseq_spd/README_stage1.md` 与 `result_summary.md` 查看阶段成果

## 参考文件

- `specs/scheme_b1_v2xseq_spd_only_spec.md`
- `passage/b1_v2xseq_spd/README_stage1.md`
- `passage/b1_v2xseq_spd/result_summary.md`
