pipeline {
    agent { label 'fpga-bench' }   // the Windows node physically connected to the board, programmer and UART
    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 20, unit: 'HOURS')   // >= sum of all test timeouts x 4 RTL jobs + flashing
    }
    stages {
        stage('Checkout') { steps { checkout scm } }
        stage('Check environment') {
            steps {
                bat 'python --version'
                bat 'python -m pip install --quiet pyserial'
                bat 'python -c "import json;json.load(open(r\'automation/config/regression.json\'));json.load(open(r\'automation/config/test_expectations.json\'))"'
            }
        }
        stage('Hardware regression') {
            steps { bat 'python automation\\scripts\\regression_controller.py' }
        }
    }
    post {
        always {
            bat(returnStatus: true, script: 'python automation\\scripts\\report_generator.py')
            archiveArtifacts artifacts: 'automation/logs/**,automation/reports/**,automation/results/**', allowEmptyArchive: true
        }
        success { echo 'All RTL configurations passed.' }
        failure { echo 'Hardware regression failed - see UART logs in the archived artifacts.' }
    }
}
