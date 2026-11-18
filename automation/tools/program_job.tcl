# FlashPro Express script. Called as:  FPExpress SCRIPT:automation\tools\program_job.tcl SCRIPT_ARGS:"<path to .job>"
# VERIFY the command names against your Libero/FlashPro Express version's Tcl reference (Help > Tcl commands).
set job_file [lindex $argv 0]
set proj_dir [file normalize "automation/work/fp_project"]
file delete -force $proj_dir
create_job_project -job_project_location $proj_dir -job_file $job_file
run_selected_actions
save_project
close_project
