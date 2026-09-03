# 方案 B1 Spec: 基于 V2X-Seq-SPD Only 的一期车路协同感知系统

## 1. 文档目的

本 spec 定义项目一期的收敛实现路线：

- 真实主数据集：`V2X-Seq-SPD`
- 一期不依赖：`OPV2V`
- 代码基线：当前工作区中的 `DAIR-V2X` 仓库能力

本 spec 用于在硬盘空间、下载带宽和数据完整性受限的情况下，先完成一期的真实车路协同主链路，不把主进度绑定在额外仿真数据集上。

## 2. 与方案 B 的关系

- 保留原 spec：`specs/scheme_b_v2xseq_opv2v_spec.md`
- 本文档是方案 B 的一期收敛版
- 核心变化只有一条：`OPV2V` 不进入一期必需范围

换句话说：

- `方案 B` 是完整路线
- `方案 B1` 是当前资源条件下的可执行一期路线

## 3. 一期目标

一期只围绕 `V2X-Seq-SPD` 完成以下闭环：

1. 数据下载、解压、索引和完整性校验
2. 时间同步、标定读取、坐标转换和闭环检查
3. 单端基线可运行
4. 协同基线可运行
5. 可视化回放、评估和日志导出可运行

一期不要求：

- `OPV2V` 仿真数据接入
- 通信延迟/丢包/带宽限制的完整实验矩阵
- 大规模故障注入系统

## 4. 采用 B1 的原因

### 4.1 当前资源约束

- 当前硬盘空间不足以舒适容纳完整 `OPV2V`
- `OPV2V` 官方下载按 `train / validate / test` 大包或分卷组织，部分下载价值有限
- 当前阶段更需要先把真实数据主链路跑通

### 4.2 题目匹配度

`V2X-Seq-SPD` 已经满足一期题目的关键要求：

- 真实车路协同
- 时序数据
- 车端与路侧多模态输入
- cooperative 标注
- 坐标转换与同步链路

因此即使暂时不用 `OPV2V`，一期主目标仍然成立。

## 5. 数据集角色定义

### 5.1 一期主数据集

`V2X-Seq-SPD` 是一期唯一主数据集，负责：

- 单端 3D 感知
- 协同 3D 感知
- 时序样本读取
- 遮挡补盲分析
- 回放与可视化

### 5.2 非一期必需数据集

`OPV2V` 在 B1 中标记为“后续增强”，不进入一期验收门槛。

### 5.3 补充数据

当前 `DAIR-V2X-C` 可保留为：

- 静态帧回归检查
- 坐标转换 sanity check
- 数据处理兼容性验证

但不作为一期主实验依据。

## 6. 仓库与落地点

### 6.1 可直接复用的现有入口

当前工作区内已存在以下与 `SPD` 直接相关的能力：

- `DAIR-V2X/docs/get_started_spd.md`
- `DAIR-V2X/docs/apis/dataloaders_spd.md`
- `DAIR-V2X/configs/vic3d-spd/late-fusion-image/README.md`
- `DAIR-V2X/tools/dataset_converter/spd2kitti_detection/dair2kitti.py`
- `DAIR-V2X/tools/dataset_converter/spd2kitti_tracking/coop_label_dair2kitti.py`
- `DAIR-V2X/v2x/dataset/__init__.py`
- `DAIR-V2X/v2x/v2x_utils/transformation_utils.py`

这意味着一期不需要另起炉灶，可以直接建立在现有 `SPD` 支持能力上。

### 6.2 建议目录

```text
D:\Dproject_coop3d/
├─ DAIR-V2X/
├─ DATA/
│  ├─ source/
│  ├─ raw/
│  │  └─ V2X-Seq-SPD/
│  ├─ processed/
│  │  ├─ V2X-Seq-SPD-KITTI/
│  │  └─ manifests/
│  └─ reports/
├─ specs/
└─ passage/
```

## 7. 数据组织要求

`V2X-Seq-SPD` 一期必须组织为：

```text
V2X-Seq-SPD/
├─ infrastructure-side/
│  ├─ image/
│  ├─ velodyne/
│  ├─ calib/
│  ├─ label/
│  └─ data_info.json
├─ vehicle-side/
│  ├─ image/
│  ├─ velodyne/
│  ├─ calib/
│  ├─ label/
│  └─ data_info.json
├─ cooperative/
│  ├─ label/
│  └─ data_info.json
└─ maps/
```

必须校验：

- 车端 `lidar_to_camera / lidar_to_novatel / novatel_to_world`
- 路侧 `virtuallidar_to_camera / virtuallidar_to_world`
- cooperative 配对关系
- 时间戳与序列字段

## 8. 一期数据处理要求

### 8.1 完整性检查

每次数据准备后必须输出：

- 文件数量统计
- 模态存在性统计
- 缺失文件清单
- 目录摘要
- 样本抽检记录

建议输出：

- `DATA/reports/v2x_seq_spd_integrity_report.json`

### 8.2 split 策略

一期优先使用官方 `cooperative-split-data-spd.json`。

要求：

- 按序列/场景划分
- 禁止相邻帧跨集合泄漏
- split 文件版本化保存

### 8.3 转换产物

一期至少需要生成：

1. 原始索引 manifest
2. `spd2kitti_detection` 转换结果
3. 可选的 tracking 转换结果
4. 投影图与 BEV 抽检图

## 9. 一期功能范围

### 9.1 P0 必做

- `V2X-Seq-SPD` 数据可读取
- 单端样本可视化
- 协同样本同步读取
- 车端与路侧坐标统一到自车参考系
- 至少一种协同模式可运行
- 评估脚本可输出结果
- README 可复现

### 9.2 P1 建议完成

- 后融合稳定跑通
- 中间融合至少保留配置与入口
- 遮挡收益分析
- 不少于 `20` 组样例可视化

### 9.3 明确延期到后续

- `OPV2V` 故障注入实验
- 延迟/丢包/带宽限制曲线
- 复杂通信降级策略矩阵

## 10. 训练与评估路线

### Phase 1: 数据与标定

目标：

- 下载并解压 `V2X-Seq-SPD`
- 建立数据路径
- 跑通格式转换
- 检查标定与坐标链

验收：

- 数据可读
- 配对明确
- 坐标闭环无系统性偏移

### Phase 2: 单端基线

目标：

- vehicle-only baseline 可运行
- infrastructure-only baseline 可运行

说明：

- 设计上仍以 `LiDAR` 主导
- 但当前工作区已优先验证 `camera-only` 车端单端链路，可作为一期“先跑通评估闭环”的可执行基线

### Phase 3: 协同基线

目标：

- 至少跑通一种协同方式

优先顺序：

1. `late fusion`
2. `intermediate fusion`
3. `early fusion`

理由：

- 后融合最适合先验证坐标、同步和去重
- 中间融合作为后续增强方向

### Phase 4: 回放与导出

目标：

- 输出统一 BEV 结果
- 生成日志和评估结果
- 支持样例回放与截图导出

## 11. 配置原则

以下内容必须配置化：

- 数据根目录
- split 文件路径
- 训练/评估范围
- 融合模式
- 体素尺寸
- 点云范围
- 节点配置
- 输出路径
- 随机种子

禁止：

- 模型代码中硬编码路径
- 静默修正异常数据
- 用手工改数据替代脚本化处理

### 11.1 当前锁定运行环境

为避免新版 `mmcv/mmengine` 与上游 `DAIR-V2X` 在 `SPD` 路径上的兼容性问题，一期评估链路当前锁定为官方旧栈：

- Python 环境：`D:\anaconda\envs\dair38old\python.exe`
- `torch 1.10.1+cu113`
- `mmcv 1.4.0`
- `mmdet 2.14.0`
- `mmseg 0.14.1`
- `mmdet3d 0.17.1`

说明：

- 新版 `mmcv 2.x` 在当前 Windows 环境下会卡在 `dataset_utils/file_io.py` 导入链路，一期不再继续兼容新版栈
- 若后续恢复到新栈，应作为独立增强任务处理，不能反向破坏当前旧栈可运行基线

## 12. 一期交付物

必须提交：

1. `V2X-Seq-SPD` 数据说明
2. 数据处理 README
3. split 文件与版本说明
4. 标定与投影检查结果
5. 单端与协同基线配置
6. 评估结果
7. 可视化样例
8. 已知限制说明

### 12.1 当前已落地交付物

截至 `2026-09-03`，以下交付物已经在工作区内形成：

1. 数据准备与完整性报告
2. `SPD` detection / tracking 转换脚本
3. 标定与同步 sanity report
4. `20` 组相机 + BEV 抽检图
5. B1 一期 README 与结果摘要
6. 单端 `camera-only` smoke + 全量 `val` 评估证据
7. cooperative `late fusion camera-only` smoke 证据
8. cooperative `late fusion camera-only` 全量 `val` 在跑证据

关键文件与目录：

- `passage/b1_v2xseq_spd/README_stage1.md`
- `passage/b1_v2xseq_spd/result_summary.md`
- `passage/b1_v2xseq_spd/run_single_side_camera_smoke.py`
- `passage/b1_v2xseq_spd/run_late_fusion_camera_smoke.py`
- `DAIR-V2X/output/spd_single_camera_veh_val_oldstack/`
- `DAIR-V2X/output/spd_late_fusion_camera_val_oldstack/`

## 13. 一期验收口径

B1 完成的判断标准是：

- 不依赖 `OPV2V`
- 仅用 `V2X-Seq-SPD` 即可从数据准备走到推理评估
- 非原开发者可按 README 跑通样例
- 单端和协同模式都能输出统一坐标系结果

不要求：

- 完整通信鲁棒性实验
- 多数据集联合对比
- 仿真故障注入闭环

### 13.1 当前验收映射

以下映射基于当前工作区的真实运行状态，而不是预期状态：

| 验收项 | 当前状态 | 证据 |
| --- | --- | --- |
| 仅依赖 `V2X-Seq-SPD` 可完成数据准备 | 已完成 | `passage/b1_v2xseq_spd/result_summary.md`、`DATA/reports/` |
| 数据可读取、split 可用、格式转换可用 | 已完成 | 完整性报告、sanity 报告、KITTI 转换脚本与输出 |
| 单端基线可运行 | 已完成 | `run_single_side_camera_smoke.py` 已跑通 |
| 单端全量评估可输出结果 | 已完成 | `DAIR-V2X/output/spd_single_camera_veh_val_oldstack/result/` 共 `3748` 个结果文件 |
| 协同基线可运行 | 已完成 | `run_late_fusion_camera_smoke.py` 已跑通，单帧成功输出预测框 |
| 协同全量评估可输出结果 | 已完成 | `DAIR-V2X/output/spd_late_fusion_camera_val_oldstack/result/` 共 `3316` 个结果文件，日志已输出最终 AP |
| 非原开发者可按 README 复现样例 | 基本具备 | 已有 `README_stage1.md`，仍建议后续补一版统一命令矩阵 |
| 单端与协同统一坐标结果输出 | 已完成 | 单端与 cooperative 全量评估均已完成并落盘 |

### 13.2 已验证结果快照

单端 `vehicle-side camera-only val` 已完成：

- 输出目录：`DAIR-V2X/output/spd_single_camera_veh_val_oldstack/`
- 结果文件数：`3748 / 3748`
- `3d AP`：`car 0.30 = 17.39`，`0.50 = 4.13`，`0.70 = 0.09`
- `bev AP`：`car 0.30 = 20.24`，`0.50 = 8.72`，`0.70 = 0.71`

cooperative `late fusion camera-only` 已完成 smoke：

- 数据集 `val` 长度日志：`3316`
- 已成功构建 `veh` / `inf` 双模型
- 已成功取到首帧配对：`veh=000870`，`inf=000902`
- 已成功生成预测框：`pred_boxes=2`

cooperative `late fusion camera-only val` 已完成：

- 后台任务：`job-89977ab10b304fffa92b8a8377ac6e7f`
- 输出目录：`DAIR-V2X/output/spd_late_fusion_camera_val_oldstack/`
- 结果文件数：`3316 / 3316`
- `3d AP`：`car 0.30 = 33.43`，`0.50 = 17.97`，`0.70 = 4.51`
- `bev AP`：`car 0.30 = 36.64`，`0.50 = 23.10`，`0.70 = 8.93`
- 平均通信开销：`301.09 Bytes`

## 14. 风险与应对

### 风险 1: SPD 下载量仍较大

应对：

- 先下 example 或优先子集验证链路
- 原始数据只读保存
- 转换产物按需生成

### 风险 2: 一期缺少仿真鲁棒性结果

应对：

- 在文档中明确列为二期任务
- 不将通信故障实验列入一期强制验收

### 风险 3: 图像分支训练压力较高

应对：

- 一期以 `LiDAR` 主导
- 图像接口保留但不过度扩展

### 风险 4: cooperative 全量评估耗时较长

应对：

- 先将 smoke 成功与单端全量结果纳入一期已验证范围
- cooperative 全量 `val` 完成后，只补充指标与结果文件统计，不再改动路线设计
- 若全量过程报错，优先做最小兼容补丁，禁止大改上游结构

## 15. 立即执行清单

当前按“已完成 / 进行中 / 待补”拆分如下：

已完成：

1. 准备 `V2X-Seq-SPD` 原始数据
2. 建立 `DAIR-V2X/data/V2X-Seq-SPD` 数据路径
3. 运行 `spd2kitti_detection` 与 cooperative tracking 转换
4. 生成完整性报告、sanity 报告与 split 清单
5. 完成 `20` 组投影 / BEV 抽检
6. 冻结旧栈一期运行环境与 smoke 脚本
7. 编写一期 README 与结果摘要
8. 跑通单端 `camera-only` smoke 与全量 `val`
9. 跑通 cooperative `late fusion camera-only` smoke

待补：

1. 将单端 / 协同复现命令整理成统一命令矩阵
2. 补充不少于 `20` 组协同可视化样例
3. 视需要增加 `infrastructure-only` 与 `LiDAR-only` 基线

## 16. 结论

`方案 B1` 是当前最符合现实资源约束的一期路线：

- 只依赖 `V2X-Seq-SPD`
- 不依赖 `OPV2V`
- 先完成真实车路协同主闭环

并且截至当前，B1 已经不只是“路线设计”，而是进入“有真实运行证据的可交付阶段”：

- 数据、转换、完整性和 sanity 检查已落地
- 单端基线已经完成全量 `val`
- cooperative 基线已经完成 smoke 与全量 `val`

因此本文档可作为一期阶段性交付基线使用；后续主要是补充复现命令矩阵和更多可视化样例，不需要再重写方案。

这样既保留题目匹配度，也避免在一期阶段把项目推进卡在额外仿真数据的下载和存储上。
