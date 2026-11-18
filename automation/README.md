# FPGA + Firmware Hardware Regression Automation

Each RTL job has its own ELF; the firmware runs its tests by itself (no menu selection).
Per RTL job (1..4): clean -> open UART -> flash RTL .job -> flash ITS .elf -> firmware runs ->
capture UART until every expected step passed IN ORDER and the completion line appears ->
save and PRINT the full UART log (Jenkins console + automation/logs/RTL_JOB_n.txt) -> next RTL job.
The next job is flashed only if the previous one passed. Exit code 0 = all passed.

## Setup (Jenkins Windows PC with board, programmer and UART)
1. Python 3.9+, `python -m pip install pyserial`. Close Tera Term (Python must own the COM port).
2. Put files in the repo: `rtl/RTL_JOB_n.job`, `firmware/FIRMWARE_n.elf` (or change paths in regression.json).
3. `automation/config/regression.json`: COM port/baud; `flash.rtl_command` and `flash.elf_command` = the exact commands you use today
   (`{rtl_job}`, `{elf}` are substituted); `*_success_regex` = text the tool prints on success; per-configuration `rtl_job` + `elf` pairs.
   `automation/tools/program_job.tcl` and `board.cfg` are TEMPLATES - verify against your tool versions.
4. `automation/config/test_expectations.json`: the exact text the firmware prints for each step (regex), the fail marker, the final
   completion marker, and timeouts. Steps must appear in the listed order.
5. Jenkins node label `fpga-bench` (edit Jenkinsfile) and a pipeline timeout >= total expected run time.

## Try without hardware
    python automation/scripts/regression_controller.py --simulate --config automation/tools/sim_regression.json --tests automation/tools/sim_test_expectations.json
Drills: SIM_FAIL=RTL_JOB_2:UART_TEST  SIM_HANG=RTL_JOB_1:CLOCK_TEST  SIM_ORDER=RTL_JOB_1  SIM_NO_COMPLETE=RTL_JOB_1

## Bring-up
`--only RTL_JOB_1` first (flash commands can be `echo` while the board is already programmed) to confirm the UART markers; then real flashing; then all four; then Jenkins.

## Outputs
automation/logs/RTL_JOB_n.txt, automation/results/results.json, automation/reports/final_regression_report.html/.txt
