#!/bin/sh
printf 'Content-Type: text/plain\r\nCache-Control: no-store\r\n\r\n'
echo "--- md5 ---"
md5sum /mnt/data/bin/fetch_av \
  /mnt/sdcard/hacks/bin/fetch_av-good \
  /mnt/sdcard/hacks/bin/fetch_av-fps25 \
  /mnt/sdcard/hacks/bin/isp_ae_guard40ms \
  /mnt/data/lib/libboardav.so.1.0.0 \
  /mnt/sdcard/hacks/lib/libboardav-good.so.1.0.0 \
  /mnt/sdcard/hacks/lib/libboardav-fps25.so.1.0.0 2>&1
echo "--- token ---"
cat /tmp/fetch-av-safe-token 2>&1
echo "--- config ---"
grep '^VIDEO_FPS=' /mnt/data/config/config.sh /mnt/sdcard/hacks/installer/config.sh 2>&1
echo "--- ps ---"
ps w | grep -E 'fetch_av|fps|isp_ae|framegrabber|rtspserver' | grep -v grep
