# Optional OpenMV IDE benchmark: no VCP image stream and no ROS dependency.
# Run in OpenMV IDE and watch the bottom Serial Terminal, not the ROS terminal.

import csi
import time

print("benchmark_start: initializing camera; serial output is working")

cam = csi.CSI()
cam.reset()
cam.pixformat(csi.JPEG)
cam.framesize(csi.QVGA)
cam.quality(80)
cam.framerate(20)
cam.framebuffers(1)
cam.snapshot(time=2000)  # Let exposure, gain and white balance settle.

print("camera_ready: reporting measured capture FPS once per second")
frame_count = 0
last_report_ms = time.ticks_ms()
last_bytes = 0

while True:
    image = cam.snapshot()
    if image is None:
        time.sleep_ms(10)
        continue

    last_bytes = len(image.bytearray())
    frame_count += 1
    now_ms = time.ticks_ms()
    elapsed_ms = time.ticks_diff(now_ms, last_report_ms)
    if elapsed_ms >= 1000:
        measured_fps = frame_count * 1000.0 / elapsed_ms
        print("capture_loop_fps=%.2f jpeg_bytes=%d" % (measured_fps, last_bytes))
        frame_count = 0
        last_report_ms = now_ms
