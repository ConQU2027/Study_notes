"""Serial reads that do not wait to fill a large batch buffer."""


def read_available(connection, max_chunk: int) -> bytes:
    """Read currently pending bytes, or wait for one byte when the port is idle.

    pyserial read(N) blocks until N bytes arrive or its timeout expires. Using
    in_waiting avoids turning a continuous low-latency stream into large bursts.
    """
    if max_chunk <= 0:
        raise ValueError("max_chunk must be positive")
    pending = connection.in_waiting
    return connection.read(min(max_chunk, pending) if pending else 1)
