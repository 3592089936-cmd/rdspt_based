# 方案 B Spec: 基于 V2X-Seq-SPD + OPV2V 的车路协同多模态感知与通信融合系统

## 1. 文档目的

本 spec 用于定义项目一期的推荐实现路线：

- 真实主数据集：`V2X-Seq-SPD`
- 仿真与鲁棒性数据集：`OPV2V`
- 代码基线：当前工作区中的 `DAIR-V2X` 仓库能力

本方案用于替代“继续依赖当前不完整的 `DAIR-V2X-C` 图像模态”的主路线，但不否定现有 `DAIR-V2X-C` 数据可作为补充对照或后续回归集。

## 2. 决策背景

### 2.1 需求约束

根据 `passage/` 下三份文档，一期核心要求是：

- 车端 + 路侧的协同三维感知
- 以 `LiDAR` 为主，保留图像扩展接口
- 支持 `single / early / intermediate / late` 中至少可运行的协同模式
- 支持时间同步、坐标转换、标定校验、回放、评估与日志
- 支持通信异常注入：延迟、丢包、带宽限制、位姿误差

### 2.2 当前现实状态

- 当前 `DAIR-V2X-C` 已恢复出完整的：
  - `vehicle-side/image`
  - `vehicle-side/velodyne`
  - `infrastructure-side/velodyne`
- 但 `infrastructure-side/image` 仍缺 `1406` 张
- 这不影响 `LiDAR` 主导链路验证，但会限制“完整多模态图像融合”作为主实验路线

### 2.3 采用方案 B 的原因

- `V2X-Seq-SPD` 更贴近“复杂场景 + 时序协同 + 车路协同”题目
- 当前仓库已存在 `SPD` 相关数据读取、坐标转换、转换脚本和评估入口
- `OPV2V` 适合承接通信故障注入和鲁棒性实验，不依赖真实数据完整性

## 3. 方案总览

### 3.1 数据集角色分工

| 数据集 | 角色 | 一期用途 |
|---|---|---|
| `V2X-Seq-SPD` | 真实主数据集 | 单端检测、协同检测、时序协同、遮挡补盲、可视化回放 |
| `OPV2V` | 仿真与鲁棒性数据集 | 早/中/后融合基线、延迟/丢包/带宽/位姿误差注入 |
| `DAIR-V2X-C` | 补充对照集 | 静态帧回归、坐标链 sanity check、兼容性验证 |

### 3.2 一期目标

一期按 `P0` 范围交付：

1. 跑通 `V2X-Seq-SPD` 数据准备、索引、转换、读取和可视化
2. 跑通单端基线与至少一种协同基线
3. 建立统一的时间同步、坐标转换和闭环校验
4. 在 `OPV2V` 上跑通通信鲁棒性实验
5. 形成可复现 README、配置、日志、评估和失败案例

## 4. 代码与仓库落点

### 4.1 现有可复用入口

当前工作区已存在以下 `SPD` 相关能力：

- `DAIR-V2X/docs/get_started_spd.md`
- `DAIR-V2X/docs/apis/dataloaders_spd.md`
- `DAIR-V2X/configs/vic3d-spd/late-fusion-image/README.md`
- `DAIR-V2X/tools/dataset_converter/spd2kitti_detection/dair2kitti.py`
- `DAIR-V2X/tools/dataset_converter/spd2kitti_tracking/coop_label_dair2kitti.py`
- `DAIR-V2X/v2x/dataset/__init__.py`
- `DAIR-V2X/v2x/v2x_utils/transformation_utils.py`

这些文件说明：

- 仓库已经支持 `vic-sync-spd` 与 `vic-async-spd`
- 已具备 `SPD` 的数据类、坐标转换和评估脚本
- 已具备将 `V2X-Seq-SPD` 转为训练/评估格式的工具链

### 4.2 一期代码组织建议

项目根目录建议保持如下结构：

```text
D:\Dproject_coop3d/
├─ DAIR-V2X/                 # 当前主代码仓库
├─ DATA/
│  ├─ source/                # 原始下载包
│  ├─ raw/
│  │  ├─ V2X-Seq-SPD/
│  │  └─ OPV2V/
│  ├─ processed/
│  │  ├─ V2X-Seq-SPD-KITTI/
│  │  ├─ opv2v_cache/
│  │  └─ manifests/
│  └─ reports/
├─ specs/
└─ passage/
```

说明：

- `raw/` 只读，保留原始解压结果
- `processed/` 存放 `KITTI` 转换、索引、split 和缓存
- `reports/` 存放完整性报告、字段校验、预览图和实验记录

## 5. 数据方案

### 5.1 V2X-Seq-SPD 数据组织标准

真实主数据集目录应满足：

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

其中必须重点校验：

- 车端 `lidar_to_camera / lidar_to_novatel / novatel_to_world`
- 路侧 `virtuallidar_to_camera / virtuallidar_to_world`
- cooperative 对应关系、时间戳、`frame_id`、`sequence_id`

### 5.2 OPV2V 数据角色

`OPV2V` 不作为真实精度主结果来源，而作为：

- 融合模式调试集
- 通信故障注入实验集
- 系统接口、日志和降级策略验证集

### 5.3 DAIR-V2X-C 的位置

`DAIR-V2X-C` 在方案 B 中不作为主数据集，但保留两类用途：

- 静态帧协同感知回归验证
- 坐标转换和数据处理脚本的兼容性检查

## 6. 数据处理规范

### 6.1 原始数据完整性检查

每次数据入库后必须生成：

- 文件数量统计
- 目录树摘要
- `SHA256` 或至少文件大小记录
- 缺失样本清单
- 解压日志

输出位置建议：

- `DATA/reports/v2x_seq_spd_integrity_report.json`
- `DATA/reports/opv2v_integrity_report.json`

### 6.2 统一 split 原则

必须遵守：

- 按场景或连续序列划分，避免相邻帧泄漏
- 真实数据与仿真数据不混测
- 训练/验证/测试配置写入版本化文件

建议采用：

- `V2X-Seq-SPD`：优先使用官方 `cooperative-split-data-spd.json`
- `OPV2V`：使用官方 split，若重划分则单独保存版本

### 6.3 V2X-Seq-SPD 转换产物

`SPD` 数据处理至少输出三类结果：

1. 原始索引清单  
   包括场景、帧、时间戳、模态存在性、标定路径和 cooperative 配对

2. 训练格式转换结果  
   使用仓库现有 `spd2kitti_detection` 与 `spd2kitti_tracking` 工具

3. 可视化与校验结果  
   包括投影图、BEV 叠加图、样例序列回放截图

## 7. 训练与评估路线

### 7.1 Phase 1: 数据与环境

目标：

- 下载并解压 `V2X-Seq-SPD`
- 建立 `DAIR-V2X/data/V2X-Seq-SPD` 链接或等价路径
- 运行 `SPD` 转换脚本
- 抽样完成不少于 `20` 组投影与配对可视化

验收：

- 数据可读取
- 标定链可闭环
- split 可复现

### 7.2 Phase 2: 单端基线

目标：

- 先跑 vehicle-only baseline
- 再跑 infrastructure-only baseline
- 形成冻结的单端 AP/Recall 基线

说明：

- 一期优先 `LiDAR` 主导
- 图像路线可保留为并行支线，不阻塞主链路

### 7.3 Phase 3: 协同基线

目标：

- 在 `V2X-Seq-SPD` 上跑通至少一种协同方式
- 推荐优先顺序：
  1. `late fusion`
  2. `intermediate fusion`
  3. `early fusion`

理由：

- 后融合更稳，便于先验证坐标、同步与去重
- 中间融合作为主创新方向更适合后续扩展

### 7.4 Phase 4: 通信鲁棒性

目标：

- 在 `OPV2V` 上完成：
  - 固定延迟
  - 随机抖动
  - 丢包
  - 带宽限制
  - 位姿误差

输出：

- 精度-延迟曲线
- 精度-丢包率曲线
- payload 统计
- 降级日志与失败案例

### 7.5 Phase 5: 系统集成与回放

目标：

- 统一回放入口
- 输出 `system_status / node_status / communication_status`
- 支持 BEV 可视化与结果导出

## 8. 配置策略

所有关键参数必须配置化，至少包括：

- 数据根目录
- split 文件路径
- 点云范围
- 体素尺寸
- 融合模式
- 节点列表
- 通信参数
- 位姿扰动参数
- 输出目录
- 随机种子

禁止：

- 在模型代码中硬编码数据路径
- 在数据读取代码中静默修正异常样本

## 9. 交付物

一期至少交付：

1. 数据说明文档
2. 数据处理脚本与 README
3. split 文件与版本号
4. 标定检查结果与样例图
5. 单端与协同基线配置
6. 评估脚本与评估结果
7. 通信故障注入配置与曲线
8. 失败案例汇总
9. 已知限制说明

## 10. 验收口径

方案 B 的完成标准不是“把所有数据集都接进来”，而是：

### P0 必达

- `V2X-Seq-SPD` 数据可完整读取并完成格式转换
- 单端基线可训练或至少可推理评估
- 协同基线可运行并输出统一坐标系三维目标
- `OPV2V` 的故障注入可运行并产生日志
- 提供复现步骤，非原开发者可跑通样例

### P1 建议达成

- 至少一种中间融合可训练或评估
- 提供遮挡收益分析
- 提供节点异常降级策略

### P2 后续扩展

- 相机-LiDAR 深层融合
- 协同跟踪
- UI 演示与在线服务化

## 11. 风险与应对

### 风险 1: V2X-Seq-SPD 下载与存储压力较大

应对：

- 原始包只读保存
- 转换产物按需生成
- 先跑 example 或子集完成链路验证

### 风险 2: 图像分支依赖更重

应对：

- 一期将 `LiDAR` 作为主线
- 图像分支不阻塞协同主链路

### 风险 3: OPV2V 与真实数据口径不同

应对：

- 不混合主指标
- 仅将 `OPV2V` 用于融合策略调试与鲁棒性验证

## 12. 立即执行清单

按优先级的下一步如下：

1. 准备 `V2X-Seq-SPD` 原始数据并落到 `DATA/raw/V2X-Seq-SPD`
2. 在 `DAIR-V2X/data/` 下建立到 `V2X-Seq-SPD` 的链接或镜像目录
3. 运行 `spd2kitti_detection` 转换脚本
4. 生成完整性报告、split 清单和 20 组可视化抽检
5. 冻结第一版单端和后融合基线配置
6. 准备 `OPV2V` 并接入故障注入实验

## 13. 结论

方案 B 是当前最贴题、也最符合现有仓库能力的路线：

- 真实主线：`V2X-Seq-SPD`
- 鲁棒性与故障注入：`OPV2V`
- 回归与兼容性：`DAIR-V2X-C`

该路线避免继续把一期主进度绑定在“当前 `DAIR-V2X-C` 路侧图像缺失”这一单点问题上，同时保留真实车路协同时序感知的研究价值和工程可交付性。
