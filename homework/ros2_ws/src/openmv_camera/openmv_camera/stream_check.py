"""Measure a real OpenMV stream without requiring ROS 2 or OpenCV."""

import argparse
import json
import time

import serial

from .protocol import FrameParser
from .serial_io import read_available


def check_stream(port: str, frame_goal: int, timeout_sec: float) -> dict:
    if frame_goal < 2:
        raise ValueError("frame_goal must be at least 2 for rate measurement")
    if timeout_sec <= 0:
        raise ValueError("timeout_sec must be positive")

    parser = FrameParser()
    frames = []
    batch_sizes = []
    error = None
    started = time.monotonic()
    try:
        with serial.Serial(port=port, baudrate=115200, timeout=0.2) as connection:
            connection.reset_input_buffer()
            while len(frames) < frame_goal:
                if time.monotonic() - started > timeout_sec:
                    raise TimeoutError(
                        f"Received {len(frames)}/{frame_goal} frames in {timeout_sec:.1f} s"
                    )
                parsed = parser.feed(read_available(connection, 16384))
                if parsed:
                    batch_sizes.append(len(parsed))
                    frames.extend(parsed[: frame_goal - len(frames)])
    except (TimeoutError, serial.SerialException, OSError) as exception:
        error = str(exception)

    wall_elapsed = time.monotonic() - started
    elapsed = (
        (frames[-1].complete_monotonic_ns - frames[0].complete_monotonic_ns) / 1e9
        if len(frames) >= 2 else 0.0
    )
    board_elapsed_ms = (
        (frames[-1].capture_ms - frames[0].capture_ms) & 0x3FFFFFFF
        if len(frames) >= 2 else 0
    )
    payload_bytes = sum(len(frame.jpeg) for frame in frames)
    interval_payload_bytes = sum(len(frame.jpeg) for frame in frames[1:])
    sequence_missing = 0
    for previous, current in zip(frames, frames[1:]):
        delta = (current.sequence - previous.sequence) & 0xFFFFFFFF
        if 1 < delta < 0x80000000:
            sequence_missing += delta - 1

    return {
        "success": error is None and len(frames) >= frame_goal,
        "error": error,
        "port": port,
        "frames_requested": frame_goal,
        "frames_received": len(frames),
        "wall_elapsed_sec": round(wall_elapsed, 6),
        "elapsed_host_sec": round(elapsed, 6),
        "received_fps_host": round((len(frames) - 1) / elapsed, 3) if elapsed > 0 else 0.0,
        "board_loop_fps": round(
            (len(frames) - 1) * 1000 / board_elapsed_ms, 3
        ) if board_elapsed_ms > 0 else 0.0,
        "jpeg_payload_bytes": payload_bytes,
        "interval_jpeg_payload_bytes": interval_payload_bytes,
        "jpeg_payload_mbit_per_sec": round(
            interval_payload_bytes * 8 / elapsed / 1e6, 3
        ) if elapsed > 0 else 0.0,
        "throughput_basis": "payload_of_frames_after_first_divided_by_interframe_elapsed",
        "mean_jpeg_bytes": round(payload_bytes / len(frames), 1) if frames else 0.0,
        "rx_batch_frames_max": max(batch_sizes, default=0),
        "rx_batch_frames_mean": round(
            sum(batch_sizes) / len(batch_sizes), 3
        ) if batch_sizes else 0.0,
        "sequence_missing": sequence_missing,
        "crc_errors": parser.counters.crc_errors,
        "invalid_headers": parser.counters.invalid_headers,
        "invalid_jpeg": parser.counters.invalid_jpeg,
        "resync_bytes": parser.counters.resync_bytes,
        "frame_timeouts": parser.counters.frame_timeouts,
        "note": "Short-interval measurement only; not a 10-minute stability result.",
    }


def main(args=None) -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--port", required=True, help="For example /dev/ttyACM0")
    cli.add_argument("--frames", type=int, default=100)
    cli.add_argument("--timeout", type=float, default=20.0)
    options = cli.parse_args(args=args)
    try:
        report = check_stream(options.port, options.frames, options.timeout)
    except ValueError as exception:
        cli.error(str(exception))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if report["success"] else 1)


if __name__ == "__main__":
    main()
