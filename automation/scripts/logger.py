"""Thread-safe logger: writes every line to the console (Jenkins) and to a per-RTL text file."""
import sys
import threading
from datetime import datetime
from pathlib import Path


class RunLogger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "w", encoding="utf-8", newline="\n")
        self._lock = threading.Lock()

    @staticmethod
    def _ts():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _emit(self, tag, text):
        line = f"[{self._ts()}] {tag} {text}"
        with self._lock:
            self._fh.write(line + "\n")
            self._fh.flush()
            try:
                print(line, flush=True)
            except UnicodeEncodeError:
                print(line.encode("ascii", "replace").decode(), flush=True)

    def info(self, text):
        self._emit("[INFO]", text)

    def error(self, text):
        self._emit("[ERROR]", text)

    def uart(self, text):
        self._emit("[UART]", text)

    def tx(self, text):
        self._emit("[TX  ]", text)

    def banner(self, text):
        bar = "=" * 70
        for line in (bar, text, bar):
            self._emit("[INFO]", line)

    def close(self):
        with self._lock:
            self._fh.close()
