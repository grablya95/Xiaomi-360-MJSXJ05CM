#!/bin/sh

BIN=/mnt/sdcard/hacks/bin
CONFIG=/mnt/data/config/config.sh
LOG=/mnt/sdcard/log/fps-guard.log

echo "fps exposure guard begin at $(date)" > "$LOG"
sleep 5

while true; do
  . "$CONFIG" 2>/dev/null || true
  FPS="${VIDEO_FPS:-25}"

  case "$FPS" in
    25)
      GUARD="$BIN/isp_ae_guard40ms"
      LABEL="25fps/40ms"
      ;;
    *)
      echo "fps guard disabled for VIDEO_FPS=${FPS} at $(date)" >> "$LOG"
      sleep 20
      continue
      ;;
  esac

  if [ ! -x "$GUARD" ]; then
    echo "missing guard: $GUARD" >> "$LOG"
    sleep 20
    continue
  fi

  echo "applying ${LABEL} exposure limit at $(date)" >> "$LOG"
  LD_LIBRARY_PATH=/mnt/data/lib:/mnt/sdcard/hacks/lib "$GUARD" >> "$LOG" 2>&1
  echo "${LABEL} exposure pass complete at $(date)" >> "$LOG"
  sleep 5
done
