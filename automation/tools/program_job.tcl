# FlashPro Express batch script.
# Invocation: FPExpress.exe SCRIPT:program_job.tcl SCRIPT_ARGS:"<absolute .job path>"
if {$argc != 1} {
    error "Usage: program_job.tcl <absolute_path_to_job_file>"
}
set job_file [file normalize [lindex $argv 0]]
if {![file exists $job_file]} {
    error "Job file does not exist: $job_file"
}
set work_dir [file normalize "automation/work/flashpro"]
file mkdir $work_dir
set project_file [file join $work_dir "ci_flashpro.pro"]
puts "FLASHPRO_JOB=$job_file"
puts "FLASHPRO_PROJECT=$project_file"
create_job_project -job_project_location $project_file -job_file $job_file -overwrite 1
run_selected_actions
save_project
close_project
puts "FLASHPRO_PROGRAMMING_COMPLETED"
