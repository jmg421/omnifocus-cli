tell application "OmniFocus 3"
    tell default document
        set testID to "fUDjGmGWOHY"
        set targetItem to first flattened task whose id is testID
        return "Found task"
    end tell
end tell
