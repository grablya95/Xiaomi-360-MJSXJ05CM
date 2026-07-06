#!/bin/sh
LOG=/mnt/sdcard/log/rtsp-8561.log
/mnt/sdcard/hacks/rtsp-server/bin/rtspserver-test \
  -p 8561 -c /mnt/data/config/rtsp.json \
  -m /var/run/rtsp_mainstream \
  >"${LOG}" 2>&1
RESULT=$?
echo "exit status: ${RESULT}" >>"${LOG}"
exit ${RESULT}
