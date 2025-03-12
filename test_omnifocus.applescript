tell application "OmniFocus"
  tell default document
    return "Connected to OmniFocus with " & (count of every flattened task) & " tasks."
  end tell
end tell