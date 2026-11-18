"""Validates the firmware's self-running test output on the UART stream.

Rules: every step marker must appear, in the configured order; a fail marker at any time
fails the run; an out-of-order step is an error; after the last step the completion marker
must appear. Each wait has its own timeout and the whole run has a total timeout.
"""
import time

from uart_controller import UARTError, UARTFailMarker, UARTTimeout


def validate_run(uart, exp, logger):
    """Returns (list of step result dicts, overall_ok, reason)."""
    steps = exp["steps"]
    fail = exp.get("fail_marker")
    total_deadline = time.monotonic() + exp.get("total_timeout_s", 21600)
    results = []

    def remaining(limit):
        return max(1, min(limit, total_deadline - time.monotonic()))

    try:
        for i, step in enumerate(steps):
            t0 = time.monotonic()
            later = {f"{s['name']} seen before {step['name']} (out of order)": s["marker"] for s in steps[i + 1:]}
            logger.info(f"Waiting for step {i + 1}/{len(steps)}: {step['name']}")
            limit = exp.get("boot_timeout_s", 120) + step.get("timeout_s", 3600) if i == 0 else step.get("timeout_s", exp.get("step_timeout_s", 3600))
            try:
                uart.wait_for(step["marker"], remaining(limit), fail_pattern=fail, abort_patterns=later, what=step["name"])
            except UARTError as exc:
                results.append({"name": step["name"], "status": "FAIL", "seconds": round(time.monotonic() - t0, 1), "detail": str(exc)})
                logger.error(f"{step['name']}: FAIL - {exc}")
                return results, False, f"{step['name']}: {exc}"
            results.append({"name": step["name"], "status": "PASS", "seconds": round(time.monotonic() - t0, 1), "detail": ""})
            logger.info(f"{step['name']}: PASS")

        t0 = time.monotonic()
        logger.info("Waiting for final completion marker")
        uart.wait_for(exp["completion_marker"], remaining(exp.get("step_timeout_s", 3600)), fail_pattern=fail, what="completion marker")
        logger.info("Completion marker received - run finished")
        return results, True, ""
    except UARTError as exc:
        results.append({"name": "COMPLETION", "status": "FAIL", "seconds": 0, "detail": str(exc)})
        logger.error(f"COMPLETION: FAIL - {exc}")
        return results, False, f"completion: {exc}"
