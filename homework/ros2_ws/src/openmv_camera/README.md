# OpenMV H7 Plus → ROS 2 Humble：取图、跟踪、PnP 与 TF

当前版本为 v1.0.0 最终交付版。本包已实现 OpenMV 连续取图与传输、ROS 2 `Image/CameraInfo` 发布、真实 QVGA 标定加载、HSV 分割、单帧正方形确认、跨帧目标 ID 与遮挡状态管理、平面 IPPE 位姿、按图像时刻查询的 TF、One Euro 位置滤波、四元数 SLERP、统一 bag 回放、真实尺寸 RViz2 Marker，以及可选的外部动态安装 TF 接口。`pipeline.launch.py` 启动七个 live 节点，`replay.launch.py` 启动六个算法节点，两者均可按需打开 RViz2。

**最终验收状态**：用户已现场确认 v0.9.0 默认 `assumed_static` 模式的实时检测、基坐标位姿和滤波输出，并完成标准 bag 重算回放；v1.0.0 相对该验收基线只更新版本与交付文档，算法、参数和启动流程不变。外部动态 TF 接口已通过软件测试，但真实机器人动态 TF 和 external 动态 bag 回放尚未现场验收；数值精度、延迟、自动曝光、增益和白平衡锁定也未验收。当前跟踪不输出遮挡期间的虚拟位姿；PnP 只输出等价姿态，不解决正方形 90° 旋转和正反面歧义。默认安装外参仍是假设值，详细验收证据和限制见包内 `ACCEPTANCE.md` 与 `POSE_TF_ASSUMPTIONS.md`。

## 两终端快速启动（推荐）

先关闭所有旧 ROS 终端和 rqt，避免重复节点抢串口或重复发布 TF。

终端 1 完成构建、启动七个节点并打开 RViz2。`PYTHONNOUSERSITE=1` 用于避开用户目录中新版 setuptools 与 colcon 的已知兼容问题：

```bash
source /opt/ros/humble/setup.bash
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro humble
PYTHONNOUSERSITE=1 colcon build --symlink-install --packages-select openmv_camera \
  --event-handlers console_direct+
source ~/ros2_ws/install/setup.bash
ros2 launch openmv_camera pipeline.launch.py rviz:=true
```

不需要 RViz2 时省略 `rviz:=true`。保持终端 1 运行，终端 2 检查跟踪、原始位姿与滤波位姿：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 topic echo --once /camera/tracking/stats
ros2 topic echo --once /camera/pose/stats
ros2 topic echo --once /camera/target_pose_base
ros2 topic echo --once /camera/filter/stats
ros2 topic echo --once /camera/target_pose_filtered
```

需要图像窗口时，在同一终端再启动 rqt：

```bash
ros2 run rqt_image_view rqt_image_view
```

选择 `/camera/square/overlay`，QoS 为 Best Effort/Sensor Data。RViz2 已自动加载 `rviz/target.rviz`，Fixed Frame 为 `base_link`，包含 TF、原始目标平面和滤波轮廓。默认目标为 99 mm，50 mm 目标需先修改 `config/pose.yaml` 的 `target_size_m: 0.050`，Marker 会从 PnP 统计同步该尺寸。

## 1. 话题与数据流

```text
OpenMV OV5640（QVGA、JPEG、目标上限 20 FPS）
  → USB VCP 二进制帧（序号、板端毫秒、宽、高、长度、CRC32）
  → 主机按当前待收字节短读、分片解析与重同步
  → 容量为 2 的最新帧队列
  → OpenCV JPEG 解码为 BGR8
  → /camera/image_raw（Best Effort）
  → /camera/camera_info（Reliable）
  → /camera/stats（JSON 字符串，1 Hz）
```

默认配置为 320×240、JPEG 质量 80、目标上限 20 FPS。它们是实验起点，不是已达成的性能结论。

主机不能直接使用 `serial.read(65536)` 读取连续流：pyserial 会等待读满指定字节数或超时，从而把多帧攒成突发批次。本包使用 `in_waiting` 读取当前待收字节；空闲时只等待 1 字节，单次最多读取 16384 字节。若部分帧超过 `frame_timeout_ms`（默认 500 ms）仍未收全，解析器会丢弃该候选帧、累计 `frame_timeouts_total` 并重新同步，避免错误帧头造成长时间静默。

## 2. 安装依赖与构建

在 Ubuntu 22.04 主机上执行：

```bash
source /opt/ros/humble/setup.bash
sudo apt update
sudo apt install -y \
  python3-colcon-common-extensions python3-setuptools python3-serial \
  python3-opencv python3-numpy python3-yaml ros-humble-rqt-image-view \
  ros-humble-rviz2 ros-humble-ros2doctor ros-humble-rosbag2 ros-humble-message-filters
```

将整个 `ros2_ws` 目录复制到 Ubuntu 主机，例如 `~/ros2_ws`，然后：

```bash
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
PYTHONNOUSERSITE=1 colcon build --symlink-install --packages-select openmv_camera \
  --event-handlers console_direct+
source ~/ros2_ws/install/setup.bash
command -v openmv_stream_check
```

若 `rosdep` 尚未初始化，先按 ROS 2 Humble 官方说明完成初始化；上面的 apt 命令已列出本阶段直接依赖。最后的 `command -v` 必须打印工具路径；如果没有输出，说明构建或环境加载尚未完成，应先保留并检查上面的 colcon 输出，不要直接进入 100 帧验收。

## 3. 在 OpenMV 上运行

### 3.1 先测量板端取图

1. 本步骤应在安装自启 `main.py` 之前执行。如果已经安装，先按第 3.3 节移除或重命名它并复位，避免二进制流干扰 IDE。
2. 用 USB 直连相机，打开 OpenMV IDE 5.0.0，确认固件为 5.0.0。
3. 打开 `ros2_ws/src/openmv_camera/openmv/benchmark_capture.py`，点击 IDE 的运行脚本按钮；不要只在 Ubuntu 终端运行该板端脚本。
4. 展开 IDE 底部的 **Serial Terminal（串口终端）**。脚本的 `print()`、警告和 traceback 都显示在这里，而不是 Ubuntu 的 ROS 终端。
5. 正常输出顺序为：先显示 `benchmark_start`，相机初始化约 2 秒后显示 `camera_ready`，随后每秒显示一次 `capture_loop_fps` 和 `jpeg_bytes`。记录至少 60 秒。
6. 如果连 `benchmark_start` 都没有，确认脚本确实在 IDE 中运行且串口终端已展开；如果显示 traceback，保留完整报错，不要继续部署 `main.py`。
7. 为排除 IDE 预览开销，可在帧缓冲面板选择 Disable 后再测一轮。
8. 此脚本只测取图，不测 USB 持续传输；后者必须执行第 4 节的 100 帧检查。

### 3.2 部署连续传输脚本

1. **不要在 IDE 中直接运行持续发送二进制图像的 `main.py`**。
2. 将包内 `openmv/main.py` 保存为相机上的 `main.py`。
3. 安全弹出相机存储盘，复位相机。
4. 断开 OpenMV IDE 与相机的连接，再启动 Ubuntu 主机接收程序，让其独占 VCP 数据流。

脚本使用 `csi.CSI`、`pyb.USB_VCP` 和 `binascii.crc32`。`omv.disable_fb` 通过 `hasattr` 做可选调用，不再作为运行前提；也不依赖实际固件中不存在的 `USB_VCP.debug_mode_enabled()`。

`usb.isconnected()` 只说明 USB 已枚举，并不代表主机程序正在读取 VCP。即使 USB 已连接，主机未读时发送仍可能走到 200 ms 超时；该检查与超时只用于降低阻塞风险，不等于彻底解决背压。

### 3.3 必须了解：停止与恢复自启脚本

`usb.setinterrupt(-1)` 必须保留，因为 JPEG 二进制流会包含 `0x03`；默认的 VCP Ctrl-C 中断可能把脚本意外停止。其副作用是 VCP 的 Ctrl-C 停止功能被禁用，IDE 的停止操作也可能无效，而保存为 `main.py` 后脚本会开机自启。

正常恢复方法：

1. 先停止 Ubuntu 接收节点。
2. 将相机作为 USB 存储设备连接到电脑。
3. 在相机文件系统中将 `main.py` 重命名或删除；不要在相机和电脑之间同时写同一文件系统。
4. 安全弹出存储设备，再复位相机。
5. 若无法访问文件系统，使用 OpenMV IDE 的官方 bootloader/恢复流程。擦除内部 FAT 文件系统属于最后手段，操作前备份需要的文件，不要无意义地重刷固件。

## 4. 先做 100 帧完整传输检查

这一步不启动 ROS 节点，不依赖 OpenCV，可直接验证：

```text
snapshot → bytearray → struct.pack → USB send → 主机短读 → CRC → 完整 JPEG
```

确认 Linux 设备：

```bash
ls -l /dev/serial/by-id/
ls -l /dev/ttyACM*
```

若只有权限错误，将当前用户加入 `dialout` 组并**注销后重新登录**：

```bash
sudo usermod -a -G dialout $USER
```

正常构建后运行：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
command -v openmv_stream_check
mkdir -p ~/openmv_experiments/phase1
set -o pipefail
openmv_stream_check --port /dev/ttyACM0 --frames 100 --timeout 20 \
  | tee ~/openmv_experiments/phase1/stream_100.json
```

如果截图式 `openmv_stream_check: command not found` 再次出现，先按第 2 节重新构建。只想先验证串口、暂时不处理 ROS 构建时，也可以直接从源码运行同一工具：

```bash
mkdir -p ~/openmv_experiments/phase1
set -o pipefail
PYTHONPATH="$HOME/ros2_ws/src/openmv_camera" \
python3 -m openmv_camera.stream_check \
  --port /dev/ttyACM0 --frames 100 --timeout 20 \
  | tee ~/openmv_experiments/phase1/stream_100.json
```

该工具报告实际接收帧数、主机接收帧率、板端循环帧率、JPEG 吞吐、单次读取交付帧数的 max/mean、序号缺失、CRC、半帧超时和重同步统计。吞吐量使用“首帧之后的 JPEG 载荷字节数 ÷ 首尾完整帧间隔”，避免把首帧字节计入 99 个帧间隔而高估。

超时、串口异常或操作系统错误时，工具仍输出包含 `success:false`、`error`、`frames_received`、`wall_elapsed_sec` 及已有统计的部分 JSON，然后以非零状态退出；上面先启用 `pipefail`，可避免 `tee` 掩盖该退出状态。100 帧通过只表示短时段完整链路跑通，不等于 10 分钟稳定或全链路 20 FPS 验收通过。

## 5. 启动 ROS 2 与查看图像

终端 1：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch openmv_camera live.launch.py
```

默认使用 `config/live.yaml` 中的 `serial_port`。需要临时覆盖时才执行：

```bash
ros2 launch openmv_camera live.launch.py serial_port:=/dev/ttyACM1
```

`serial_port` launch 参数默认为空，不会再无条件覆盖 YAML。也可通过 `params_file:=/绝对路径/local.yaml` 使用另一份配置。

终端 2（rqt_image_view）：

```bash
source ~/ros2_ws/install/setup.bash
rqt_image_view
```

1. 选择 `/camera/image_raw`。
2. 在工具栏 QoS 下拉菜单中选择 `Best Effort`（或 `Sensor Data`）。这是固定步骤，不是可选项；默认 Reliable 订阅无法匹配 Best Effort 发布端。

终端 3（RViz2）：

```bash
source ~/ros2_ws/install/setup.bash
rviz2
```

1. Add → By display type → Image。
2. 在 Image 显示项中设置 Topic 为 `/camera/image_raw`。
3. 展开 Topic 的 QoS 设置，将 Reliability 固定设为 `Best Effort`，Depth 设为 `1`。

终端 4：

```bash
source ~/ros2_ws/install/setup.bash
ros2 topic list
ros2 topic echo --once /camera/camera_info
ros2 topic hz /camera/image_raw
ros2 topic echo /camera/stats
```

Humble 的 `ros2 topic hz` 不支持 `--qos-reliability` 参数；它自身使用 sensor-data QoS，可直接匹配本节点的 Best Effort 图像话题，不要添加上述参数。

预期话题：

```text
/camera/image_raw
/camera/camera_info
/camera/stats
```

live 节点要求 `use_sim_time: false`，避免实时图像时间戳与 `/clock` 混用。若误设为 `true`，节点会记录 fatal 日志、清理已创建的 ROS 节点并以状态 1 退出，不会启动串口读取线程。

v0.1.6 的取图处理和统计定时器使用 `ClockType.STEADY_TIME`，避免虚拟机/NTP 调整系统墙钟时 `rclpy` 默认 ROS 时间定时器暂停。该修改只影响定时调度；`Image.header.stamp` 仍按第 6 节使用主机墙钟，不代表时钟对齐已经完成。`ros2 topic hz` 自身仍可能在系统时间跳变时显示负间隔，需结合单调时钟统计和增量计数判断。

## 6. 统计字段与时间戳限制

| 字段 | 含义 |
|---|---|
| `capture_fps_board` | 相邻板端 `snapshot()` 完成时刻计算的板端循环帧率，包含发送阻塞影响 |
| `received_fps_host` | 主机收到且 CRC 有效的完整 JPEG 帧率 |
| `published_fps_ros` | 解码成功并实际发布的 ROS 图像帧率 |
| `rx_ms_mean` | 首次识别帧头到收齐载荷的平均耗时，不是曝光到主机的总延迟 |
| `decode_ms_mean` | OpenCV JPEG 解码平均耗时 |
| `publish_latency_ms_mean` | 解析完整帧到 ROS 发布的平均耗时，不包含此前的串口等待 |
| `rx_batch_frames_max` | 最近 5 秒内，单次串口读取交付的最大有效帧数；持续偏大并伴随队列丢帧时需检查批量攒帧 |
| `rx_batch_frames_mean` | 最近 5 秒内，每次产生有效帧的读取所交付的平均帧数 |
| `rx_batch_frames_max_total` | 自启动以来单次读取交付的最大有效帧数，不随滑窗衰减 |
| `receive_batches_total` | 自启动以来至少交付一个有效帧的读取批次数 |
| `sequence_dropped_total` | 根据板端连续序号推断的缺失帧数 |
| `queue_dropped_total` | 有界队列或最新帧策略主动丢弃的帧数 |
| `connection_attempts_total` | 串口打开尝试次数 |
| `connections_total` | 串口成功打开次数 |
| `connection_errors_total` | 串口异常或非法配置错误次数 |
| `reconnects_total` | 首次连接之后成功重新打开的次数，不再把失败尝试计作重连 |
| `crc_errors_total` | CRC 校验失败帧数 |
| `frame_timeouts_total` | 部分帧超过 `frame_timeout_ms` 未收全而被丢弃的次数 |
| `resync_bytes_total` | 为寻找下一帧头丢弃的字节数；刚接入时非零可以接受 |

当前 `Image.header.stamp` 是**主机解析出完整 JPEG 时的墙钟时间**，不是曝光时刻，也不是字节到达内核的硬件时间戳。误差包括串口读取等待、主机调度及内核/用户缓冲积压；不能简单声称固定等于读取超时，更不能给出未经验证的严格上界。v0.9.0 已提供 external 动态 TF 接口，但真实机器人接入前仍必须完成时钟偏差估计和时间对齐；软件接口实现不代表这项现场工作已经完成。

`CameraInfo` 使用 Reliable，是为了与常见相机驱动和 `image_transport`/`camera_info_manager` 的用法一致，并减少逐个工具调整 QoS；不是因为 Humble 默认 `ros2 topic echo` 无法接收 Best Effort。

未提供真实标定文件时，`CameraInfo.K` 全零、`D` 为空，明确表示尚未标定。依赖有效相机模型的下游（例如 `image_geometry.PinholeCameraModel`）会在 `K[0]==0` 时失败或抛出异常，不能使用这种无效内参做 PnP。当前真实标定位于 `config/camera_qvga.yaml`，启动时通过 `config/live_calibrated.yaml` 加载；用户已确认现场 `K` 非零，但 RMS 未提供，标定精度尚未评价。自动增益、曝光和白平衡锁定仍未实现，HSV 阈值必须在实际光照下调整。

## 7. 十分钟稳定性实验

启动节点后，在另一个终端保存统计：

```bash
mkdir -p ~/openmv_experiments/phase1
source ~/ros2_ws/install/setup.bash
timeout 600 ros2 topic echo /camera/stats \
  > ~/openmv_experiments/phase1/stats.txt
```

与此同时：

```bash
timeout 600 ros2 topic hz /camera/image_raw \
  > ~/openmv_experiments/phase1/topic_hz.txt
```

保存环境和实际参数：

```bash
ros2 doctor --report | tee ~/openmv_experiments/phase1/ros2_doctor.txt
ros2 param dump /camera/openmv_camera \
  > ~/openmv_experiments/phase1/parameters.yaml
cp ~/ros2_ws/src/openmv_camera/config/live.yaml \
  ~/openmv_experiments/phase1/live.yaml
```

同时记录 OpenMV 固件版本、板端脚本、主机代码版本、USB 连接方式、工作分辨率和 JPEG 质量。

### 验收标准

- 100 帧完整传输检查成功，随后连续运行 10 分钟且节点无异常退出。
- 断开后停止输出并尝试重连；成功重连与失败尝试分别计数。
- rqt_image_view 和 RViz2 均按第 5 节设置 Best Effort，图像持续更新，方向、颜色和分辨率正确。
- 初始同步后，CRC 错误、非法 JPEG、半帧超时和重同步字节不持续增长。
- 序号缺失、5 秒滑窗批量读取和队列丢帧均有统计，不用旧帧伪装实时输出。
- 分别报告板端、接收和发布帧率；只有真实结果支持时才宣称约 20 FPS。
- `CameraInfo` 与图像时间戳一致，且未标定状态表达明确。

## 8. 排障

| 现象 | 检查与处理 |
|---|---|
| 没有 `/dev/ttyACM*` | 更换数据线/USB 口；确认相机已上电；检查 IDE 是否仍能识别 |
| `Permission denied` | 加入 `dialout` 并重新登录 |
| IDE 不打印 FPS | 展开 IDE 底部 Serial Terminal；确认运行的是 `benchmark_capture.py`；检查是否已有自启 `main.py`；保留 `benchmark_start` 之前的错误或完整 traceback |
| `openmv_stream_check: command not found` | 设备节点问题与工具安装问题要分开处理；按第 2 节重新 colcon build、source 并用 `command -v` 自检，或按第 4 节用 `PYTHONPATH` 直接从源码运行 |
| 一直 `waiting` | 断开 IDE；确认相机已保存并运行 `main.py`；核对端口 |
| `frame_timeouts_total` 持续增长 | 检查是否同时有 IDE/其他程序读取 VCP，核对数据线和供电；不要直接调大超时掩盖断流 |
| IDE 无法用 Ctrl-C 停止自启脚本 | 按第 3.3 节通过 USB 存储移除或重命名 `main.py` |
| IDE 报 CRC 断言失败 | 保留原始错误并停止实验，不要关闭校验绕过 |
| CRC 错误持续增长 | 检查是否同时有 IDE/其他程序读取 VCP，更换 USB 线并重新连接 |
| 有大量序号缺口但 CRC 正常 | 检查批量帧、主机调度和 USB 传输，再对比降低 JPEG 质量或分辨率的结果 |
| 接收帧率正常、发布帧率低 | 查看 5 秒滑窗 `rx_batch_frames_max`、队列丢帧、解码耗时和 CPU，不要先归因于 USB |
| 每分钟集中丢帧且 `topic hz` 出现负间隔 | 使用 v0.1.6 单调时钟定时器并检查虚拟机/NTP 校时；不要把它误判为 USB 丢帧 |
| `camera_info` 一直收不到 | 当前发布端为 Reliable；检查话题名和 DDS，不要改成不匹配 QoS |
| `image_raw` 无显示 | 将 rqt/RViz2 Reliability 设为 Best Effort，并直接运行 `ros2 topic hz /camera/image_raw` 检查 |
| 分辨率错误 | 板端脚本和 YAML 必须同时为 QVGA 320×240 |

## 9. 真实截图、视频和 bag 采集

### 截图

1. 同屏显示 rqt 图像、`ros2 topic hz` 和 `/camera/stats` 统计。
2. 使用 Ubuntu 截图工具保存为 `phase1_rqt_stats.png`。
3. 截图必须来自本次真实运行，不使用合成数值。

### 视频

1. 打开 rqt、统计终端和节点终端，开始屏幕录制。
2. 连续录制至少 60 秒，包含静止、移动目标、拔线/恢复中的一个明确过程。
3. 保存原始视频，并记录对应时间段和实验条件。

### bag

```bash
ros2 bag record -o ~/openmv_experiments/phase1/input_bag \
  /camera/image_raw /camera/camera_info /camera/stats
# 结束记录后：
ros2 bag info ~/openmv_experiments/phase1/input_bag
```

第一阶段尚无 TF；后续阶段必须加入 `/tf`、`/tf_static` 和必要动态数据。原始 `bgr8` bag 占用空间较大，记录前检查磁盘。

回放前停止 live 节点，避免重复发布：

```bash
ros2 bag play --clock ~/openmv_experiments/phase1/input_bag
```

本阶段的 replay 只用于检查图像记录与回放；live 驱动不消费 `/clock`，旧统计数据也不作为新实时统计。**第一阶段尚未满足原任务第 9 条要求的统一 live/replay/test launch**：当前只有 live launch、bag 回放命令和软件测试，计划在第七阶段系统集成时统一接入仿真时间、launch 和 YAML 配置并补齐。

## 10. HSV 颜色分割（v0.2.0）

本阶段新增 `/camera/hsv_segmenter`：

| 类型 | 名称 | 说明 |
|---|---|---|
| 订阅 | `/camera/image_raw` | 要求紧凑 `bgr8`，使用 Sensor Data QoS |
| 发布 | `/camera/hsv/mask` | `mono8`，命中为白色，未命中为黑色 |
| 发布 | `/camera/hsv/preview` | `bgr8`，原图命中区域覆盖为绿色 |
| 发布 | `/camera/hsv/stats` | JSON，包含 `hsv_ms`、`mask_pixels`、`mask_ratio` 和当前阈值 |

`config/hsv.yaml` 的初始白色试探范围是 `H=0–179、S=0–70、V=180–255`，不是实测结论。本阶段没有形态学、轮廓、目标确认、PnP 或 TF；颜色命中不等于已确认正方形目标。

### 10.1 构建

```bash
source /opt/ros/humble/setup.bash
cd ~/ros2_ws
PYTHONNOUSERSITE=1 colcon build --symlink-install --packages-select openmv_camera \
  --event-handlers console_direct+
source ~/ros2_ws/install/setup.bash
```

保持已标定的相机节点运行。若它尚未启动，在终端 1 执行：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch openmv_camera live.launch.py \
  params_file:=/home/a/ros2_ws/src/openmv_camera/config/live_calibrated.yaml
```

在终端 2 启动 HSV 节点：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 run openmv_camera openmv_hsv_node --ros-args \
  --params-file /home/a/ros2_ws/src/openmv_camera/config/hsv.yaml
```

### 10.2 查看和调参

打开 `rqt_image_view`，分别选择 `/camera/hsv/mask` 和 `/camera/hsv/preview`，QoS 固定选择 **Best Effort** 或 **Sensor Data**。期望目标区域在 mask 中为白色、在 preview 中为绿色，背景大部分为黑色；大片背景命中时不要用轮廓判断来掩盖阈值问题。

在终端 3 在线调整，例如：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 param set /camera/hsv_segmenter s_max 60
ros2 param set /camera/hsv_segmenter v_min 190
ros2 topic echo --once /camera/hsv/stats
```

- 饱和彩色背景被选中：通常逐步降低 `s_max`。
- 较暗背景被选中：通常逐步提高 `v_min`。
- 白色目标过暗而缺失：可逐步降低 `v_min`，同时观察背景误命中。
- OpenCV 范围为 H 0–179、S/V 0–255，且各通道 min 不得大于 max；非法更新会被拒绝并保留旧值。
- 调好后将六个值写回 `config/hsv.yaml`，否则重启节点会恢复文件中的参数。

本步骤的验收只针对颜色分割：目标命中、背景大部分剔除、stats 持续输出。真实阈值和处理耗时以现场输出为准；当前未锁定自动曝光、增益和白平衡，换光照后必须重新检查。

## 11. 单帧正方形确认（v0.3.0）

新增 `/camera/square_detector`，用相同时间戳同步原始图像和 HSV 掩膜。处理顺序为：开/闭形态学、外轮廓、面积过滤、四边形拟合、凸性、邻边长比和四个内角检查。

| 类型 | 名称 | 说明 |
|---|---|---|
| 订阅 | `/camera/image_raw` | 原始 `bgr8`，Sensor Data QoS |
| 订阅 | `/camera/hsv/mask` | HSV `mono8`，Sensor Data QoS |
| 发布 | `/camera/square/mask` | 只保留通过几何检查的区域 |
| 发布 | `/camera/square/overlay` | 原图叠加绿色四边形、红色中心叉和编号 |
| 发布 | `/camera/square/stats` | JSON，包含是否检出、候选剔除原因、顶点、中心和几何指标 |

### 11.1 构建与启动

```bash
source /opt/ros/humble/setup.bash
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
PYTHONNOUSERSITE=1 colcon build --symlink-install --packages-select openmv_camera \
  --event-handlers console_direct+
source ~/ros2_ws/install/setup.bash
```

依次在三个终端启动相机、HSV 和正方形节点，前两个命令见第 5、10 节。第三个终端执行：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 run openmv_camera openmv_square_node --ros-args \
  --params-file /home/a/ros2_ws/src/openmv_camera/config/square.yaml
```

三个进程都要保持运行。rqt 查看 `/camera/square/overlay` 或 `/camera/square/mask`，QoS 选 Best Effort/Sensor Data。

```bash
ros2 topic echo --once /camera/square/stats
```

`detected:true` 且 `target_count` 大于 0 才表示本帧存在通过全部几何门限的候选。`rejected` 分别统计面积、顶点数、凸性、长宽比和角度剔除数量，用于定位漏检发生在哪一级。

### 11.2 参数与验收

`config/square.yaml` 是初始门限：最小面积 300 px、四边形拟合比例 0.04、最大邻边长比 1.4、内角允许 70–110°。它们不是真实场景已验收值。

- 小目标因面积被拒绝时，可在确认 stats 后逐步降低 `min_area_px`，例如 `ros2 param set /camera/square_detector min_area_px 200.0`。
- 透视较强时，长宽比或角度可能拒绝真实目标；只有核对 stats 后才逐步放宽，不能一开始就取消几何检查。
- 形态学核必须为奇数，开/闭运算用于小噪声和缝隙，不应用大核把相邻白色区域强行连成目标。
- 验收要求真实目标有绿色四边形，LEGION 字母、长矩形和边缘白块不被标成 SQUARE，并在移动、旋转和改变距离后复查。

单帧 `detected:true` 不等于稳定跟踪；当前跨帧关联见第 14 节。两个正方形物理尺寸不同，不能仅凭几何外观可靠区分 99 mm 与 50 mm 目标，仍须由配置明确指定尺寸。

## 12. PnP 位姿与 TF（v0.4.0，v0.6.0 接入跟踪，v0.9.0 支持外部安装 TF）

`/camera/pose_estimator` 读取 `/camera/tracking/stats` 和 `/camera/camera_info`，只选择面积最大的已确认跟踪目标进行 IPPE 平面 PnP。`/camera/pose/stats` 记录 `selected_track_id`；切换目标 ID 时不会沿用上一目标的旋转候选。

| 输出 | 类型/内容 |
|---|---|
| `/camera/target_pose_camera` | `PoseStamped`，目标在 `camera_optical_frame` 中的等价位姿 |
| `/camera/target_pose_base` | `PoseStamped`，按图像时刻经 TF 转换到 `base_link` |
| `/camera/pose/stats` | JSON，包含有效性、失败原因、跟踪 ID、平面多解、重投影误差、两套位姿和安装 TF 模式 |
| `/tf_static` | 仅 `assumed_static` 模式发布假设的 `base_link → camera_optical_frame` |
| `/tf` | 有效新检测对应的 `camera_optical_frame → target` |

**默认假设安装外参不是实测值**：平移 `[0.20, 0, 0.10]` 米、RPY `[-90, 0, -90]` 度。坐标轴、矩阵、四元数和修改方法见包内 `POSE_TF_ASSUMPTIONS.md`，不要省略该记录。external 模式的配置与验收见第 17 节。

### 12.1 构建与启动

推荐直接使用顶部的两终端快速启动，由 `pipeline.launch.py` 按同一配置启动七个节点，避免漏开跟踪或可视化节点。默认边长为 99 mm。若当前目标是 50 mm，先把 `config/pose.yaml` 的 `target_size_m` 改为 `0.050` 再启动；不要混用尺寸。修改假设安装平移、RPY 或安装模式后需重启位姿节点。

### 12.2 验收与排障

```bash
ros2 topic echo --once /camera/tracking/stats
ros2 topic echo --once /camera/pose/stats
ros2 topic echo --once /camera/target_pose_camera
ros2 topic echo --once /camera/target_pose_base
ros2 run tf2_ros tf2_echo base_link camera_optical_frame
ros2 run tf2_ros tf2_echo camera_optical_frame target
```

- 有效时应看到 `valid:true`、`reason:ok`、`selected_track_id`、正深度和较低重投影误差。
- `target_occluded`：跟踪器保留短期身份但当前没有可见目标；`target_not_confirmed`：新轨迹尚未达到确认帧数。
- `no_square_target`：先检查正方形和跟踪节点；`invalid_or_missing_camera_info`：检查真实标定和 `K`。
- `no_valid_pnp_candidate`：查看 `pnp.rejected_candidates`、深度和重投影误差，不要直接取消正深度/可见面检查。
- `tf_lookup_failed`：按当前模式检查假设静态 TF 或外部 TF、frame 名和图像时间戳；不能改用最新 TF 掩盖时间对齐问题。
- `planar_ambiguous:true`：存在误差接近的平面候选，应保留警告并复核，不能宣称方向唯一。
- RViz2 设置 Fixed Frame 为 `base_link`，添加 TF，检查 `base_link → camera_optical_frame → target`；默认假设外参未替换前，基坐标系位置仅用于联调。

无目标、遮挡、无有效 PnP 或 TF 查询失败时不会发布新位姿，也不会重发旧 TF。当前候选连续性选择不是滤波；One Euro 与四元数 SLERP 见第 13 节，外部动态安装 TF 见第 17 节。

## 13. 位姿滤波（v0.5.0）

新增 `/camera/pose_filter`。位置使用按图像时间戳计算 `dt` 的 One Euro 滤波：静止时降低抖动，移动速度增大时提高截止频率以减少滞后；姿态使用四元数符号连续处理和 SLERP，不平均欧拉角。

| 类型 | 名称 | 说明 |
|---|---|---|
| 订阅 | `/camera/target_pose_base` | 未滤波的 `base_link` 目标位姿 |
| 订阅 | `/camera/pose/stats` | 上游有效性、丢失原因和图像时间戳 |
| 发布 | `/camera/target_pose_filtered` | 滤波后的 `PoseStamped` |
| 发布 | `/camera/filter/stats` | JSON，包含滤波指标、异常剔除、丢失和重捕获计数 |
| 发布 | `/tf` | `base_link → target_filtered`，不覆盖原始 `target` TF |

`config/filter.yaml` 初始参数为：位置最小截止频率 1 Hz、速度系数 `beta=0.02`、姿态时间常数 0.12 s、位置跳变上限 0.30 m、姿态跳变上限 80°、重捕获超时 0.5 s。它们是调试起点，不是真实场景的最优值。静止仍抖动时可适当降低 `position_min_cutoff_hz`；快速移动滞后明显时可适当提高 `position_beta`，每次只改一项并对照原始位姿。

超过跳变上限的输入会被拒绝并计入 `outliers_rejected_total`，不会污染滤波状态；超过重捕获超时会重置滤波器，从下一份有效输入重新初始化。非递增时间戳同样会被拒绝。上游报告无目标或无效位姿时，节点只发布失败统计，不发布新滤波位姿，也不重发旧 TF。

### 13.1 启动与验收

推荐使用顶部的两终端快速启动，由 `pipeline.launch.py` 一次启动六个节点。终端 2 执行：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 topic echo --once /camera/tracking/stats
ros2 topic echo --once /camera/pose/stats
ros2 topic echo --once /camera/target_pose_base
ros2 topic echo --once /camera/filter/stats
ros2 topic echo --once /camera/target_pose_filtered
```

有效时原始与滤波统计均应包含 `valid:true`、`reason:ok`；`filter/stats` 还包含 `dt_sec`、位置和姿态跳变量、滤波后的位置/四元数及累计计数。现场验收需分别检查：

1. 目标静止时，对照 `/camera/target_pose_base` 与 `/camera/target_pose_filtered` 的连续输出，确认位置抖动下降且没有明显漂移。
2. 缓慢和快速移动目标，确认滤波输出能跟随；若滞后过大，再调整 One Euro 参数，不能用取消跳变检查来掩盖异常。
3. 遮挡目标后，`filter/stats` 应报告上游失败原因，滤波位姿停止更新；恢复目标后应重新输出，并检查 `lost_events_total`、`reacquisitions_total`。
4. RViz2 中同时检查原始 `target` 和 `target_filtered`，两者都应位于 `base_link` 树下；假设安装外参替换为实测值之前，不代表真实机器人精度。

## 14. 时序跟踪与遮挡管理（v0.6.0）

新增 `/camera/target_tracker`，订阅 `/camera/square/stats`，发布 `/camera/tracking/stats`。跟踪完全在图像坐标中进行：以上次质心和速度预测当前位置，将满足距离与面积门限的候选按距离排序，再做一对一关联。已确认目标按面积排序，PnP 仍只处理第一个目标。

| 状态 | 含义 | 是否向 PnP 提供目标 |
|---|---|---|
| `tentative` | 新轨迹尚未达到确认帧数 | 否 |
| `tracked` | 当前帧存在已确认关联 | 是 |
| `occluded` | 短期未检出，保留 ID 和预测 | 否 |
| `lost` | 超过帧数或时间上限，轨迹已删除 | 否 |
| `no_target` | 当前没有活动轨迹 | 否 |
| `invalid_input` | 输入 JSON、时间戳或检测数据无效 | 否 |

`config/tracking.yaml` 的初始值为：关联距离 60 px、面积比上限 2.0、速度更新系数 0.5、连续命中 2 帧确认、最多遮挡 5 帧且不超过 0.5 s。两个遮挡上限任一超限都会删除轨迹；重新出现后分配新 ID。短暂遮挡后重新关联则沿用原 ID，并增加 `reacquisitions_total`。

**遮挡期间 `targets` 为空，位姿和 TF 不会用预测值补齐。**预测只用于下一次检测的 ID 关联。非递增时间戳会被拒绝。`/camera/square/overlay` 中的 `SQUARE 0` 仍是单帧面积序号，不是跟踪 ID；真实 ID 以 `/camera/tracking/stats` 的 `track_id` 和 `selected_track_id` 为准。

### 14.1 现场验收

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 topic echo /camera/tracking/stats
ros2 topic echo /camera/pose/stats
```

1. 正常可见时，`tracking_state` 为 `tracked`，目标带稳定 `track_id`。
2. 缓慢移动目标，确认 ID 不随单帧面积排序变化；快速移动超出关联门限时应新建轨迹，而不是强行关联。
3. 短暂遮挡时状态变为 `occluded`，`targets` 为空，`pose/stats` 报 `target_occluded`；恢复后检查是否沿用原 ID。
4. 遮挡超过 0.5 s 或 5 帧后应删除轨迹，再次出现时使用新 ID。
5. 若画面中有多个同色目标，检查一对一 ID 关联；当前只有面积最大的已确认目标进入 PnP，不等同于全部目标都输出 6DoF。

## 15. bag 记录与统一回放（v0.7.0，v0.8.0 增加 Marker）

### 15.1 记录一次真实实验

保持 live 的 `pipeline.launch.py` 运行，在终端 2 执行：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
mkdir -p ~/openmv_experiments/phase7

ros2 bag record -o ~/openmv_experiments/phase7/input_run_01 \
  /camera/image_raw /camera/camera_info \
  /camera/stats /camera/hsv/stats /camera/square/stats \
  /camera/tracking/stats /camera/pose/stats /camera/filter/stats \
  /camera/target_pose_base /camera/target_pose_filtered \
  /camera/target_marker_raw /camera/target_marker_filtered \
  /tf /tf_static
```

完成静止、移动、短暂遮挡和长遮挡后，按 Ctrl+C 停止记录并等待 bag 正常关闭。这个 bag 同时保存输入、TF 和结果，便于之后比较；重新计算时只选择输入话题，不能播放全部话题。

另存当时的实际参数和环境报告：

```bash
for node in openmv_camera hsv_segmenter square_detector target_tracker pose_estimator pose_filter target_visualizer; do
  ros2 param dump "/camera/$node" > "$HOME/openmv_experiments/phase7/${node}.yaml"
done
ros2 doctor --report > ~/openmv_experiments/phase7/ros2_doctor.txt
ros2 bag info ~/openmv_experiments/phase7/input_run_01
```

### 15.2 两终端重新计算回放

先关闭 live pipeline、旧 replay 和其他可能发布同名话题的节点。此模式不启动相机节点，也不读取串口。

终端 1：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch openmv_camera replay.launch.py rviz:=true
```

不需要 RViz2 时省略 `rviz:=true`。`replay.launch.py` 启动 HSV、正方形、跟踪、PnP、滤波和可视化六个节点，并对每个节点覆盖 `use_sim_time: true`，即使原 YAML 中 live 值为 false。

终端 2：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 bag play ~/openmv_experiments/phase7/input_run_01 \
  --clock \
  --topics /camera/image_raw /camera/camera_info
```

`--clock` 发布 bag 的 `/clock`；`--topics` 明确只播放原始算法输入。bag 里旧的 `/tf`、`/tf_static`、Marker 和位姿结果不会播放，由当前代码重新生成，因此不存在重复发布者。标准 replay 的 `pose.yaml` 必须继续使用 `mount_tf_mode: "assumed_static"`，假设安装外参来自当前配置；若录制后修改过参数，回放结果反映的是新配置，不是原配置的复现。

**不要把现有 bag 的 `/tf` 直接加入上述 external 重算回放。**该 `/tf` 同时含有机器人 TF 和本包生成的 `target/target_filtered`，直接播放会与当前节点重复发布目标 TF。external 动态回放需要单独准备只含安装关系的 TF 记录，或先过滤掉旧 `target/target_filtered` 并提供过滤后的 TF 源；该动态回放流程尚未现场验收，详见第 17 节。

### 15.3 回放验收与排障

另开检查命令前仍先 source 两个环境。检查：

```bash
ros2 topic echo --once /camera/tracking/stats
ros2 topic echo --once /camera/pose/stats
ros2 topic echo --once /camera/filter/stats
```

- bag 播放后应重新出现 overlay、跟踪状态、原始位姿和滤波位姿；遮挡段仍不得产生新位姿或旧 Marker。
- 输出 `header.stamp` 应与输入图像的原始时间戳一致，而不是回放开始时的墙钟。
- 若 `/clock` 不发布，先检查是否漏掉 `--clock`；若没有任何输出，再检查 bag 路径、`ros2 bag info` 和两个输入话题的消息数。
- 若出现重复 TF 或重复话题，说明 live、旧 replay 或另一次 bag play 尚未关闭；不要通过忽略警告继续实验。
- 需要直接查看 bag 原始内容时，不要启动 `replay.launch.py`。直接播放全部话题属于查看模式，不属于重新计算模式。

### 15.4 直接查看已录制内容

bag 不是视频文件，终端只显示播放状态；原始画面需用 rqt，已录制的 TF/Marker 需用 RViz2。先关闭所有 live 和 replay 算法节点。

只看原始相机画面时，终端 1 执行：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 bag play ~/openmv_experiments/phase7/input_run_01 \
  --topics /camera/image_raw /camera/camera_info
```

终端 2 执行 `ros2 run rqt_image_view rqt_image_view`，选择 `/camera/image_raw`，QoS 设为 Best Effort/Sensor Data。播放终端中空格暂停/继续，方向键上调/下调速度。

直接查看当时录制的 RViz 结果时，先停止上面的 rqt 和 bag play。终端 1 播放全部录制话题：

```bash
ros2 bag play ~/openmv_experiments/phase7/input_run_01 --clock
```

终端 2 打开使用仿真时间的 RViz2：

```bash
ros2 run rviz2 rviz2 \
  -d ~/ros2_ws/src/openmv_camera/rviz/target.rviz \
  --ros-args -p use_sim_time:=true
```

此查看模式不要启动 `replay.launch.py`，否则可能重复发布位姿、Marker 和 TF。`ros2 bag info ~/openmv_experiments/phase7/input_run_01` 可查看录制时长、消息数和话题清单。

## 16. RViz2 真实尺寸可视化（v0.8.0）

新增 `/camera/target_visualizer`，直接消费现有原始与滤波位姿，不改变 PnP、滤波或 TF 数值。

| 话题 | 类型与外观 | 含义 |
|---|---|---|
| `/camera/target_marker_raw` | 绿色半透明 `CUBE` | 原始 `target_pose_base` 的正方形平面 |
| `/camera/target_marker_filtered` | 蓝色 `LINE_LIST` 轮廓 | 滤波后位姿的正方形四边 |

Marker 边长从 `pose/stats` 的 `target_size_m` 同步，默认 99 mm；使用 50 mm 目标时只需正确修改 `config/pose.yaml`。`visualization.yaml` 中 1 mm 显示厚度和 2 mm 线宽只是为了看见模型，**不代表目标真实厚度**。

live 启动：

```bash
ros2 launch openmv_camera pipeline.launch.py rviz:=true
```

replay 启动：

```bash
ros2 launch openmv_camera replay.launch.py rviz:=true
```

两者都会加载 `rviz/target.rviz`，Fixed Frame 已为 `base_link`，并添加 Grid、TF 和两个 Marker。现场检查：

1. 目标可见时，TF 中有 `base_link → camera_optical_frame → target` 和 `base_link → target_filtered`，绿色平面与蓝色轮廓位于对应位姿。
2. 静止时蓝色轮廓应比绿色平面更平稳；移动时两者都应跟随，具体延迟仍以位姿实验为准。
3. 遮挡或位姿无效时，可视化节点收到失败统计并发布 `DELETE`，旧平面和旧轮廓应消失，不能留在最后位置。
4. 若显示 `base_link does not exist` 或目标不出现，先检查 `/camera/pose/stats`、`/camera/filter/stats` 和 TF，不要只重置 RViz。
5. 正方形朝向仍有 90° 与正反面等价歧义，Marker 的方向不是唯一物理朝向；假设安装外参未替换前，位置也不代表真实机器人测量精度。

## 17. 外部动态 TF（v0.9.0）

`config/pose.yaml` 的安装关系现在有两种模式：

| `mount_tf_mode` | 行为 |
|---|---|
| `assumed_static`（默认） | 保持原行为，发布假设的 `base_link → camera_optical_frame` 静态 TF |
| `external` | 不发布安装 TF，按每张图像的时间戳查询机器人提供的外部 TF |

默认配置无需修改，之前的固定外参实验可原样运行。接入真实机器人时，先将 `config/pose.yaml` 改为：

```yaml
mount_tf_mode: "external"
```

external 模式会忽略 `base_to_camera_translation_m` 和 `base_to_camera_rpy_deg`。机器人侧必须独立提供 `base_link → camera_optical_frame`，frame 名与 `pose.yaml` 一致，TF 时间覆盖图像时间戳；不要同时让其他节点和本包发布同一安装关系。模式不能在线切换，必须修改 YAML 并重启，避免旧的假设静态 TF 残留。

完成顶部构建后，用两个终端检查。终端 1 先确认外部 TF 已存在：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 run tf2_ros tf2_echo base_link camera_optical_frame
```

确认持续输出且数值来自机器人后，按 Ctrl+C 停止 `tf2_echo`，在同一终端启动：

```bash
ros2 launch openmv_camera pipeline.launch.py rviz:=true
```

终端 2 检查模式与输出：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 topic echo --once /camera/pose/stats
ros2 topic echo --once /camera/target_pose_base
```

`/camera/pose/stats` 应包含 `mount_tf_mode:"external"` 和 `mount_is_assumed:false`。现场动态验收还应让相机相对机器人低速运动，确认安装 TF 与 `/camera/target_pose_base` 随同一图像时刻的安装关系变化，而不是仍使用假设固定值。

外部 TF 缺失、frame 名不一致或时间外推时，`pose/stats` 会报告 `tf_lookup_failed`，不发布新位姿；不能改用最新 TF 掩盖时间对齐问题。主机图像时间戳不是曝光时刻，真实接入前仍需检查机器人时钟与相机主机的时间对齐。

**动态回放限制**：标准 replay 继续使用 `assumed_static`，只播放图像和 CameraInfo。现有 bag 的 `/tf` 同时含机器人 TF 和本包生成的 `target/target_filtered`，不能在 external 重算回放时简单把 `/tf` 加进 `ros2 bag play --topics`，否则会重复目标 TF。external 动态回放需要单独准备不含旧目标 frame 的安装 TF 记录，或提供过滤后的 TF 源；该流程尚未现场验收。

## 18. 软件测试

```bash
cd ~/ros2_ws/src/openmv_camera
python3 -m unittest discover -s test -v
cd ~/ros2_ws
colcon test --packages-select openmv_camera
colcon test-result --verbose
```

当前开发环境的 67 项测试已通过，覆盖米制模型点、PnP、重投影门限、候选连续性、假设安装旋转、TF 坐标复合、One Euro、四元数 SLERP、异常剔除、重捕获、双目标关联、遮挡状态、安装模式校验、外部安装位置变化、静态 TF 发布保护、live/replay/RViz 启动契约、真实尺寸轮廓几何和参数校验。当前环境没有 ROS 2/RViz2，因此上述 `colcon test` 未在本机执行；软件测试不能替代真实 OpenMV、ROS 2、TF 或精度验证。默认模式的真实 Humble 实时链路及标准回放已由用户现场确认，真实机器人动态 TF 和 external 动态 bag 回放仍待验收。

## 19. 最终交付验收（v1.0.0）

本次最终验收以默认 `assumed_static` 配置为基线：

- 现场 stats 确认 `mount_tf_mode:"assumed_static"`、`mount_is_assumed:true`。
- 实时跟踪包含 `detected:true`，基坐标位姿具有非零有限位置与四元数。
- 滤波统计记录 `accepted_poses_total:116`，并输出滤波位姿。
- 用户完成标准 bag 重算回放后回复 OK；播放截图显示只读打开、速率 1、仅播放图像与 CameraInfo，结束返回 shell 且未显示错误。

v1.0.0 相对该验收基线只更新版本与交付文档，算法、参数和启动流程不变。完整证据、早期实测结果及未验收项目见包内 `ACCEPTANCE.md`。
