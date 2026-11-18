"""Hardware regression orchestrator.

For each enabled RTL job (with ITS OWN firmware ELF):
  clean -> open UART -> flash RTL -> flash that RTL's ELF -> firmware runs its tests by itself ->
  capture UART until every expected step passed in order and the completion marker appears ->
  save + print the UART log -> next RTL job.
The next job is only programmed if the current one fully passed (unless continue_on_failure).

Usage:
  python automation/scripts/regression_controller.py
  python automation/scripts/regression_controller.py --only RTL_JOB_2
  python automation/scripts/regression_controller.py --simulate --config automation/tools/sim_regression.json --tests automation/tools/sim_test_expectations.json
"""
import argparse
import glob
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from flash_controller import FlashError, flash_firmware, flash_rtl  # noqa: E402
from logger import RunLogger  # noqa: E402
from test_validator import validate_run  # noqa: E402
from uart_controller import UARTController, UARTError  # noqa: E402


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def clean_generated(patterns, logger):
    logger.info("Cleaning generated outputs (RTL .job files and the ELF are never touched)")
    for pattern in patterns:
        for p in glob.glob(pattern):
            path = Path(p)
            if path.suffix.lower() in (".job", ".elf"):
                continue
            try:
                shutil.rmtree(path) if path.is_dir() else path.unlink()
                logger.info(f"  removed {p}")
            except OSError as exc:
                logger.error(f"  could not remove {p}: {exc}")


def open_transport(cfg_uart, rtl_name, simulate):
    if simulate:
        from sim_board import SimSerial
        return SimSerial(rtl_name)
    import serial
    return serial.Serial(port=os.environ.get("UART_PORT", cfg_uart["port"]), baudrate=cfg_uart["baudrate"],
                         bytesize=cfg_uart.get("bytesize", 8), parity=cfg_uart.get("parity", "N"),
                         stopbits=cfg_uart.get("stopbits", 1), timeout=0.2)


def run_configuration(item, cfg, exp, simulate, log_dir):
    name = item["name"]
    elf = item["elf"]
    res = {"name": name, "rtl_job": item["rtl_job"], "elf": elf,
           "elf_sha256": sha256(elf) if Path(elf).is_file() else "MISSING",
           "rtl_flash": "NOT RUN", "elf_flash": "NOT RUN",
           "tests": [], "status": "FAIL", "reason": "", "log": f"{name}.txt", "seconds": 0.0,
           "started": datetime.now().isoformat(timespec="seconds")}
    log_path = Path(log_dir) / f"{name}.txt"
    logger = RunLogger(log_path)
    t0 = time.monotonic()
    uart = None
    try:
        logger.banner(f"{name} - HARDWARE REGRESSION   (RTL: {item['rtl_job']}   ELF: {elf})")
        logger.info("Expected order: " + " -> ".join(s["name"] for s in exp["steps"]) + " -> " + exp["completion_marker"])
        clean_generated(cfg.get("clean_paths", []), logger)

        # Open UART first so the firmware's boot output is captured. Python is the only owner of the port.
        uart = UARTController(open_transport(cfg["uart"], name, simulate), logger)

        try:
            flash_rtl(item["rtl_job"], cfg["flash"], logger)
            res["rtl_flash"] = "PASS"
        except FlashError:
            res["rtl_flash"] = "FAIL"
            raise
        uart.discard_unread()  # ignore anything printed before this RTL's firmware is loaded
        try:
            flash_firmware(elf, cfg["flash"], logger)
            res["elf_flash"] = "PASS"
        except FlashError:
            res["elf_flash"] = "FAIL"
            raise
        if simulate:
            uart.ser.reset()

        logger.info("Firmware loaded - capturing UART while the firmware runs its tests")
        steps, ok, reason = validate_run(uart, exp, logger)
        res["tests"] = steps
        res["status"] = "PASS" if ok else "FAIL"
        res["reason"] = reason
    except (FlashError, UARTError, FileNotFoundError, OSError) as exc:
        res["reason"] = f"{type(exc).__name__}: {exc}"
        logger.error(res["reason"])
    except Exception as exc:  # never lose the log on an unexpected bug
        res["reason"] = f"unexpected {type(exc).__name__}: {exc}"
        logger.error(res["reason"])
    finally:
        if uart:
            uart.close()
        res["seconds"] = round(time.monotonic() - t0, 1)
        logger.banner(f"{name}: {'REGRESSION PASSED' if res['status'] == 'PASS' else 'REGRESSION FAILED - ' + res['reason']}"
                      f"  ({res['seconds']}s)")
        logger.close()
        if cfg.get("print_log_after_each_config", True):
            print(f"\n########## UART LOG: {name} ({log_path}) ##########", flush=True)
            print(log_path.read_text(encoding="utf-8", errors="replace"), flush=True)
            print(f"########## END OF LOG: {name} ##########\n", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="automation/config/regression.json")
    ap.add_argument("--tests", default="automation/config/test_expectations.json")
    ap.add_argument("--out", default="automation")
    ap.add_argument("--only", help="run just this configuration name")
    ap.add_argument("--simulate", action="store_true", help="use the built-in fake board (no hardware)")
    args = ap.parse_args()

    cfg, exp = load_json(args.config), load_json(args.tests)
    log_dir, res_dir = Path(args.out) / "logs", Path(args.out) / "results"
    log_dir.mkdir(parents=True, exist_ok=True)
    res_dir.mkdir(parents=True, exist_ok=True)

    summary = {"started": datetime.now().isoformat(timespec="seconds"), "simulated": args.simulate,
               "configurations": [], "overall": "FAIL"}

    items = [c for c in cfg["configurations"] if c.get("enabled", True) and (not args.only or c["name"] == args.only)]
    if not items:
        print("No configurations selected", file=sys.stderr)
        return 2

    all_ok = True
    for i, item in enumerate(items):
        result = run_configuration(item, cfg, exp, args.simulate, log_dir)
        summary["configurations"].append(result)
        (res_dir / "results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        if result["status"] != "PASS":
            all_ok = False
            if not cfg.get("continue_on_failure", False):
                for rest in items[i + 1:]:
                    summary["configurations"].append({"name": rest["name"], "rtl_job": rest["rtl_job"], "elf": rest["elf"],
                                                      "rtl_flash": "NOT RUN", "elf_flash": "NOT RUN", "tests": [],
                                                      "status": "NOT RUN", "reason": "skipped after earlier failure",
                                                      "log": "", "seconds": 0.0})
                break

    summary["finished"] = datetime.now().isoformat(timespec="seconds")
    summary["overall"] = "PASS" if all_ok else "FAIL"
    (res_dir / "results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    passed = sum(1 for c in summary["configurations"] if c["status"] == "PASS")
    print(f"\nREGRESSION {summary['overall']}: {passed}/{len(summary['configurations'])} configurations passed")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
