# PnP 与 TF 坐标假设（v0.4.0 起，适用于 v1.0.0）

## 1. 验证状态

用户已现场确认默认 `assumed_static` 模式的实时有效 PnP、基坐标位姿和滤波输出，并完成标准 bag 重算回放；这不等于数值精度已经验收。v1.0.0 相对该现场验收基线只更新版本与交付文档。外部动态 TF 接口通过软件级测试和静态检查，但尚未在真实机器人动态 TF 或 external 动态 bag 回放中验证。真实标定内参已加载且 `K` 非零，但用户未提供 RMS 重投影误差，因此标定精度仍未评价。

## 2. 坐标系

| 坐标系 | 约定 |
|---|---|
| `base_link` | 机器人根坐标系；x 向前、y 向左、z 向上 |
| `camera_optical_frame` | 相机光学坐标系；x 向图像右方、y 向图像下方、z 沿光轴向前 |
| `target` | 目标中心；x/y 沿正方形两边，z=0 为靶面，+z 背离当前可见正面 |

目标没有缺口且正反面相同，因此目标 x/y 轴的起始编号是人为约定。正方形旋转 90° 或翻面后可能得到等价外观，当前输出是**一种等价 6DoF 姿态**，不是唯一物理方向。

## 3. 安装外参的两种模式

`config/pose.yaml` 新增 `mount_tf_mode`，只允许以下两个值：

| 模式 | 行为 |
|---|---|
| `assumed_static`（默认） | 本包发布下述假设的 `base_link → camera_optical_frame` 静态 TF，保持此前配置不变 |
| `external` | 本包不发布安装 TF，按每张图像的时间戳查询机器人提供的 `base_link → camera_optical_frame` |

默认假设静态变换为：

```text
base_link → camera_optical_frame
平移（米）：[0.20, 0.00, 0.10]
RPY（度）：[-90, 0, -90]
四元数 xyzw：[0.5, -0.5, -0.5, 0.5]
```

物理含义：相机光学原点位于 `base_link` 原点前方 20 cm、上方 10 cm，横向无偏移；光学 z 轴朝机器人前方，光学 x 轴朝机器人右方，光学 y 轴朝下。

对应旋转矩阵为：

```text
R_base_camera = [ 0  0  1 ]
                [-1  0  0 ]
                [ 0 -1  0 ]
```

**这些数值全部是假设，不是实测安装外参。**默认模式下，`/camera/target_pose_base` 和 RViz2 中相对 `base_link` 的位置只能用于链路联调，不能当作真实机器人上的准确测量值。修改假设安装平移/RPY 后需重启位姿节点，使静态 TF 重新发布。

使用真实或外部安装关系时，在 `config/pose.yaml` 设置：

```yaml
mount_tf_mode: "external"
```

机器人侧必须提前提供 `base_link → camera_optical_frame`，frame 名与 `pose.yaml` 完全一致，TF 时间范围必须覆盖图像时间戳。external 模式忽略上述假设平移和 RPY；安装模式不能在线切换，必须修改 YAML 并重启，避免旧的假设静态 TF 残留。`/camera/pose/stats` 中的 `mount_tf_mode` 和 `mount_is_assumed` 可用于核对当前来源。

## 4. PnP 模型与候选筛选

- `target_size_m` 默认 `0.099`，使用 50 mm 目标时必须改成 `0.050`；尺寸填错会使距离按比例出错。
- 模型点以目标中心为原点、单位为米，四个顶点与图像顶点按相同循环顺序对应。
- 使用 `solvePnPGeneric + SOLVEPNP_IPPE`，不是一般矩形的 `IPPE_SQUARE` 模板调用。
- 候选依次检查所有模型点正深度、可见面约定和重投影 RMS 误差；默认误差上限 8 px。
- 有同一跟踪 ID 的近期上一位姿时先比较旋转连续性，再比较重投影误差；这只是平面候选选择，不是位置/姿态滤波。
- `planar_ambiguous:true` 表示仍存在误差接近的平面候选，需要结合时序滤波和实验复核。
- v0.6.0 支持多个检测目标的图像空间 ID 关联，但 PnP 仍只选择面积最大的已确认目标，不为每个目标分别发布 6DoF。

## 5. 时间戳与 TF 树

```text
base_link
  └── camera_optical_frame    （假设静态或外部提供）
        └── target            （有效 PnP 时按图像时刻发布）
```

节点严格按以下关系计算：

```text
T_base_target(t_image) = T_base_camera_optical(t_image) × T_camera_optical_target(t_image)
```

`target_pose_camera`、`target_pose_base` 和动态 `target` TF 使用正方形图像的原始时间戳。TF 查询也使用该图像时刻，而不是查询“最新”变换。无目标、遮挡、CameraInfo 无效、PnP 无有效候选或 TF 查询失败时，只发布 `/camera/pose/stats` 的失败原因，不发布新位姿，也不重发旧 TF 伪装 20 FPS。

live external 模式已支持相机相对机器人的动态安装关系：外部 TF 缺失、frame 名不一致或时间外推时会报告 `tf_lookup_failed`，不会退回“最新 TF”掩盖时间对齐问题。真实动态相机、机器人时钟与图像时间戳对齐仍须现场验收。

**动态回放限制**：现有 bag 的 `/tf` 同时包含机器人 TF 和本包生成的 `target/target_filtered`。不能在 external 重算回放时简单把 `/tf` 加入 `ros2 bag play --topics`，否则会重复发布目标 TF。标准 replay 继续使用 `assumed_static`，只播放图像和 CameraInfo；external 动态回放必须单独准备不含旧目标 frame 的安装 TF 记录，或提供经过滤的 TF 源，该流程尚未现场验收。

## 6. 现场检查

```bash
ros2 topic echo --once /camera/tracking/stats
ros2 topic echo --once /camera/pose/stats
ros2 topic echo --once /camera/target_pose_camera
ros2 topic echo --once /camera/target_pose_base
ros2 run tf2_ros tf2_echo base_link camera_optical_frame
ros2 run tf2_ros tf2_echo camera_optical_frame target
```

正常时 `pose/stats` 包含 `valid:true`、`reason:ok`、`selected_track_id`、正深度、重投影误差和两套坐标系下的位置/四元数。默认模式应有 `mount_tf_mode:"assumed_static"`、`mount_is_assumed:true`；external 模式应分别为 `"external"` 和 `false`。live/replay 添加 `rviz:=true` 后会自动加载 Fixed Frame 为 `base_link` 的配置，应看到上述坐标关系和 `target_filtered`。

v0.5.0 已新增 One Euro 位置滤波、四元数 SLERP、`/camera/target_pose_filtered`、`/camera/filter/stats` 和 `base_link → target_filtered` TF；v0.6.0 新增跨帧 ID 与遮挡状态；v0.7.0 新增统一 replay launch；v0.8.0 新增真实边长 Marker 和 RViz 配置；v0.9.0 新增外部动态安装 TF 接口。原始 PnP 位姿与 `camera_optical_frame → target` 保持未滤波，便于对照。标准重新计算回放只播放图像和 CameraInfo，旧 TF 不播放，由当前节点按默认假设外参重新生成。真实动态 TF、external 动态回放和精度验收仍未完成，不能从软件测试或有效输出推断这些项目已经通过。
