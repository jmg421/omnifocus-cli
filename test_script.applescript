tell application "OmniFocus 3"
    tell default document
        set deletedCount to 0
        set itemList to {"fUDjGmGWOHY", "cvVtpftobYG"}
        repeat with itemID in itemList
            try
                if "tasks" is "tasks" then
                    set targetItem to first flattened task whose id is itemID
                else
                    set targetItem to first project whose id is itemID
                end if
                delete targetItem
                set deletedCount to deletedCount + 1
            on error
                -- Item might already be deleted or not found, continue
            end try
        end repeat
        return deletedCount
    end tell
end tell