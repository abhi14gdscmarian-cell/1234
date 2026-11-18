"""Runs the RTL (.job) and firmware (.elf) programming commands from regression.json."""
import re
import subprocess
import time
from pathlib import Path


class FlashError(Exception):
    pass


def _run(command, timeout, success_regex, logger, description):
    logger.info(f"{description}: {command}")
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, errors="replace")
    lines = []
    deadline = time.monotonic() + timeout
    import threading

    def pump():
        for line in proc.stdout:
            line = line.rstrip()
            lines.append(line)
            logger.info(f"  | {line}")

    t = threading.Thread(target=pump, daemon=True)
    t.start()
    while t.is_alive():
        t.join(timeout=1)
        if time.monotonic() > deadline:
            proc.kill()
            raise FlashError(f"{description} timed out after {timeout}s")
    proc.wait()
    output = "\n".join(lines)
    if proc.returncode != 0:
        raise FlashError(f"{description} exited with code {proc.returncode}")
    if success_regex and not re.search(success_regex, output, re.I):
        raise FlashError(f"{description}: exit code 0 but success text /{success_regex}/ not found in tool output")
    logger.info(f"{description}: OK")


def _with_retries(fn, retries, logger, description):
    last = None
    for attempt in range(1, retries + 2):
        try:
            return fn()
        except FlashError as exc:
            last = exc
            logger.error(f"{description} attempt {attempt} failed: {exc}")
            time.sleep(3)
    raise last


def flash_rtl(job_file, flash_cfg, logger):
    job = Path(job_file).resolve()
    if not job.is_file():
        raise FlashError(f"RTL job file not found: {job}")
    cmd = flash_cfg["rtl_command"].replace("{rtl_job}", str(job))
    _with_retries(lambda: _run(cmd, flash_cfg.get("rtl_timeout_s", 900), flash_cfg.get("rtl_success_regex"),
                               logger, "RTL programming"),
                  flash_cfg.get("retries", 1), logger, "RTL programming")
    time.sleep(flash_cfg.get("settle_after_flash_s", 3))


def flash_firmware(elf_file, flash_cfg, logger):
    elf = Path(elf_file).resolve()
    if not elf.is_file():
        raise FlashError(f"firmware ELF not found: {elf}")
    cmd = flash_cfg["elf_command"].replace("{elf}", str(elf).replace("\\", "/"))
    _with_retries(lambda: _run(cmd, flash_cfg.get("elf_timeout_s", 600), flash_cfg.get("elf_success_regex"),
                               logger, "Firmware programming"),
                  flash_cfg.get("retries", 1), logger, "Firmware programming")
