
param(
    [Parameter(Mandatory=$true)]
    [string]$Elf
)

$ErrorActionPreference = "Stop"

Write-Host "===================================="
Write-Host "POLARFIRE ELF PROGRAMMING"
Write-Host "===================================="

if (!(Test-Path $Elf)) {
    throw "ELF file not found: $Elf"
}

if (!$env:OPENOCD_EXE -or !(Test-Path $env:OPENOCD_EXE)) {
    throw "OPENOCD_EXE is missing or invalid"
}

if (!$env:RISCV_BIN) {
    throw "RISCV_BIN environment variable is missing"
}

$Gdb = Join-Path $env:RISCV_BIN "riscv64-unknown-elf-gdb.exe"

if (!(Test-Path $Gdb)) {
    throw "RISC-V GDB not found: $Gdb"
}

Write-Host "ELF: $Elf"
Write-Host "OpenOCD: $env:OPENOCD_EXE"
Write-Host "GDB: $Gdb"

& $Gdb --version

if ($LASTEXITCODE -ne 0) {
    throw "GDB verification failed"
}

Write-Host "ELF and GDB validation completed."
