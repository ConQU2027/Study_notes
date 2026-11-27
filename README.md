# 肖皓文 · ROS 2 学习笔记

## 目录

| 目录 | 内容 |
|---|---|
| `src/homework` | Service / Action 练习（car_client、car_service、move_to_target） |
| `src/lr_interfaces` | 自定义 srv / action 接口 |
| `src/niluo_node`、`src/student_node` | Topic 练习 |
| `src/vision`、`src/vision_core` | **视觉项目：白方块位姿估计**（本项目） |
| `config/camera_calib.yaml` | 相机内参（8×6 棋盘格标定结果） |

---

# 视觉项目：已知尺寸目标的 6 自由度位姿估计

用单目相机识别一张尺寸已知的白色方形标定板，解出它在相机坐标系下的位姿，稳定跑在 20Hz，并用 launch / rqt / tf2 / rviz2 / ros2 bag / ros2 doctor 补齐启动、可视化、记录、回放、排查能力。算法全部为传统视觉方法，没有用深度学习。

## 一、包结构

```
src/
├── vision_core/          纯算法库，不依赖 ROS
│   ├── include/vision_core/square_detector.hpp   Params / Result / Diagnostics
│   └── src/square_detector.cpp                   白度分割 + 四边形拟合 + PnP + One Euro
└── vision/               ROS 节点与启动文件
    ├── src/view.cpp      订阅图像 → 调 detector → 发布位姿与调试图
    └── launch/vision.launch.py
```

**为什么拆两个包**：算法层不 include 任何 `rclcpp`，可以脱离 ROS 单独跑。本项目的阈值调参就是写了个独立小程序直接读图片、打印白度分布和最大连通域面积，不用起节点、不用插相机、不用 `colcon build`。如果全塞进一个节点，每改一次阈值都要重编译，调参效率差一个量级。节点层保持很薄（250 行），只做三件事：`ROS msg → cv::Mat`、`detector.detect()`、`发结果`。

`Diagnostics` 结构体是调试时加的：记录面积、四边形、长宽比、凸性、角点、PnP、重投影、贴边每一道门槛各挡掉了几个候选。作用是「框不出来时能一句话说清是哪一步挡的」，不用凭感觉猜阈值。

## 二、算法链路

### 1. 白度图：用 min(B,G,R) 而不是 HSV 的 V

HSV 的 V 就是 `max(R,G,B)`，一根红色灯管的 V 也是 255，判不出「白」。真正的白是**又亮又没颜色**：

```cpp
cv::min(ch[0], ch[1], w);   // w = min(B,G,R)
cv::min(w, ch[2], w);
double otsu = cv::threshold(w, tmp, 0, 255, THRESH_BINARY | THRESH_OTSU);
int thr = std::clamp((int)otsu, white_min, white_max);   // Otsu 自动定阈，再夹在上下限内
```

`min(B,G,R)` 的物理含义接近「这个像素离灰色有多近」：纯白三通道都高，min 就高；纯红只有一个通道高，min 被拉低。

### 2. 饱和度闸门 —— 这一步是转折点

只靠亮度时，白纸和木桌高光**连成一整块**。实测：白纸 min≈228~244、S=0~4；木桌高光 min=239（亮度几乎一样）但 S=11。两者粘成一个 81476 像素的连通域，外接框横跨 626×362 还贴边，`approxPolyDP` 只能拟出 8~10 个顶点，不是四边形，直接判失败。

加上 `S <= sat_max`（默认 25）后，同一帧：白色占比 29.6%→10.6%，最大连通域 81476→5469 像素，独立、4 顶点、凸、长宽比 0.93，候选数 0→1。

> 教训：调参调不出来时，先怀疑**判据选错了**，而不是阈值没调对。在 `white_min` 上试 90/100/120 全都失败，因为问题不在「多亮算白」。

### 3. 候选筛选五道闸

| 门槛 | 条件 | 挡住什么 |
|---|---|---|
| 面积 | `min_area < area < 40% 画面` | 噪点、整片墙 |
| 四边形 | `approxPolyDP` 后 4 顶点且凸 | 不规则反光块 |
| 长宽比 | 0.6 ~ 1.6 | 细长条（桌沿、灯管） |
| 角点偏差 | 内角与 90° 平均偏差 < 20° | 歪斜梯形 |
| 贴边 | 外接框距边缘 > 2px | 被画面切掉的目标 |

贴边这道闸是后期加的：目标太近被画面切掉时，`approxPolyDP` 会把**图像边界当成方块的边**，算出的位姿数值平稳、不报错，但物理上是错的——这种「稳定地错」最危险。

### 4. 位姿与平滑

`solvePnP`(ITERATIVE + IPPE 双解取重投影误差小的)，再过跳变门限（单帧位移超 `max_track_dist` 判为错解丢弃），最后进 One Euro 滤波。选 One Euro 而非普通低通，因为它速度自适应：静止时截止频率低（抖动压得死），快速移动时频率随速度升高（不拖影）。

## 三、编译与运行

```bash
mkdir -p task2_ws/src && cd task2_ws/src
# 把本仓库的 src/vision、src/vision_core、config/ 拷进来
cd .. && colcon build --packages-select vision_core vision
source install/setup.bash
```

启动前先锁相机曝光，否则自动曝光会把曝光时间拉到 160ms，帧率掉到 6Hz：

```bash
v4l2-ctl -d /dev/video0 -c auto_exposure=1 -c exposure_time_absolute=300
```

```bash
ros2 launch vision vision.launch.py
# 另开终端看调试图
ros2 run rqt_image_view rqt_image_view /debug_image/compressed
```

> launch 里 `camera_info_url` 默认写的是 `file:///home/an/ros2_learning/task2_ws/config/camera_calib.yaml`，换机器要改成自己的绝对路径。标定文件没加载时节点会用近似内参先跑，并在调试图上标 `NO CALIB`，不会静默不动。

## 四、参数表（全部可从 launch 覆盖，无一处写死）

| 参数 | 默认 | 说明 |
|---|---|---|
| `video_device` | `/dev/video0` | 插拔后编号可能变 |
| `pixel_format` | `yuyv2rgb` | **不要用 mjpeg2rgb**，这台相机会让 usb_cam 抛异常退出 |
| `image_width` / `image_height` | 640 / 480 | 必须和标定文件一致 |
| `framerate` | 20.0 | |
| `white_min` | 100 | 白度下限，整块识别不出就往小调 90/80/70 |
| `white_max` | 165 | 白度阈值封顶，框不住调小 150，框住整面桌调大 180 |
| `sat_max` | 25 | 饱和度上限，框住木桌/纸箱调小 15，暖光偏黄调大 40 |
| `min_area` | 500 | 目标远、框不出时调小 |
| `max_reproj` | 6.0 | 重投影误差上限，调大能多检出但假解变多 |
| `max_track_dist` | 200.0 | 跟随允许的单帧最大位移，快挥时跟丢就调大 |
| `smooth_min_cutoff` | 1.6 | 静止时截止频率，越大越跟手 |
| `smooth_beta` | 0.02 | 速度增益 |
| `debug_every` | 2 | 调试图隔帧发布（2=10Hz） |

```bash
ros2 launch vision vision.launch.py sat_max:=15          # 框住了木桌
ros2 launch vision vision.launch.py white_min:=90        # 环境偏暗
ros2 launch vision vision.launch.py smooth_min_cutoff:=2.5  # 抖动明显
```

两个坑：数值参数必须 `ParameterValue(..., value_type=float)`，否则传成字符串会让 usb_cam 报 invalid type；话题名要 remap 两边一起改，不能只改一端。

## 五、话题

| 话题 | 类型 | 说明 |
|---|---|---|
| `/camera/image_raw` | `sensor_msgs/Image` | 相机输入 |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | 内参 |
| `/target_pose_camera` | `geometry_msgs/PoseStamped` | 目标位姿（相机光学系） |
| `/debug_image` | `sensor_msgs/Image` | 调试图（原始） |
| `/debug_image/compressed` | `sensor_msgs/CompressedImage` | 调试图（JPEG，推荐） |

调试图为什么要单独发 JPEG：640×480 原始图 900KB，20Hz 就是 18MB/s，会把 DDS 吃满、输入帧率被削到 12Hz。JPEG 一张 60KB，小 15 倍，才能和 20Hz 共存。

## 六、验证

```bash
rqt_graph                                                    # 数据流无断点
ros2 topic echo /camera/camera_info                          # 确认标定已加载（看 K）
ros2 run tf2_tools view_frames                               # TF 树，生成 frames.pdf
ros2 run tf2_ros tf2_echo base_link default_cam              # 确认平移与旋转
ros2 bag record -o vision_case /camera/image_raw /camera/camera_info
ros2 bag play vision_case --rate 0.5                         # 回放复现
ros2 doctor                                                  # 环境检查
```

静态 TF 的 child 必须写 `default_cam`，因为 usb_cam 用 `camera_name` 当 frame_id：

```bash
ros2 run tf2_ros static_transform_publisher \
  --x 0.2 --y 0.0 --z 0.3 \
  --roll -1.5708 --pitch 0.0 --yaw -1.5708 \
  --frame-id base_link --child-frame-id default_cam
```

`-90°/-90°` 必须有：`solvePnP` 结果在光学坐标系（z 朝前），ROS 习惯 z 朝上。只写平移不写旋转，tf2 不报错，但方块会被算到头顶而不是前方——项目里最隐蔽的坑。

## 七、实测指标

| 指标 | 值 |
|---|---|
| 输入帧率 | 20.0Hz（关闭 rviz2 时） |
| 单帧耗时 | 4.4ms（预算 50ms） |
| 静止位姿抖动 | x sd 0.15mm / y sd 0.12mm / z sd 0.61mm |
| 单帧最大位移 | 1.1mm |
| 测距 | 桌面白纸 z=0.595m，与卷尺一致 |

注意：rviz2 在虚拟机里走软件渲染，占 179% CPU（4 核机器），开着它时相机链路掉到 6~7Hz。所以 20Hz 必须在关掉 rviz 时测，两个数字不能混着讲。

## 八、待改进

1. 目标物换成**带缺口的彩色矩形**。当前是无标记白卡，四角完全对称，位姿朝向有 **4 重歧义**（翻转 90° 同样是合法解），缺口正是用来打破这个对称的。
2. 加 `tf2_ros::Buffer` + `TransformListener`，输出 `/target_pose_base`，真正给出「机器人坐标系下」的位姿（目前只有相机系）。
3. bag 补录 `/target_pose_camera`、`/tf`、`/tf_static`，否则回放只能复现「看到什么」、复现不了「算出了什么」。
4. rviz2 的 Fixed Frame 改 `base_link` 并存成 `.rviz` 配置文件（默认 `map` 在这棵树里不存在，会让所有坐标系塌在原点）。
5. 相机画面横置 90°，检测不受影响，但 rviz 里姿态会差 90°，等机械结构固定后校正。
