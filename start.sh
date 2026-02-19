#!/usr/bin/env bash
# DS2 Scholar — start backend + frontend in separate Terminal tabs

PROJ="$HOME/Desktop/ds2_scholar"

osascript <<EOF
tell application "Terminal"
    activate

    -- Tab 1: backend
    do script "echo '⚔  DS2 Scholar — Backend'; cd $PROJ && python3 -m backend.main"

    delay 0.6

    -- Open Tab 2 via Terminal's process (ensures keystroke lands in the right app)
    tell application "System Events"
        tell process "Terminal"
            keystroke "t" using {command down}
        end tell
    end tell

    delay 0.6

    -- Tab 2: frontend
    do script "echo '🔥 DS2 Scholar — Frontend'; cd $PROJ/frontend && PORT=3001 npm start" in front window
end tell
EOF
