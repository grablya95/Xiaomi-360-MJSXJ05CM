#!/bin/sh

CONFIG="/mnt/data/config/config.sh"
SD_CONFIG="/mnt/sdcard/hacks/installer/config.sh"

. "${CONFIG}" 2>/dev/null
MEDIA_ENABLE="${MEDIA_ENABLE:-on}"
BACKCHANNEL_ENABLE="${BACKCHANNEL_ENABLE:-on}"
PTZ_ENABLE="${PTZ_ENABLE:-off}"
AUDIO_START_DELAY="${AUDIO_START_DELAY:-120}"
BACKCHANNEL_START_DELAY="${BACKCHANNEL_START_DELAY:-20}"
BACKCHANNEL_RESTART_DELAY="${BACKCHANNEL_RESTART_DELAY:-10}"
TIMEZONE="${TIMEZONE:-Europe/Kyiv}"
LED_INDICATOR="${LED_INDICATOR:-off}"
FULL_COLOR="${FULL_COLOR:-off}"
NIGHT_VISION="${NIGHT_VISION:-auto}"
WDR="${WDR:-on}"
WATERMARK="${WATERMARK:-on}"
VIDEO_FLIP="${VIDEO_FLIP:-off}"
FTP_ENABLE="${FTP_ENABLE:-on}"
VIDEO_FPS="${VIDEO_FPS:-25}"

json_bool() { [ "$1" = "on" ] && printf true || printf false; }
json_response() {
  printf 'Content-Type: application/json\r\nCache-Control: no-store\r\n\r\n'
  printf '{"mediaEnabled":%s,"backchannelEnabled":%s,"ftpEnabled":%s,"ptzEnabled":%s,' \
    "$(json_bool "${MEDIA_ENABLE}")" "$(json_bool "${BACKCHANNEL_ENABLE}")" "$(json_bool "${FTP_ENABLE}")" "$(json_bool "${PTZ_ENABLE}")"
  printf '"ledIndicator":%s,"fullColor":%s,"nightVision":"%s","wdrEnabled":%s,"watermarkEnabled":%s,"videoFlip":%s,' \
    "$(json_bool "${LED_INDICATOR}")" "$(json_bool "${FULL_COLOR}")" "${NIGHT_VISION}" "$(json_bool "${WDR}")" "$(json_bool "${WATERMARK}")" "$(json_bool "${VIDEO_FLIP}")"
  printf '"timezone":"%s","audioStartDelay":%s,"backchannelStartDelay":%s,"backchannelRestartDelay":%s,"videoFps":"%s"}\n' \
    "${TIMEZONE}" "${AUDIO_START_DELAY}" "${BACKCHANNEL_START_DELAY}" "${BACKCHANNEL_RESTART_DELAY}" "${VIDEO_FPS}"
}

[ "${REQUEST_METHOD}" = "POST" ] || { json_response; exit 0; }

BODY=$(cat)
value() { printf '%s\n' "${BODY}" | sed -n "s/^$1=//p" | tail -n 1; }
valid_toggle() { [ "$1" = "on" ] || [ "$1" = "off" ]; }
valid_number() { case "$1" in ''|*[!0-9]*) return 1;; esac; [ "$1" -ge "$2" ] && [ "$1" -le "$3" ]; }
set_key() {
  FILE="$1" KEY="$2" VALUE="$3" TMP="$1.tmp.$$"
  [ -f "${FILE}" ] || : > "${FILE}"
  awk -v key="${KEY}" -v val="${VALUE}" '
    BEGIN { done=0 }
    index($0,key "=")==1 { print key "=\"" val "\""; done=1; next }
    { print }
    END { if (!done) print key "=\"" val "\"" }
  ' "${FILE}" > "${TMP}" && mv "${TMP}" "${FILE}"
}

NEW_MEDIA=$(value MEDIA_ENABLE); NEW_BACKCHANNEL=$(value BACKCHANNEL_ENABLE)
NEW_FTP=$(value FTP_ENABLE); NEW_PTZ=$(value PTZ_ENABLE)
NEW_LED=$(value LED_INDICATOR); NEW_FULL=$(value FULL_COLOR); NEW_NIGHT=$(value NIGHT_VISION)
NEW_WDR=$(value WDR); NEW_WATERMARK=$(value WATERMARK); NEW_FLIP=$(value VIDEO_FLIP)
NEW_TZ=$(value TIMEZONE); NEW_AUDIO_DELAY=$(value AUDIO_START_DELAY)
NEW_BC_DELAY=$(value BACKCHANNEL_START_DELAY); NEW_RESTART_DELAY=$(value BACKCHANNEL_RESTART_DELAY)
NEW_FPS=$(value VIDEO_FPS)
[ -n "${NEW_FPS}" ] || NEW_FPS="${VIDEO_FPS}"

for V in "${NEW_MEDIA}" "${NEW_BACKCHANNEL}" "${NEW_FTP}" "${NEW_PTZ}" "${NEW_LED}" "${NEW_FULL}" "${NEW_WDR}" "${NEW_WATERMARK}" "${NEW_FLIP}"; do
  valid_toggle "${V}" || { printf 'Content-Type: application/json\r\n\r\n{"ok":false,"error":"invalid toggle"}\n'; exit 1; }
done
case "${NEW_NIGHT}" in auto|on|off) ;; *) printf 'Content-Type: application/json\r\n\r\n{"ok":false,"error":"invalid night vision"}\n'; exit 1;; esac
case "${NEW_FPS}" in 20|25) ;; *) printf 'Content-Type: application/json\r\n\r\n{"ok":false,"error":"invalid fps"}\n'; exit 1;; esac
case "${NEW_TZ}" in Europe/Kyiv|Europe/Warsaw|Europe/Berlin|Europe/London|Europe/Madrid|Asia/Jerusalem|America/New_York|UTC) ;; *) printf 'Content-Type: application/json\r\n\r\n{"ok":false,"error":"invalid timezone"}\n'; exit 1;; esac
valid_number "${NEW_AUDIO_DELAY}" 30 300 && valid_number "${NEW_BC_DELAY}" 0 120 && valid_number "${NEW_RESTART_DELAY}" 1 60 || {
  printf 'Content-Type: application/json\r\n\r\n{"ok":false,"error":"invalid delay"}\n'; exit 1;
}

OLD_PTZ="${PTZ_ENABLE}"; OLD_BACKCHANNEL="${BACKCHANNEL_ENABLE}"; OLD_FTP="${FTP_ENABLE}"
for FILE in "${CONFIG}" "${SD_CONFIG}"; do
  set_key "${FILE}" MEDIA_ENABLE "${NEW_MEDIA}"
  set_key "${FILE}" BACKCHANNEL_ENABLE "${NEW_BACKCHANNEL}"
  set_key "${FILE}" FTP_ENABLE "${NEW_FTP}"
  set_key "${FILE}" PTZ_ENABLE "${NEW_PTZ}"
  set_key "${FILE}" TIMEZONE "${NEW_TZ}"
  set_key "${FILE}" LED_INDICATOR "${NEW_LED}"
  set_key "${FILE}" FULL_COLOR "${NEW_FULL}"
  set_key "${FILE}" NIGHT_VISION "${NEW_NIGHT}"
  set_key "${FILE}" WDR "${NEW_WDR}"
  set_key "${FILE}" WATERMARK "${NEW_WATERMARK}"
  set_key "${FILE}" VIDEO_FLIP "${NEW_FLIP}"
  set_key "${FILE}" AUDIO_START_DELAY "${NEW_AUDIO_DELAY}"
  set_key "${FILE}" BACKCHANNEL_START_DELAY "${NEW_BC_DELAY}"
  set_key "${FILE}" BACKCHANNEL_RESTART_DELAY "${NEW_RESTART_DELAY}"
  set_key "${FILE}" VIDEO_FPS "${NEW_FPS}"
done

TZ_PATH="${NEW_TZ}"
[ "${TZ_PATH}" = "Europe/Kyiv" ] && [ ! -f /usr/share/zoneinfo/Europe/Kyiv ] && TZ_PATH="Europe/Kiev"
ln -sf "/usr/share/zoneinfo/${TZ_PATH}" /mnt/data/etc/TZ
mortoxc set nvram default timezone "/usr/share/zoneinfo/${TZ_PATH}" >/dev/null 2>&1 || true
mortoxc set nvram default light "${NEW_LED}" >/dev/null 2>&1 || true
/bin/sh /mnt/sdcard/hacks/bin/led-indicator.sh "${NEW_LED}" >/dev/null 2>&1 || true
mortoxc set nvram default full_color "${NEW_FULL}" >/dev/null 2>&1 || true
case "${NEW_NIGHT}" in on) NIGHT_MODE=2;; off) NIGHT_MODE=1;; *) NIGHT_MODE=0;; esac
mortoxc set nvram default night_mode "${NIGHT_MODE}" >/dev/null 2>&1 || true
mortoxc set nvram default wdr "${NEW_WDR}" >/dev/null 2>&1 || true
mortoxc set nvram default watermark "${NEW_WATERMARK}" >/dev/null 2>&1 || true
mortoxc set nvram default flip "${NEW_FLIP}" >/dev/null 2>&1 || true
mortoxc sync nvram >/dev/null 2>&1 || true

if [ "${OLD_FTP}" != "${NEW_FTP}" ]; then
  [ "${NEW_FTP}" = "on" ] && perpctl A ftp-server >/dev/null 2>&1 || perpctl X ftp-server >/dev/null 2>&1
fi
if [ "${OLD_BACKCHANNEL}" != "${NEW_BACKCHANNEL}" ]; then
  if [ "${NEW_BACKCHANNEL}" = "on" ]; then perpctl A audio-bridge >/dev/null 2>&1; else perpctl X audio-bridge >/dev/null 2>&1; fi
fi
if [ "${OLD_PTZ}" != "${NEW_PTZ}" ]; then
  if [ "${NEW_PTZ}" = "on" ]; then
    perpctl A motor-controller >/dev/null 2>&1 || true
  else
    perpctl X motor-controller >/dev/null 2>&1 || true
    killall motord >/dev/null 2>&1 || true
  fi
  perpctl X onvif-server >/dev/null 2>&1 || true
  sleep 1
  perpctl A onvif-server >/dev/null 2>&1 || true
fi
sync

MEDIA_ENABLE="${NEW_MEDIA}"; BACKCHANNEL_ENABLE="${NEW_BACKCHANNEL}"; FTP_ENABLE="${NEW_FTP}"; PTZ_ENABLE="${NEW_PTZ}"
LED_INDICATOR="${NEW_LED}"; FULL_COLOR="${NEW_FULL}"; NIGHT_VISION="${NEW_NIGHT}"; WDR="${NEW_WDR}"; WATERMARK="${NEW_WATERMARK}"; VIDEO_FLIP="${NEW_FLIP}"
TIMEZONE="${NEW_TZ}"; AUDIO_START_DELAY="${NEW_AUDIO_DELAY}"; BACKCHANNEL_START_DELAY="${NEW_BC_DELAY}"; BACKCHANNEL_RESTART_DELAY="${NEW_RESTART_DELAY}"
VIDEO_FPS="${NEW_FPS}"
printf 'Content-Type: application/json\r\nCache-Control: no-store\r\n\r\n'
printf '{"ok":true,"message":"Сохранено. Для полного применения перезагрузите камеру."}\n'
