#ifndef VISION_CORE__SQUARE_DETECTOR_HPP_
#define VISION_CORE__SQUARE_DETECTOR_HPP_

#include <opencv2/opencv.hpp>
#include <cmath>
#include <vector>

namespace vision_core
{

// 检测参数：全部带默认值，运行时可以用 launch 参数覆盖，不用改代码。
struct Params
{
    // --- 白色分割 ---
    // 白度 = min(B,G,R)。白纸三个通道都亮，彩色物体总有一路明显偏暗，
    // 所以它比 HSV 的固定阈值(S<30, V>200)耐用得多：
    // 室内暖光下白纸的 S 经常到 40~70、V 只有 180 左右，固定阈值会整片漏掉。
    int white_min = 100;           // 白度下限(0~255)，环境偏暗就调小
    // 上限压住"窗外/白墙过曝区把 Otsu 抬太高"。实测这间屋子 Otsu 会落到 152~183，
    // 而暖光下白纸的白度只有 150~175，阈值一旦过 180 白块就被整块切掉 -> cand=0。
    // 所以默认压到 165：够白块进来的同时，蓝绿桌面(白度~130)仍在阈值下面。
    int white_max = 165;           // 白度上限；框不住白块调小(150)，框住整片桌面调大(180)
    // 饱和度上限：白纸/白板几乎没有颜色(S≈0~10)，而木桌、纸箱、米色托盘 S 常在 60 以上。
    // 只用亮度分不开它们——木头高光和白墙反光一样很亮，会把白块和背景连成一整块。
    int sat_max = 25;              // 框住一堆有色物体就调小(15)，白块在暖光下偏黄就调大(35)
    double min_area = 500.0;       // 最小面积(像素)，太小的是噪点
    double approx_eps = 0.03;      // 多边形逼近精度(占周长比例)
    double max_area_ratio = 0.60;  // 最大面积占全图比例，挡掉整片桌面
    double min_ratio = 0.65;       // 外接矩形长宽比下限
    double max_ratio = 1.55;       // 上限；正方形≈1，斜着看会偏离
    double max_corner_dev = 35.0;  // 内角与 90° 的最大偏差(度)

    // --- 位姿筛选 ---
    double min_z = 0.05;           // 最近距离(米)
    double max_z = 3.0;            // 最远距离(米)
    double max_reproj = 6.0;       // 重投影误差上限(像素)，挡掉发散的假解

    // --- 跟随 ---
    double max_track_dist = 200.0; // 目标中心一帧最多移动多少像素
    int lost_frames = 6;           // 连续丢这么多帧才解除锁定

    // --- 平滑：One Euro 自适应滤波 ---
    double jump_max = 0.35;        // 单帧最大位移(米)，超过算跳变
    double jump_max_angle = 0.6;   // 单帧最大转角(弧度)，超过算跳变
    double min_cutoff = 1.6;       // 静止截止频率(Hz)，越小越稳
    double beta = 0.02;            // 速度增益，越大动起来越跟手
};

// 每帧的诊断计数：cand=0 时靠它判断卡在哪一道门槛上，现场调参就看这几个数。
// 只做统计，不参与任何判断，所以加它不会改变检测行为。
struct Diag
{
    double white_ratio = 0.0;  // 白色掩膜占全图比例；接近 0 = 阈值太高或画面全黑
    int contours = 0;          // 掩膜里轮廓总数
    int max_cnt_area = 0;      // 最大轮廓面积(像素)：目标到底有没有被分割出来
    int rej_area = 0;          // 面积太小/太大
    int rej_edge = 0;          // 贴着画面边缘(目标被切掉了，解出来的位姿一定是错的)
    int rej_approx = 0;        // 不是四边形
    int rej_convex = 0;        // 不是凸四边形
    int rej_ratio = 0;         // 长宽比超出 0.65~1.55
    int rej_corner = 0;        // 内角与 90° 偏差过大(斜看太厉害)
    int rej_pnp = 0;           // solvePnP 失败
    int rej_z = 0;             // 解出的距离离谱
    int rej_reproj = 0;        // 重投影误差过大(解算不自洽)
};

// 一帧的检测结果
struct Result
{
    bool found = false;             // 这一帧有没有锁定到目标
    cv::Mat rvec;                   // 旋转向量 3x1，相机坐标系
    cv::Mat tvec;                   // 平移向量 3x1，单位米，相机坐标系
    cv::Point2f center;             // 目标在图像上的中心(像素)
    std::vector<cv::Point2f> quad;  // 目标四边形的 4 个角点，画框用
    bool tracking = false;          // 是否已处于"锁定跟随"状态
    int candidates = 0;             // 本帧通过筛选的候选数，调参时可看
};

// 一维 One Euro 滤波器
// 普通低通的系数是固定的：系数大就抖，系数小就慢，二者不可兼得。
// One Euro 按速度改系数：目标静止 -> 强滤波(不抖)；快速移动 -> 弱滤波(不延迟)。
class OneEuro
{
public:
    OneEuro() = default;
    OneEuro(double min_cutoff, double beta) : mc_(min_cutoff), beta_(beta) {}

    void reset() {init_ = false;}

    double filter(double x, double dt)
    {
        if (dt < 1e-4) {dt = 1e-3;}                    // 时间戳异常时保护
        if (!init_) {init_ = true; xp_ = x; return x;}
        double dx = (x - xp_) / dt;                    // 速度估计
        dxp_ += alpha(1.0, dt) * (dx - dxp_);          // 速度本身也低通，抗噪
        xp_ += alpha(mc_ + beta_ * std::fabs(dxp_), dt) * (x - xp_);
        return xp_;
    }

private:
    // 一阶低通里"截止频率 -> 新值权重"的换算
    static double alpha(double cutoff, double dt)
    {
        return 1.0 / (1.0 + 1.0 / (2.0 * 3.14159265358979 * cutoff) / dt);
    }

    double mc_ = 1.6, beta_ = 0.02, xp_ = 0.0, dxp_ = 0.0;
    bool init_ = false;
};

// 白方块检测器：只做算法，不依赖 ROS，可以单独编译、单独测试。
class SquareDetector
{
public:
    explicit SquareDetector(const Params & params = Params());

    // 处理一帧 BGR 图像。K/D 是相机内参矩阵和畸变系数，来自 camera_info。
    // dt：与上一帧的时间间隔(秒)，One Euro 靠它把"速度"算对。
    Result detect(const cv::Mat & bgr, const cv::Mat & K, const cv::Mat & D, double dt);

    // 清空跟随状态（目标被移走、想重新开始时调用）
    void reset();

    const Params & params() const {return params_;}
    int whiteThr() const {return white_thr_;}  // 本帧实际用的白度阈值，调参用
    const Diag & diag() const {return diag_;}  // 本帧各道门槛的淘汰计数

private:
    // 内部用：一个"候选目标"
    struct Candidate
    {
        std::vector<cv::Point2f> quad;  // 排好序的 4 个角点
        cv::Point2f center;             // 图像中心
        cv::Mat rvec;
        cv::Mat tvec;
        double area = 0.0;
    };

    Params params_;
    OneEuro pos_[3];        // x/y/z 各一个滤波器
    OneEuro rot_[3];        // 旋转向量三个分量各一个

    // 跟随状态
    bool has_target_ = false;            // 是否已锁定目标
    cv::Point2f last_center_{0.f, 0.f};  // 上一帧目标的图像中心
    int lost_cnt_ = 0;                   // 连续丢失帧数

    // 位姿跳变与平滑状态
    cv::Mat last_t_;
    cv::Mat last_rvec_;
    bool have_last_ = false;
    int jump_cnt_ = 0;                   // 连续跳变帧数
    int white_thr_ = 0;                  // 本帧白度阈值
    Diag diag_;                          // 本帧诊断计数
};

}  // namespace vision_core

#endif  // VISION_CORE__SQUARE_DETECTOR_HPP_
