#include "vision_core/square_detector.hpp"

#include <algorithm>
#include <vector>

namespace vision_core
{
namespace
{

// 10cm×10cm 正方形模板，原点在中心，单位米。
// 顺序必须和 sortCorner 的结果一致：左上、右上、右下、左下。
const std::vector<cv::Point3f> kObjectPoints = {
  {-0.05f, 0.05f, 0.f}, {0.05f, 0.05f, 0.f},
  {0.05f, -0.05f, 0.f}, {-0.05f, -0.05f, 0.f}};

// 角点排序：左上、右上、右下、左下
std::vector<cv::Point2f> sortCorner(const std::vector<cv::Point2f> & pts)
{
  std::vector<double> sum(4), diff(4);
  for (int i = 0; i < 4; ++i) {
    sum[i] = pts[i].x + pts[i].y;
    diff[i] = pts[i].x - pts[i].y;
  }
  // 左上=和最小，右下=和最大，右上=差最小，左下=差最大
  std::vector<cv::Point2f> res(4);
  res[0] = pts[std::min_element(sum.begin(), sum.end()) - sum.begin()];
  res[1] = pts[std::min_element(diff.begin(), diff.end()) - diff.begin()];
  res[2] = pts[std::max_element(sum.begin(), sum.end()) - sum.begin()];
  res[3] = pts[std::max_element(diff.begin(), diff.end()) - diff.begin()];
  return res;
}

// 重投影误差：把 3D 模板按解出的位姿投影回图像，和实际角点差几个像素。
// 角点共线或畸变严重时 PnP 会发散（比如算出 471 米），这个值会突然变得很大。
double reprojError(
  const std::vector<cv::Point2f> & img_pts, const cv::Mat & K,
  const cv::Mat & D, const cv::Mat & rvec, const cv::Mat & tvec)
{
  std::vector<cv::Point2f> proj;
  cv::projectPoints(kObjectPoints, rvec, tvec, K, D, proj);
  double err = 0.0;
  for (int i = 0; i < 4; ++i) {err += cv::norm(proj[i] - img_pts[i]);}
  return err / 4.0;
}

// 四边形内角检查：正方形四个内角都该接近 90°，
// 被斜切一半的白纸、梯形桌沿在这里会被挡掉。
// 注意这是"图像上的角"，斜着看时透视会让内角偏离 90°，所以门槛给到 35°。
bool cornersRectLike(const std::vector<cv::Point2f> & q, double max_dev)
{
  for (int i = 0; i < 4; ++i) {
    cv::Point2f a = q[(i + 3) % 4] - q[i];  // 指向前一个角
    cv::Point2f b = q[(i + 1) % 4] - q[i];  // 指向后一个角
    double na = cv::norm(a), nb = cv::norm(b);
    if (na < 1e-3 || nb < 1e-3) {return false;}
    double cosv = std::clamp(static_cast<double>(a.dot(b)) / (na * nb), -1.0, 1.0);
    double deg = std::acos(cosv) * 180.0 / 3.14159265358979;
    if (std::fabs(deg - 90.0) > max_dev) {return false;}
  }
  return true;
}

// 白度图 + 自适应亮度阈值
// 白度 = min(B,G,R)，阈值每帧 Otsu 自适应，white_min/white_max 只做上下限兜底。
void whiteMask(const cv::Mat & bgr, int lo, int hi, int sat_max, cv::Mat & mask, int & used)
{
  cv::Mat ch[3], w, tmp, hsv, s_ch;
  cv::split(bgr, ch);
  cv::min(ch[0], ch[1], w);
  cv::min(w, ch[2], w);  // w = min(B,G,R)

  double otsu = cv::threshold(w, tmp, 0, 255, cv::THRESH_BINARY | cv::THRESH_OTSU);
  used = std::clamp(static_cast<int>(otsu), lo, hi);

  // 白色 = 够亮 且 几乎不带颜色。只靠亮度分不开：木桌高光、白墙反光一样很亮，
  // 会把白块和背景连成一整块，轮廓直接作废。白纸的 S 基本 0~10，木桌 60~110。
  cv::cvtColor(bgr, hsv, cv::COLOR_BGR2HSV);
  cv::extractChannel(hsv, s_ch, 1);
  cv::bitwise_and(w > used, s_ch <= sat_max, mask);

  cv::morphologyEx(mask, mask, cv::MORPH_OPEN, cv::getStructuringElement(cv::MORPH_RECT, {5, 5}));
  cv::morphologyEx(mask, mask, cv::MORPH_CLOSE, cv::getStructuringElement(cv::MORPH_RECT, {7, 7}));
}

}  // namespace

SquareDetector::SquareDetector(const Params & params)
: params_(params)
{
  for (int i = 0; i < 3; ++i) {
    pos_[i] = OneEuro(params_.min_cutoff, params_.beta);
    rot_[i] = OneEuro(params_.min_cutoff, params_.beta);
  }
}

void SquareDetector::reset()
{
  has_target_ = false;
  lost_cnt_ = 0;
  have_last_ = false;
  jump_cnt_ = 0;
  for (int i = 0; i < 3; ++i) {pos_[i].reset(); rot_[i].reset();}
}

Result SquareDetector::detect(
  const cv::Mat & bgr, const cv::Mat & K, const cv::Mat & D, double dt)
{
  Result out;
  diag_ = Diag();  // 诊断计数每帧清零

  // ---------- ① 把白色区域分割出来 ----------
  cv::Mat mask;
  whiteMask(bgr, params_.white_min, params_.white_max, params_.sat_max, mask, white_thr_);
  diag_.white_ratio = cv::countNonZero(mask) / static_cast<double>(mask.total());

  std::vector<std::vector<cv::Point>> contours;
  cv::findContours(mask, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
  diag_.contours = static_cast<int>(contours.size());

  // ---------- ② 收集本帧所有"像白方块"的候选 ----------
  // 不能"找到第一个就 break"：画面里有第二块白东西时每帧框到的不一样，看起来就是乱跳。
  // 每道 continue 顺手记一次数，cand=0 时直接看出卡在哪一步。
  std::vector<Candidate> cands;
  for (const auto & cnt : contours) {
    double area = cv::contourArea(cnt);
    diag_.max_cnt_area = std::max(diag_.max_cnt_area, static_cast<int>(area));
    // 贴边 = 目标被切掉一部分，approxPolyDP 会把图像边界当"角点"，位姿会稳定地错且看不出异常
    cv::Rect bb = cv::boundingRect(cnt);
    if (bb.x <= 2 || bb.y <= 2 || bb.br().x >= bgr.cols - 2 || bb.br().y >= bgr.rows - 2) {
      ++diag_.rej_edge; continue;
    }
    // 太小是噪点；太大是贴到镜头上了，解出来的位姿也没法用
    if (area < params_.min_area || area > params_.max_area_ratio * bgr.total()) {++diag_.rej_area; continue;}

    std::vector<cv::Point> approx;
    cv::approxPolyDP(cnt, approx, params_.approx_eps * cv::arcLength(cnt, true), true);
    if (approx.size() != 4) {++diag_.rej_approx; continue;}
    if (!cv::isContourConvex(approx)) {++diag_.rej_convex; continue;}

    // 长宽比：正方形≈1，挡掉桌沿、显示器这类长条
    cv::RotatedRect box = cv::minAreaRect(approx);
    double ratio = box.size.width / std::max(1e-6, static_cast<double>(box.size.height));
    if (ratio < params_.min_ratio || ratio > params_.max_ratio) {++diag_.rej_ratio; continue;}

    std::vector<cv::Point2f> pts2f;
    for (const auto & p : approx) {pts2f.emplace_back(static_cast<float>(p.x), static_cast<float>(p.y));}

    Candidate c;
    c.quad = sortCorner(pts2f);
    if (!cornersRectLike(c.quad, params_.max_corner_dev)) {
      ++diag_.rej_corner; continue;  // 内角不像 90°，不是正对着的方块
    }
    c.center = box.center;
    c.area = area;

    if (!cv::solvePnP(kObjectPoints, c.quad, K, D, c.rvec, c.tvec, false, cv::SOLVEPNP_ITERATIVE)) {
      ++diag_.rej_pnp; continue;
    }
    // 模板是 float 点，PnP 输出的 rvec/tvec 也会是 CV_32F。
    // 不统一转成 double，后面 at<double>() 会读错内存，位姿直接变垃圾值。
    c.rvec.convertTo(c.rvec, CV_64F);
    c.tvec.convertTo(c.tvec, CV_64F);

    double z = c.tvec.at<double>(2);
    if (z < params_.min_z || z > params_.max_z) {++diag_.rej_z; continue;}  // 距离离谱
    if (reprojError(c.quad, K, D, c.rvec, c.tvec) > params_.max_reproj) {
      ++diag_.rej_reproj; continue;  // 解算不自洽
    }

    cands.push_back(c);
  }

  out.candidates = static_cast<int>(cands.size());
  if (cands.empty()) {
    // 一个候选都没有 = 目标确实不在画面里，累计丢失帧数
    if (++lost_cnt_ >= params_.lost_frames) {
      has_target_ = false;
      lost_cnt_ = 0;
    }
    return out;
  }

  // ---------- ③ 在候选里挑出"本帧要跟的那一个" ----------
  int best = 0;
  if (has_target_) {
    // 已锁定：选离上一帧最近的那个，框就自然粘在同一个白块上
    double best_d = 1e9;
    for (size_t i = 0; i < cands.size(); ++i) {
      double d = cv::norm(cands[i].center - last_center_);
      if (d < best_d) {best_d = d; best = static_cast<int>(i);}
    }
    // 连最近的都离得很远 → 原来那块大概已经离开画面了。
    // 这一帧宁可不出结果，也不要去框别的白东西，否则又变成乱跳。
    if (best_d > params_.max_track_dist) {
      if (++lost_cnt_ >= params_.lost_frames) {
        has_target_ = false;
        lost_cnt_ = 0;
      }
      return out;
    }
  } else {
    // 还没锁定：选面积最大的，最可能是一整块目标而不是碎白点
    for (size_t i = 1; i < cands.size(); ++i) {
      if (cands[i].area > cands[best].area) {
        best = static_cast<int>(i);
      }
    }
  }

  // ---------- ④ 锁定成功，更新跟随状态 ----------
  Candidate & c = cands[best];
  bool was_tracking = has_target_;  // 记下这帧之前是否已锁定，用于显示 TRACK/SEARCH
  has_target_ = true;
  lost_cnt_ = 0;
  last_center_ = c.center;

  // ---------- ⑤ 位姿兜一层，再做自适应平滑 ----------
  if (have_last_) {
    // 位置或角度一帧内跳太多，先当噪声；连续 3 帧都跳才认为是真的动了
    bool jump = cv::norm(c.tvec - last_t_) > params_.jump_max ||
      cv::norm(c.rvec - last_rvec_) > params_.jump_max_angle;
    if (jump && ++jump_cnt_ < 3) {
      return out;
    }
    if (jump) {
      // 目标确实换了位置：把滤波器清空，让它从新位置重新起步，不要慢慢爬过去
      for (int i = 0; i < 3; ++i) {pos_[i].reset(); rot_[i].reset();}
    }
    jump_cnt_ = 0;  // 这一帧没跳就归零，否则跳变计数会越攒越大、后面一碰就算跳
    for (int i = 0; i < 3; ++i) {
      c.tvec.at<double>(i) = pos_[i].filter(c.tvec.at<double>(i), dt);
      c.rvec.at<double>(i) = rot_[i].filter(c.rvec.at<double>(i), dt);
    }
  }
  last_t_ = c.tvec.clone();
  last_rvec_ = c.rvec.clone();
  have_last_ = true;

  out.found = true;
  out.rvec = c.rvec.clone();
  out.tvec = c.tvec.clone();
  out.center = c.center;
  out.quad = c.quad;
  out.tracking = was_tracking;
  return out;
}

}  // namespace vision_core
