tell application "OmniFocus"
    tell default document
        set taskCount to count of flattened tasks
        return taskCount
    end tell
end tell
