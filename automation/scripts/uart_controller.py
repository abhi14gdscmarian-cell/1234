"""UART engine.

A background thread reads the serial port continuously, so no byte is lost while the
test logic is waiting. All received text is appended to a buffer; the waiting functions
search the buffer from a cursor and advance it past each match, so every event is
consumed exactly once and a marker from an earlier test can never satisfy a later one.
"""
import re
import threading
import time


class UARTError(Exception):
    pass


class UARTTimeout(UARTError):
    pass


class UARTFailMarker(UARTError):
    pass


class UARTController:
    def __init__(self, transport, logger, send_newline=False):
        self.ser = transport
        self.log = logger
        self.send_newline = send_newline
        self._buf = ""
        self._cursor = 0
        self._cv = threading.Condition()
        self._partial = ""
        self._stop = False
        self._error = None
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    # ---------------- reader thread ----------------
    def _reader(self):
        last_rx = time.monotonic()
        try:
            while not self._stop:
                data = self.ser.read(self.ser.in_waiting or 1)
                if not data:
                    if self._partial.strip() and time.monotonic() - last_rx > 0.5:
                        self.flush_pending_log()
                    continue
                last_rx = time.monotonic()
                text = data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
                self._log_lines(text)
                with self._cv:
                    self._buf += text
                    self._cv.notify_all()
        except Exception as exc:  # port unplugged etc.
            with self._cv:
                self._error = exc
                self._cv.notify_all()

    def _log_lines(self, text):
        self._partial += text
        while "\n" in self._partial:
            line, self._partial = self._partial.split("\n", 1)
            if line.strip():
                self.log.uart(line)

    # ---------------- helpers ----------------
    def flush_pending_log(self):
        if self._partial.strip():
            self.log.uart(self._partial)
        self._partial = ""

    def discard_unread(self):
        """Move the cursor to the end of the buffer (ignore everything received so far)."""
        with self._cv:
            self._cursor = len(self._buf)

    def send(self, text):
        payload = text + ("\r\n" if self.send_newline else "")
        self.ser.write(payload.encode("utf-8"))
        try:
            self.ser.flush()
        except Exception:
            pass
        self.log.tx(f"sent {text!r}")

    def wait_for(self, pattern, timeout, fail_pattern=None, abort_patterns=None, what=None):
        """Wait for regex `pattern` after the cursor.

        fail_pattern  -> raises UARTFailMarker if it appears first
        abort_patterns-> dict name->regex; raises UARTFailMarker naming the unexpected event
        Returns the text from the old cursor up to and including the match.
        """
        what = what or pattern
        rx = re.compile(pattern, re.S)
        frx = re.compile(fail_pattern, re.S) if fail_pattern else None
        arx = {k: re.compile(v, re.S) for k, v in (abort_patterns or {}).items()}
        deadline = time.monotonic() + timeout
        with self._cv:
            while True:
                if self._error:
                    raise UARTError(f"serial port error: {self._error}")
                seg = self._buf[self._cursor:]
                m = rx.search(seg)
                fm = frx.search(seg) if frx else None
                # whichever happens first in the stream wins
                if m and (not fm or m.start() <= fm.start()):
                    self._cursor += m.end()
                    return seg[:m.end()]
                if fm:
                    self._cursor += fm.end()
                    raise UARTFailMarker(f"failure marker seen while waiting for {what!r}: {fm.group(0)!r}")
                for name, a in arx.items():
                    am = a.search(seg)
                    if am:
                        raise UARTFailMarker(f"unexpected event '{name}' while waiting for {what!r}")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise UARTTimeout(f"timeout after {timeout}s waiting for {what!r}")
                self._cv.wait(timeout=min(remaining, 1.0))

    def close(self):
        self._stop = True
        self._thread.join(timeout=3)
        self.flush_pending_log()
        try:
            self.ser.close()
        except Exception:
            pass
