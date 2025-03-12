tell application "OmniFocus"
  tell default document
    set output to ""
    set allTasks to every flattened task
    
    repeat with t in allTasks
      try
        if completed of t is true then
          -- Skip completed tasks
          continue
        end if
        
        -- Get basic task details
        set taskID to id of t
        set taskName to name of t
        set taskNote to note of t
        set isCompleted to completed of t
        set taskProject to ""
        set dd to ""
        
        -- Set due date if available
        if due date of t is not missing value then
          set dd to due date of t as string
        end if
        
        -- Try to get project name
        try
          set prj to containing project of t
          if prj is not missing value then
            set taskProject to name of prj
          end if
        end try
        
        -- Build the output line
        set taskLine to taskID & "||" & taskName & "||" & taskNote & "||" & dd & "||" & isCompleted & "||" & taskProject
        
        -- Append to output
        if output is "" then
          set output to taskLine
        else
          set output to output & linefeed & taskLine
        end if
      end try
    end repeat
    
    return output
  end tell
end tell