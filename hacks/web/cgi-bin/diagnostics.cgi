#!/bin/sh
printf 'Content-Type: text/plain; charset=utf-8\r\nCache-Control: no-store\r\n\r\n'
echo 'MJSXJ05CM diagnostics'
echo "date: $(date)"
echo "uptime: $(cat /proc/uptime 2>/dev/null)"
echo
echo '--- services ---'
ps | grep -E 'fetch_av|framegrabber|rtspserver|onvif|audio-bridge|tcpsvd' | grep -v grep
echo
echo '--- ports ---'
netstat -lnt 2>/dev/null | grep -E ':80 |:5000 |:8554 |:2121 '
echo
echo '--- stream pipes ---'
ls -l /var/run/rtsp_mainstream /var/run/rtsp_audio /var/run/audio_backchannel 2>&1
echo
echo '--- RTSP executable test ---'
/mnt/data/bin/rtspserver -h 2>&1
echo "exit status: $?"
echo
echo '--- RTSP service log ---'
tail -n 100 /mnt/sdcard/log/rtsp-server.log 2>&1
