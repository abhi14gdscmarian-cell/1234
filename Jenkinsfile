pipeline {
    agent { label 'fpga-bench' }

    options {
        timestamps()
        disableConcurrentBuilds()
        skipDefaultCheckout(true)
        timeout(time: 20, unit: 'HOURS')
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    parameters {
        booleanParam(name: 'RUN_SIMULATION', defaultValue: false,
            description: 'Run simulated regression without hardware')
        string(name: 'ONLY_CONFIGURATION', defaultValue: '',
            description: 'Optional: RTL_JOB_1, RTL_JOB_2 or RTL_JOB_3')
        string(name: 'UART_PORT', defaultValue: 'COM5',
            description: 'UART COM port connected to PolarFire SoC')
        string(name: 'DEVICE', defaultValue: 'MPFS',
            description: 'Device selector expected by installed OpenOCD scripts')
    }

    environment {
        // Replace these paths with the actual paths on the Jenkins Windows agent.
        FP_EXPRESS_BIN = 'C:\\Microchip\\Libero_SoC_v2024.2\\Designer\\bin'
        RISCV_BIN = 'C:\\Microchip\\SoftConsole-v2022.2-RISC-V-747\\riscv-unknown-elf-gcc\\bin'
        OPENOCD_BIN = 'C:\\Microchip\\SoftConsole-v2022.2-RISC-V-747\\openocd\\bin'
        OPENOCD_SCRIPTS = 'C:\\Microchip\\SoftConsole-v2022.2-RISC-V-747\\openocd\\share\\openocd\\scripts'
        GDB_ARCH = 'riscv:rv32'  // Keep consistent with the ELF architecture; change to riscv:rv64 if required.
        PYTHONUNBUFFERED = '1'
        PIP_DISABLE_PIP_VERSION_CHECK = '1'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo 'Hardware regression source checked out successfully.'
                bat 'git log -1 --pretty=format:"Commit Hash: %%H%%nAuthor: %%an%%nDate: %%ad%%nMessage: %%s"'
            }
        }

        stage('Verify Tools') {
            steps {
                bat '''
                    @echo off
                    echo ==== Git ====
                    git --version
                    if errorlevel 1 exit /b 1

                    echo ==== Python ====
                    python --version
                    if errorlevel 1 exit /b 1
                '''

                script {
                    if (!params.RUN_SIMULATION) {
                        withEnv(["PATH+OPENOCD=${env.OPENOCD_BIN}"]) {
                            bat '''
                                @echo off
                                echo ==== FlashPro Express ====
                                if not exist "%FP_EXPRESS_BIN%\\FPExpress.exe" (
                                    echo ERROR: FPExpress.exe not found: %FP_EXPRESS_BIN%
                                    exit /b 1
                                )

                                echo ==== OpenOCD ====
                                if not exist "%OPENOCD_BIN%\\openocd.exe" (
                                    echo ERROR: openocd.exe not found: %OPENOCD_BIN%
                                    exit /b 1
                                )
                                if not exist "%RISCV_BIN%\\riscv64-unknown-elf-gdb.exe" (
                                    echo ERROR: riscv64-unknown-elf-gdb.exe not found: %RISCV_BIN%
                                    exit /b 1
                                )
                                "%OPENOCD_BIN%\\openocd.exe" --version
                                if errorlevel 1 exit /b 1

                                echo ==== OpenOCD scripts ====
                                if not exist "%OPENOCD_SCRIPTS%\\interface\\microsemi-flashpro.cfg" exit /b 1
                                if not exist "%OPENOCD_SCRIPTS%\\target\\microsemi-riscv.cfg" exit /b 1
                            '''
                        }
                    }
                }

                bat 'python -m pip install -r requirements.txt'
            }
        }

        stage('Validate Project Files') {
            steps {
                bat '''
                    @echo off
                    if not exist automation\\scripts\\regression_controller.py exit /b 1
                    if not exist automation\\scripts\\flash_controller.py exit /b 1
                    if not exist automation\\config\\regression.json exit /b 1
                    if not exist automation\\config\\test_expectations.json exit /b 1
                    if not exist automation\\tools\\program_job.tcl exit /b 1
                    if not exist automation\\tools\\board.cfg exit /b 1
                    if not exist automation\\tools\\program_elf_gdb.ps1 exit /b 1

                    for %%F in (rtl\\1.job rtl\\2.job rtl\\3.job firmware\\1.elf firmware\\2.elf firmware\\3.elf) do (
                        if not exist "%%F" (
                            echo ERROR: Required file missing: %%F
                            exit /b 1
                        )
                    )
                    echo Project validation completed.
                '''
            }
        }

        stage('Clean Generated Files') {
            steps {
                powershell '''
                    $ErrorActionPreference = 'Stop'
                    $dirs = @(
                        'automation/work',
                        'automation/logs',
                        'automation/results',
                        'automation/reports'
                    )
                    foreach ($dir in $dirs) {
                        $path = Join-Path $env:WORKSPACE $dir
                        if (Test-Path -LiteralPath $path) {
                            Write-Host "Removing generated directory: $path"
                            Remove-Item -LiteralPath $path -Recurse -Force
                        }
                        New-Item -ItemType Directory -Path $path -Force | Out-Null
                    }
                    Write-Host 'Generated output directories are ready.'
                '''
            }
        }

        stage('Run Hardware Regression') {
            steps {
                script {
                    withEnv([
                        "PATH+OPENOCD=${env.OPENOCD_BIN}",
                        "FP_EXPRESS_EXE=${env.FP_EXPRESS_BIN}\\FPExpress.exe",
                        "OPENOCD_EXE=${env.OPENOCD_BIN}\\openocd.exe",
                        "RISCV_BIN=${env.RISCV_BIN}",
                        "GDB_ARCH=${env.GDB_ARCH}",
                        "UART_PORT=${params.UART_PORT}",
                        "DEVICE=${params.DEVICE}"
                    ]) {
                        if (params.RUN_SIMULATION) {
                            bat 'python automation\\scripts\\regression_controller.py --simulate --config automation\\tools\\sim_regression.json --tests automation\\tools\\sim_test_expectations.json'
                        } else if (params.ONLY_CONFIGURATION?.trim()) {
                            if (!(params.ONLY_CONFIGURATION in ['RTL_JOB_1', 'RTL_JOB_2', 'RTL_JOB_3'])) {
                                error('Invalid ONLY_CONFIGURATION: ' + params.ONLY_CONFIGURATION)
                            }
                            bat "python automation\\scripts\\regression_controller.py --only ${params.ONLY_CONFIGURATION}"
                        } else {
                            bat 'python automation\\scripts\\regression_controller.py'
                        }
                    }
                }
            }
        }

        stage('Show Commit Details') {
            steps {
                bat 'git log -1 --format="Commit: %%h%%nAuthor: %%an%%nMessage: %%s"'
            }
        }
    }

    post {
        always {
            bat(returnStatus: true, script: 'python automation\\scripts\\report_generator.py')
            archiveArtifacts artifacts: 'automation/logs/**,automation/reports/**,automation/results/**',
                allowEmptyArchive: true
            echo 'PolarFire SoC hardware regression pipeline finished.'
        }
        success {
            echo 'SUCCESS: Selected RTL, ELF and UART regression checks passed.'
        }
        failure {
            echo 'FAILURE: Review FlashPro, OpenOCD and UART logs in archived artifacts.'
        }
    }
}
