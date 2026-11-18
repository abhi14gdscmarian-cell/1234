pipeline {
    agent { label 'fpga-bench' }
    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 20, unit: 'HOURS')
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }
    parameters {
        string(name: 'UART_PORT', defaultValue: 'COM5', description: 'UART COM port connected to DUT')
        string(name: 'DEVICE', defaultValue: 'MPFS', description: 'OpenOCD device selector')
        booleanParam(name: 'RUN_SIMULATION', defaultValue: false, description: 'Run fake-board simulation without hardware')
        string(name: 'ONLY_CONFIGURATION', defaultValue: '', description: 'Optional: RTL_JOB_1, RTL_JOB_2 or RTL_JOB_3')
    }
    environment {
        PYTHONUNBUFFERED = '1'
        PIP_DISABLE_PIP_VERSION_CHECK = '1'
    }
    stages {
        stage('Checkout') { steps { checkout scm } }
        stage('Validate tools and inputs') {
            steps {
                bat '''
                    @echo off
                    python --version || exit /b 1
                    python -c "import json; json.load(open('automation/config/regression.json')); json.load(open('automation/config/test_expectations.json'))" || exit /b 2
                    for %%F in (rtl\\1.job rtl\\2.job rtl\\3.job firmware\\1.elf firmware\\2.elf firmware\\3.elf) do (
                      if not exist "%%F" (echo ERROR: Missing %%F & exit /b 3)
                    )
                '''
                bat 'python -m pip install -r requirements.txt'
                script {
                    if (!params.RUN_SIMULATION) {
                        bat '''
                            if not exist "%FP_EXPRESS_EXE%" (echo ERROR: FP_EXPRESS_EXE invalid & exit /b 4)
                            if not exist "%OPENOCD_EXE%" (echo ERROR: OPENOCD_EXE invalid & exit /b 5)
                            if not exist "%OPENOCD_SCRIPTS%\\interface\\microsemi-flashpro.cfg" (echo ERROR: OPENOCD_SCRIPTS invalid & exit /b 6)
                        '''
                    }
                }
            }
        }
        stage('Run regression') {
            steps {
                script {
                    withEnv(["UART_PORT=${params.UART_PORT}", "DEVICE=${params.DEVICE}"]) {
                        if (params.RUN_SIMULATION) {
                            bat 'python automation\\scripts\\regression_controller.py --simulate --config automation\\tools\\sim_regression.json --tests automation\\tools\\sim_test_expectations.json'
                        } else if (params.ONLY_CONFIGURATION?.trim()) {
                            if (!(params.ONLY_CONFIGURATION in ['RTL_JOB_1', 'RTL_JOB_2', 'RTL_JOB_3'])) {
                                error("Invalid ONLY_CONFIGURATION: ${params.ONLY_CONFIGURATION}")
                            }
                            bat "python automation\\scripts\\regression_controller.py --only ${params.ONLY_CONFIGURATION}"
                        } else {
                            bat 'python automation\\scripts\\regression_controller.py'
                        }
                    }
                }
            }
        }
    }
    post {
        always {
            bat(returnStatus: true, script: 'python automation\\scripts\\report_generator.py')
            archiveArtifacts artifacts: 'automation/logs/**,automation/reports/**,automation/results/**', allowEmptyArchive: true
        }
        success { echo 'All selected RTL/ELF configurations passed.' }
        failure { echo 'Regression failed. Inspect archived FlashPro, OpenOCD and UART logs.' }
    }
}
