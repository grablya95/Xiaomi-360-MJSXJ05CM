#!/bin/sh

. /mnt/data/config/config.sh
MEDIA_ENABLE="${MEDIA_ENABLE:-on}"
BACKCHANNEL_ENABLE="${BACKCHANNEL_ENABLE:-on}"
PTZ_ENABLE="${PTZ_ENABLE:-off}"
AUDIO_START_DELAY="${AUDIO_START_DELAY:-120}"
BACKCHANNEL_START_DELAY="${BACKCHANNEL_START_DELAY:-20}"
BACKCHANNEL_RESTART_DELAY="${BACKCHANNEL_RESTART_DELAY:-10}"
TZ_PATH="${TIMEZONE}"
[ "${TZ_PATH}" = "Europe/Kyiv" ] && [ ! -f /usr/share/zoneinfo/Europe/Kyiv ] && TZ_PATH="Europe/Kiev"
[ -f "/usr/share/zoneinfo/${TZ_PATH}" ] && ln -sf "/usr/share/zoneinfo/${TZ_PATH}" /mnt/data/etc/TZ

# sync time
NTP_PEER="pool.ntp.org"
/mnt/data/bin/ntpd -p ${NTP_PEER}
sleep 10

# Keep the legacy service disabled. The old audio-rtsp service consumes
# the same microphone FIFO as the main RTSP downsampler and corrupts audio.
perpctl X audio-rtsp 2>/dev/null || true
if [ "${PTZ_ENABLE}" = "on" ]; then
  perpctl A motor-controller
else
  perpctl X motor-controller 2>/dev/null || true
  killall motord 2>/dev/null || true
fi

# Start base services and remote maintenance first.
perpctl A fetch_av miio_sdcard miio_record miio_algo
perpctl A web-interface

# Apply the configured LED state after vendor services initialize GPIOs.
/bin/sh /mnt/sdcard/hacks/bin/led-indicator.sh "${LED_INDICATOR:-off}" >/dev/null 2>&1 || true

if [ "${FTP_ENABLE}" = "on" ]; then
  perpctl A ftp-server
else
  perpctl X ftp-server 2>/dev/null || true
fi

# The camera audio hardware is initialized asynchronously by the vendor
# services. Starting capture/AO too early leaves the speaker silent and can
# make microphone audio discontinuous until the media chain is restarted.
if [ "${MEDIA_ENABLE}" = "on" ]; then
  sleep "${AUDIO_START_DELAY}"
  perpctl A audio-capture framegrabber
  sleep 2
  perpctl A rtsp-server
  sleep 2
  perpctl A onvif-server talk-http-server
  if [ "${BACKCHANNEL_ENABLE}" = "on" ]; then
    sleep "${BACKCHANNEL_START_DELAY}"
    perpctl A audio-bridge
    sleep "${BACKCHANNEL_RESTART_DELAY}"
    perpctl X audio-bridge 2>/dev/null || true
    for PID in $(ps w | grep 'audio-bridge/bin/audio-bridge' | grep -v grep | awk '{print $1}'); do
      kill -9 "$PID" 2>/dev/null || true
    done
    sleep 2
    perpctl A audio-bridge
  else
    perpctl X audio-bridge 2>/dev/null || true
  fi
else
  perpctl X audio-capture framegrabber rtsp-server onvif-server talk-http-server audio-bridge 2>/dev/null || true
fi
