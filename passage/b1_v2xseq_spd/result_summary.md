# V2X-Seq-SPD B1 一期结果摘要

## 已完成

- `V2X-Seq-SPD` 已解压到 `D:\Dproject_coop3d\DATA\raw\V2X-Seq-SPD`
- `DAIR-V2X\data\V2X-Seq-SPD` 已挂接到原始数据目录
- 官方 split 已复制到 `D:\Dproject_coop3d\DATA\processed\manifests\cooperative-split-data-spd.json`
- 完整性报告已生成到 `D:\Dproject_coop3d\DATA\reports\v2x_seq_spd_integrity_report.json`
- 标定/同步 sanity 报告已生成到 `D:\Dproject_coop3d\DATA\reports\v2x_seq_spd_sanity_report.json`
- 已导出 `20` 组相机 + BEV 抽检图到 `D:\Dproject_coop3d\DATA\reports\v2x_seq_spd_visual_checks`
- `vehicle-side` detection KITTI 转换已完成
- `infrastructure-side` detection KITTI 转换已完成

## 完整性统计

- vehicle `data_info.json`：`12252`
- infrastructure `data_info.json`：`11275`
- cooperative `data_info.json`：`10761`
- vehicle image：`12252`
- vehicle velodyne：`12252`
- infrastructure image：`11275`
- infrastructure velodyne：`11275`
- cooperative label：`10761`
- 缺失检查：`0`

## KITTI 转换结果

### Vehicle-side

- 路径：`D:\Dproject_coop3d\DATA\processed\V2X-Seq-SPD-KITTI\vehicle-side`
- `training/image_2`：`12252`
- `training/velodyne`：`12252`
- `training/label_2`：`12252`
- `training/calib`：`12252`
- `ImageSets`：`train.txt / val.txt / trainval.txt / test.txt`

### Infrastructure-side

- 路径：`D:\Dproject_coop3d\DATA\processed\V2X-Seq-SPD-KITTI\infrastructure-side`
- `training/image_2`：`11275`
- `training/velodyne`：`11275`
- `training/label_2`：`11275`
- `training/calib`：`11275`
- `ImageSets`：`train.txt / val.txt / trainval.txt / test.txt`

## Sanity 检查

- cooperative pair 数：`10761`
- vehicle vs infrastructure 点云时间差：
  - `p50 = 24.798 ms`
  - `p90 = 44.158 ms`
  - `max = 82.934 ms`
- vehicle vs infrastructure 图像时间差：
  - `p50 = 98.192 ms`
  - `p90 = 145.361 ms`
- 旋转矩阵行列式：
  - `mean = 1.0000000436`
- 正交性最大误差：
  - `mean = 8.819e-07`
- cooperative 与 vehicle token 对齐残差：
  - `p50 ~= 1e-7 m`
- infrastructure 变换到 vehicle 后与 cooperative 对齐残差：
  - `p50 = 0.951 m`
  - `p90 = 2.346 m`

## Smoke Check

- 报告路径：`D:\Dproject_coop3d\DATA\reports\v2x_seq_spd_smoke_check.json`
- `dair-v2x-v-spd`：
  - `length = 8504`
  - 样本类型：`VehFrameSPD`
  - 样本标签数：`15`
- `dair-v2x-i-spd`：
  - `length = 7834`
  - 样本类型：`InfFrameSPD`
  - 样本标签数：`17`
- `vic-sync-spd`：
  - `length = 7445`
  - 样本类型：`VICFrameSPD`
  - 样本标签数：`19`

## 新增脚本

- `passage/b1_v2xseq_spd/generate_integrity_report.py`
- `passage/b1_v2xseq_spd/generate_sanity_and_visual_checks.py`
- `passage/b1_v2xseq_spd/convert_detection_to_kitti_win.py`
- `passage/b1_v2xseq_spd/smoke_check_spd_dataset.py`
- `passage/b1_v2xseq_spd/README_stage1.md`

## 当前未覆盖

- cooperative tracking 转换
- 单端/协同模型训练与评估
- README 中的完整训练推理命令矩阵
