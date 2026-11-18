# Jenkins hardware regression: RTL + firmware

## Workflow
For each enabled pair: (1) Flash the `.job` using FlashPro Express Tcl batch mode; (2) program its matching `.elf` using SoftConsole OpenOCD and FlashPro JTAG; (3) capture UART and validate ordered test markers; (4) archive logs and reports. The next pair runs only after the current pair passes.

The uploaded ZIP contains **three** RTL jobs and **three** ELF files. The configuration uses `1.job`/`1.elf` through `3.job`/`3.elf`. Add a fourth pair explicitly if supplied.

## Jenkins Windows agent
Use a Windows agent physically connected to the PolarFire SoC board, FlashPro programmer and UART adapter. Label it `fpga-bench`. Run the agent under a Windows account with USB programmer-driver and COM-port access. For initial bring-up, use an interactive logged-in account; Windows services in Session 0 may not see USB/JTAG or COM devices. Close Tera Term and any other serial terminal.

## Node environment variables
Set these as Jenkins node environment variables, replacing examples with actual installed paths:

| Variable | Example |
|---|---|
| `FP_EXPRESS_EXE` | `C:\\Microchip\\Libero_SoC_v2024.2\\Designer\\bin\\FPExpress.exe` |
| `OPENOCD_EXE` | `C:\\Microchip\\SoftConsole-v2022.2-RISC-V-747\\openocd\\bin\\openocd.exe` |
| `OPENOCD_SCRIPTS` | `C:\\Microchip\\SoftConsole-v2022.2-RISC-V-747\\openocd\\share\\openocd\\scripts` |

These are examples only. Confirm the files exist on the Jenkins PC. Build parameters let you select `UART_PORT` (default COM5), `DEVICE` (default MPFS), simulation mode, or one configuration.

## FlashPro Express
`automation/tools/program_job.tcl` receives the absolute `.job` path via `SCRIPT_ARGS`. FlashPro's documented command-line form is `FPExpress.exe SCRIPT:<script.tcl> SCRIPT_ARGS:"<job path>"`. The script creates a temporary `.pro` project, runs selected actions, saves and closes it. Verify `create_job_project`, `run_selected_actions`, `save_project`, and `close_project` against the Tcl command reference installed with your FlashPro Express version. It emits `FLASHPRO_PROGRAMMING_COMPLETED` only after the commands finish.

## OpenOCD
`automation/tools/board.cfg` sources `interface/microsemi-flashpro.cfg` and `target/microsemi-riscv.cfg`. The command passes the SoftConsole scripts directory using `-s`, sets `DEVICE`, then runs `program <elf> verify reset exit`. Confirm the actual target selector, ELF link address and hart/core selection for your design before running. OpenOCD must detect the FlashPro and target and report `Verified OK`.

## UART expectations
Edit `automation/config/test_expectations.json` to match actual firmware output. Current markers require SPI, UART, CLOCK in that order, followed by `ALL TESTS COMPLETED`. Update markers and timeouts as required. Change `automation/config/regression.json` UART port if it differs from COM5.

## Local checks
`python -m pip install -r requirements.txt`

Simulation without hardware:
`python automation/scripts/regression_controller.py --simulate --config automation/tools/sim_regression.json --tests automation/tools/sim_test_expectations.json`

Single real configuration:
`python automation/scripts/regression_controller.py --only RTL_JOB_1`

Full regression:
`python automation/scripts/regression_controller.py`

## Git contents
Commit scripts, JSON, Tcl, CFG, Jenkinsfile, requirements and required RTL/ELF artifacts if your repository policy permits binary files. Do not commit generated `automation/work`, `automation/logs`, `automation/results`, `automation/reports`, Python caches or virtual environments.

## Bring-up order
1. Verify FlashPro Express batch execution manually.
2. Verify OpenOCD standalone connection and programmer detection.
3. Confirm UART COM port is available.
4. Run only RTL_JOB_1 and validate its UART output.
5. Run all configurations.
6. Enable automated triggers only after stable manual runs.

The pipeline disables concurrent builds because all builds share one physical board, programmer and COM port.
