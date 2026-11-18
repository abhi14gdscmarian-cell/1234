"""Builds automation/reports/final_regression_report.html and .txt from results.json."""
import html
import json
import sys
from pathlib import Path


def fmt(seconds):
    s = int(seconds)
    return f"{s // 3600}h {s % 3600 // 60:02d}m {s % 60:02d}s"



def main(out="automation"):
    results_file = Path(out) / "results" / "results.json"

    if not results_file.exists():
        print(
            f"WARNING: Regression results not available: {results_file}"
        )
        print(
            "The regression stage may not have started or may have failed."
        )
        return 0

    res = json.loads(results_file.read_text(encoding="utf-8"))

    rep = Path(out) / "reports"
    rep.mkdir(parents=True, exist_ok=True)

    cfgs = res["configurations"]
    passed = sum(1 for c in cfgs if c["status"] == "PASS")


    txt = [f"HARDWARE REGRESSION: {res['overall']}  ({passed}/{len(cfgs)} configurations passed)",
           f"Started {res['started']}  Finished {res.get('finished', '?')}",
           ("[SIMULATED RUN]" if res.get("simulated") else ""), ""]
    rows = []
    for c in cfgs:
        order = " -> ".join(f"{t['name']}={t['status']}" for t in c["tests"]) or "-"
        txt += [f"{c['name']:<10} {c['status']:<8} elf={c.get('elf','')} sha256:{c.get('elf_sha256','')}",
                f"           rtl={c['rtl_flash']} elf={c['elf_flash']} {fmt(c['seconds'])}",
                f"           tests: {order}"] + ([f"           reason: {c['reason']}"] if c["reason"] else [])
        color = {"PASS": "#1a7f37", "FAIL": "#cf222e"}.get(c["status"], "#6e7781")
        rows.append(
            f"<tr><td>{html.escape(c['name'])}<br><small>{html.escape(c['rtl_job'])}<br>{html.escape(c.get('elf',''))} ({c.get('elf_sha256','')})</small></td>"
            f"<td style='color:{color};font-weight:700'>{c['status']}</td><td>{c['rtl_flash']}</td><td>{c['elf_flash']}</td>"
            f"<td>{html.escape(order)}</td><td>{fmt(c['seconds'])}</td>"
            f"<td>{html.escape(c['reason'])}</td><td><a href='../logs/{html.escape(c['log'])}'>{html.escape(c['log'])}</a></td></tr>")
    (rep / "final_regression_report.txt").write_text("\n".join(txt), encoding="utf-8")
    ocolor = "#1a7f37" if res["overall"] == "PASS" else "#cf222e"
    (rep / "final_regression_report.html").write_text(f"""<!doctype html><meta charset="utf-8"><title>Hardware Regression</title>
<style>body{{font:14px system-ui;margin:24px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #d0d7de;padding:6px 10px;text-align:left;vertical-align:top}}th{{background:#f6f8fa}}</style>
<h2>Hardware Regression: <span style="color:{ocolor}">{res['overall']}</span> ({passed}/{len(cfgs)} passed)</h2>
<p>Started {res['started']} &middot; Finished {res.get('finished', '?')}<br>{'<b>SIMULATED RUN</b>' if res.get('simulated') else ''}</p>
<table><tr><th>Configuration</th><th>Result</th><th>RTL flash</th><th>ELF flash</th><th>Tests (execution order)</th><th>Duration</th><th>Failure reason</th><th>UART log</th></tr>
{''.join(rows)}</table>""", encoding="utf-8")
    print("\n".join(txt))
    return 0 if res["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "automation"))
