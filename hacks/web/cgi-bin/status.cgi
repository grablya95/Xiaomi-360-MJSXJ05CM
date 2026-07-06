#!/bin/sh
. /mnt/data/config/config.sh 2>/dev/null
IP=$(ip -4 addr show wlan0 2>/dev/null | awk '/inet /{sub(/\/.*/,"",$2);print $2;exit}')
[ -n "${IP}" ] || IP="unknown"
UP=$(cut -d. -f1 /proc/uptime 2>/dev/null)
[ -n "${UP}" ] || UP=0
D=$((UP / 86400)); H=$(((UP % 86400) / 3600)); M=$(((UP % 3600) / 60))
running() { pidof "$1" >/dev/null 2>&1 && printf true || printf false; }
proc_running() { ps w 2>/dev/null | grep -q "$1" && printf true || printf false; }
microphone_running() {
  ps w 2>/dev/null | grep -q '[f]ramegrabber-audio.*rtsp_audio' || return 1
  ps w 2>/dev/null | grep -q '[g]711-downsample.*rtsp_audio8' || return 1
  return 0
}
audio_rtsp_running() {
  netstat -ltn 2>/dev/null | grep -q '0.0.0.0:8554[[:space:]]' || { printf false; return; }
  microphone_running && printf true || printf false
}
rtsp_running() { netstat -ltn 2>/dev/null | grep -q '0.0.0.0:8554[[:space:]]' && printf true || printf false; }
ftp_running() { ps | grep -q '[t]cpsvd' && printf true || printf false; }
bool_microphone() { microphone_running && printf true || printf false; }
CPU_LOAD=$(awk '{print $1}' /proc/loadavg 2>/dev/null)
[ -n "$CPU_LOAD" ] || CPU_LOAD="0.00"
CPU_PERCENT=null
CPU_LINE=$(awk '/^cpu /{print $2" "$3" "$4" "$5" "$6" "$7" "$8" "$9; exit}' /proc/stat 2>/dev/null)
if [ -n "$CPU_LINE" ]; then
  set -- $CPU_LINE
  idle_now=$4
  total_now=$(($1+$2+$3+$4+$5+$6+$7+$8))
  if [ -s /tmp/web_status_cpu.prev ]; then
    read total_prev idle_prev < /tmp/web_status_cpu.prev
    total_delta=$((total_now-total_prev))
    idle_delta=$((idle_now-idle_prev))
    if [ "$total_delta" -gt 0 ]; then
      CPU_PERCENT=$(( (100 * (total_delta - idle_delta)) / total_delta ))
    fi
  fi
  echo "$total_now $idle_now" >/tmp/web_status_cpu.prev
fi
MEM_TOTAL=$(awk '/^MemTotal:/{print $2; exit}' /proc/meminfo 2>/dev/null)
MEM_AVAIL=$(awk '/^MemAvailable:/{print $2; exit}' /proc/meminfo 2>/dev/null)
if [ -z "$MEM_AVAIL" ]; then
  MEM_AVAIL=$(awk '/^(MemFree|Buffers|Cached):/{s+=$2} END{print s+0}' /proc/meminfo 2>/dev/null)
fi
[ -n "$MEM_TOTAL" ] || MEM_TOTAL=0
[ -n "$MEM_AVAIL" ] || MEM_AVAIL=0
MEM_USED=$((MEM_TOTAL-MEM_AVAIL))
[ "$MEM_USED" -ge 0 ] 2>/dev/null || MEM_USED=0
MEM_PERCENT=0
[ "$MEM_TOTAL" -gt 0 ] 2>/dev/null && MEM_PERCENT=$((100 * MEM_USED / MEM_TOTAL))
VIDEO_FPS="${VIDEO_FPS:-25}"
printf 'Content-Type: application/json\r\nCache-Control: no-store\r\n\r\n'
printf '{"ip":"%s","uptime":"%dd %02dh %02dm","rtsp":%s,"onvif":%s,"audio":%s,"audioRtsp":%s,"recording":%s,"ftp":%s,"onvifPort":"%s","ftpPort":"%s","audioRtspPort":"%s","audioRtspUrl":"%s","cpuLoad":"%s","cpuPercent":%s,"memTotalKb":%s,"memUsedKb":%s,"memUsedPercent":%s,"videoFps":"%s"}\n' \
  "${IP}" "${D}" "${H}" "${M}" "$(rtsp_running)" "$(running onvif_srvd)" \
  "$(bool_microphone)" "$(audio_rtsp_running)" "$(running miio_record)" "$(ftp_running)" \
  "${ONVIF_PORT:-5000}" "${FTP_PORT:-2121}" "8554" "rtsp://${IP}:8554/mainstream" \
  "${CPU_LOAD}" "${CPU_PERCENT}" "${MEM_TOTAL}" "${MEM_USED}" "${MEM_PERCENT}" "${VIDEO_FPS}"
