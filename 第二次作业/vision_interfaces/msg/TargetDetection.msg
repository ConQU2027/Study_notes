std_msgs/Header header
# 四个角点，图像平面像素坐标 (u, v, 0)，已按缺口归一化排序
geometry_msgs/Point32[4] corners
# 缺口所在边索引 0..3，表示 corners[i] -> corners[(i+1)%4] 之间的边
int32 notch_edge
# 检测置信度 0.0 ~ 1.0
float32 confidence
