#!/usr/bin/env bash
# DS Scholar — start backend + frontend in separate Terminal tabs

PROJ="$HOME/Desktop/ds_scholar"

osascript <<APPLESCRIPT
tell application "Terminal"
    activate

    -- Tab 1: backend (DS2 + ER)
    do script "echo '⚔  DS Scholar — Backend'; cd $PROJ && python3 -m backend.main"

    delay 0.6

    tell application "System Events"
        tell process "Terminal"
            keystroke "t" using {command down}
        end tell
    end tell

    delay 0.6

    -- Tab 2: frontend
    do script "echo '⚔  DS Scholar — Frontend'; cd $PROJ/frontend && PORT=3001 npm start" in front window
end tell
APPLESCRIPT
