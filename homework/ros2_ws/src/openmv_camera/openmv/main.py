# OpenMV Cam H7 Plus, firmware 5.0.0.
# Streams hardware-encoded JPEG frames over USB VCP; no text is printed to VCP.
# Disconnect OpenMV IDE before starting the ROS 2 host node.

import binascii
import csi
import omv
import pyb
import struct
import time

MAGIC = b"OMVJ"
TARGET_FPS = 20
JPEG_QUALITY = 80
SEND_TIMEOUT_MS = 200

# Fail loudly if this firmware's CRC32 is not compatible with host zlib.crc32.
assert binascii.crc32(b"123456789") == 0xCBF43926, "CRC32/IEEE mismatch"

usb = pyb.USB_VCP()
# Required because arbitrary JPEG bytes include 0x03 (the default Ctrl-C).
# See README for stopping and recovery instructions before installing as main.py.
usb.setinterrupt(-1)

# Some firmware 5.0.0 builds do not expose omv.disable_fb. It is only an
# optional IDE-preview optimization, not a requirement for USB VCP streaming.
if hasattr(omv, "disable_fb"):
    omv.disable_fb(True)

cam = csi.CSI()
cam.reset()
cam.pixformat(csi.JPEG)
cam.framesize(csi.QVGA)
cam.quality(JPEG_QUALITY)
cam.framerate(TARGET_FPS)
cam.framebuffers(1)
cam.snapshot(time=2000)  # Let exposure, gain and white balance settle.

sequence = 0


def send_all(data):
    view = memoryview(data)
    offset = 0
    while offset < len(view):
        sent = usb.send(view[offset:], timeout=SEND_TIMEOUT_MS)
        if sent is None or sent <= 0:
            raise OSError("USB VCP send timeout")
        offset += sent


while True:
    if not usb.isconnected():
        time.sleep_ms(100)
        continue
    try:
        image = cam.snapshot()
        capture_ms = time.ticks_ms() & 0x3FFFFFFF
        payload = image.bytearray()
        header = struct.pack(
            "<4sIIHHII",
            MAGIC,
            sequence,
            capture_ms,
            image.width(),
            image.height(),
            len(payload),
            binascii.crc32(payload),
        )
        send_all(header)
        send_all(payload)
        sequence = (sequence + 1) & 0xFFFFFFFF
    except OSError:
        # A timeout can leave a partial frame in USB. The host discards it via
        # reconnect/resynchronization; no diagnostic text is mixed into VCP.
        time.sleep_ms(100)
