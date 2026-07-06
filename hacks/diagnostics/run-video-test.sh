#!/bin/sh
exec /mnt/sdcard/hacks/framegrabber/bin/ipc019/framegrabber-video \
  -f /var/run/rtsp_mainstream -c 0 \
  >/mnt/sdcard/log/framegrabber-detached.log 2>&1
