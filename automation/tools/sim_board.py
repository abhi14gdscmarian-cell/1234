"""Fake board (pyserial-like) whose firmware runs its tests automatically after reset().
Env: SIM_FAIL=RTL_JOB_2:UART_TEST   SIM_HANG=RTL_JOB_3:CLOCK_TEST   SIM_ORDER=RTL_JOB_1  (runs tests out of order)
     SIM_NO_COMPLETE=RTL_JOB_4  (never prints the final completion line)"""
import os, queue, threading, time

ORDER = ["SPI", "UART", "CLOCK"]


class SimSerial:
    def __init__(self, rtl_name, speed=0.05):
        self.rtl, self.speed = rtl_name, speed
        self._rx = queue.Queue()
        self._closed = False

    @property
    def in_waiting(self):
        return self._rx.qsize()

    def read(self, n=1):
        out = b""
        try:
            out += self._rx.get(timeout=0.1)
            while len(out) < n:
                out += self._rx.get_nowait()
        except queue.Empty:
            pass
        return out

    def write(self, data):
        pass

    def flush(self):
        pass

    def close(self):
        self._closed = True

    def _emit(self, text):
        for ch in text:
            self._rx.put(ch.encode())

    def reset(self):
        threading.Thread(target=self._firmware, daemon=True).start()

    def _firmware(self):
        self._emit("\r\nBOOT OK  clock config test firmware\r\n")
        order = list(reversed(ORDER)) if os.environ.get("SIM_ORDER") == self.rtl else ORDER
        for name in order:
            if self._closed:
                return
            key = f"{self.rtl}:{name}_TEST"
            self._emit(f"{name} TEST STARTED\r\n")
            time.sleep(self.speed)
            if os.environ.get("SIM_HANG") == key:
                return
            self._emit("progress 50%\r\n")
            time.sleep(self.speed)
            ok = os.environ.get("SIM_FAIL") != key
            self._emit(f"{name} TEST COMPLETED\r\nRESULT: {'PASS' if ok else 'FAIL'}\r\n")
        if os.environ.get("SIM_NO_COMPLETE") != self.rtl:
            self._emit("ALL TESTS COMPLETED\r\n")
