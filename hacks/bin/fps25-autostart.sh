#!/bin/sh

BIN=/mnt/sdcard/hacks/bin
LOG=/mnt/sdcard/log/fps25-autostart.log

echo "fps25 exposure guard begin at $(date); continuous day/night protection" > "$LOG"
sleep 5

while true; do
  echo "applying 40 ms exposure limit at $(date)" >> "$LOG"
  LD_LIBRARY_PATH=/mnt/data/lib:/mnt/sdcard/hacks/lib \
    "$BIN/isp_ae_guard40ms" >> "$LOG" 2>&1
  echo "40 ms exposure limit applied at $(date)" >> "$LOG"
  sleep 5
done
