# 最终验收记录（v1.0.0）

## 1. 交付基线

v1.0.0 是本次 ROS 2 单目视觉项目的最终交付版。用户现场验收的是 v0.9.0 的默认 `assumed_static` 配置；v1.0.0 只更新版本号和交付文档，不改变算法代码、参数或启动流程。

## 2. 已确认的验收结果

| 项目 | 证据与结论 |
|---|---|
| 软件回归 | 当前开发环境 67 项 Python/OpenCV 单元与静态契约测试全部通过；Python 语法、YAML、XML、RViz 配置和 ZIP 完整性检查通过 |
| 默认安装模式 | 现场 `/camera/pose/stats` 显示 `mount_tf_mode:"assumed_static"`、`mount_is_assumed:true`，确认没有意外切换到外部 TF |
| 实时目标检测 | 现场跟踪输出包含 `detected:true`，说明当前存在已确认跟踪目标 |
| 基坐标位姿 | 现场 `/camera/target_pose_base` 具有非零有限位置与四元数；另一样本记录 `base_translation_m:[0.787188, 0.005633, 0.064912,...]`，证明 PnP 与 TF 转换链路有有效输出 |
| 位姿滤波 | 现场 `/camera/filter/stats` 记录 `accepted_poses_total:116`，并输出滤波四元数和平移，证明滤波器持续接受有效输入 |
| 标准 bag 重算回放 | 用户按两终端流程完成后回复 OK；终端截图显示 bag 以 `READ_ONLY` 打开、速率 1、只播放图像与 CameraInfo，播放结束返回 shell，未显示错误 |
| 早期传输实测 | v0.1.5 十分钟记录接收约 20 FPS、发布约 19.25 FPS，序号/CRC/解码/重连错误增量为 0，但存在周期性队列丢弃；该结果不外推为当前版本无丢帧保证 |

## 3. 最终交付不宣称通过的项目

- 真实机器人外部动态 TF、相机与机器人时钟对齐、external 动态 bag 回放。
- PnP 距离/位置/姿态精度、端到端延迟和标定 RMS 精度评价。
- 正方形 90° 旋转与正反面歧义的唯一方向恢复；当前只输出等价姿态。
- 自动曝光、增益和白平衡锁定，以及跨光照阈值稳定性。
- v0.1.6 单调时钟修正后的十分钟复测；用户此前选择跳过。
- 多目标分别输出 6DoF；当前只对面积最大的已确认目标进行 PnP。
- 遮挡期间的预测位姿；当前遮挡时不发布虚拟位姿，定量遮挡恢复记录未保存。
- 默认假设安装外参的真实机器人精度；实际机器人必须测量外参或提供可信外部 TF。

## 4. 最终运行入口

实时管线：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch openmv_camera pipeline.launch.py rviz:=true
```

标准重算回放（终端 1）：

```bash
ros2 launch openmv_camera replay.launch.py rviz:=true
```

标准重算回放（终端 2）：

```bash
ros2 bag play ~/openmv_experiments/phase7/input_run_01 \
  --clock --topics /camera/image_raw /camera/camera_info
```

直接查看已录制结果时，先关闭所有 live/replay 算法节点，再播放全部录制话题并打开使用仿真时间的 RViz2。不要同时进行“直接播放全部话题”和“算法重算”，否则可能重复发布位姿、Marker 和 TF。

完整配置、动态 TF 接口、原始图像查看和排障方法见包内 `README.md`；安装坐标与假设见 `POSE_TF_ASSUMPTIONS.md`。
