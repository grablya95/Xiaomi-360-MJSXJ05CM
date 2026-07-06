#!/bin/sh

SD=/mnt/sdcard/hacks
DATA=/mnt/data
CONFIG=/mnt/data/config/config.sh
SD_CONFIG=/mnt/sdcard/hacks/installer/config.sh
LOG=/mnt/sdcard/log/fps-switch.log

json_header() {
  printf 'Content-Type: application/json\r\nCache-Control: no-store\r\n\r\n'
}

json_error() {
  json_header
  printf '{"ok":false,"error":"%s"}\n' "$1"
  exit 1
}

set_key() {
  FILE="$1" KEY="$2" VALUE="$3" TMP="$1.tmp.$$"
  DIR=$(dirname "$FILE")
  [ -d "$DIR" ] || mkdir -p "$DIR"
  [ -f "$FILE" ] || : > "$FILE"
  awk -v key="$KEY" -v val="$VALUE" '
    BEGIN { done=0 }
    index($0,key "=")==1 { print key "=\"" val "\""; done=1; next }
    { print }
    END { if (!done) print key "=\"" val "\"" }
  ' "$FILE" > "$TMP" && mv "$TMP" "$FILE"
}

read_body_value() {
  BODY=$(cat)
  printf '%s\n' "$BODY" | sed -n 's/^FPS=//p' | tail -n 1
}

stop_video_services() {
  perpctl X onvif-server >/dev/null 2>&1 || true
  perpctl X rtsp-server >/dev/null 2>&1 || true
  perpctl X framegrabber >/dev/null 2>&1 || true
  perpctl X fetch_av >/dev/null 2>&1 || true
  killall rtspserver-v041-uclibc >/dev/null 2>&1 || true
  killall framegrabber >/dev/null 2>&1 || true
  killall fetch_av >/dev/null 2>&1 || true
  sleep 3
}

stop_fps_guard() {
  perpctl X fps25-controller >/dev/null 2>&1 || true
  killall isp_ae_guard40ms >/dev/null 2>&1 || true
  for pid in $(ps w | grep 'fps-guard-autostart.sh' | grep -v grep | awk '{print $1}'); do
    kill "$pid" >/dev/null 2>&1 || true
  done
  for pid in $(ps w | grep 'fps25-autostart.sh' | grep -v grep | awk '{print $1}'); do
    kill "$pid" >/dev/null 2>&1 || true
  done
  rm -f /tmp/fps25-autostart.lock
}

install_fps_controller() {
  mkdir -p "$DATA/etc/perp/fps25-controller"
  cp -f "$SD/installer/fps-controller.rc.main" "$DATA/etc/perp/fps25-controller/rc.main" || return 1
  chmod 755 "$DATA/etc/perp/fps25-controller/rc.main"
  chmod +t "$DATA/etc/perp/fps25-controller"
  chmod 755 "$SD/bin/fps-guard-autostart.sh" "$SD/bin/isp_ae_guard40ms" 2>/dev/null || true
}

apply_profile() {
  FPS="$1"
  mkdir -p "$DATA/bin" "$DATA/lib" "$DATA/etc/perp/fetch_av" /mnt/sdcard/log

  case "$FPS" in
    20)
      [ -f "$SD/bin/fetch_av-good" ] || return 20
      [ -f "$SD/lib/libboardav-good.so.1.0.0" ] || return 21
      [ -f "$SD/installer/fetch_av_set-default.sh" ] || return 22
      stop_fps_guard
      rm -rf "$DATA/etc/perp/fps25-controller"
      cp -f "$SD/bin/fetch_av-good" "$DATA/bin/fetch_av" || return 23
      cp -f "$SD/lib/libboardav-good.so.1.0.0" "$DATA/lib/libboardav.so.1.0.0" || return 24
      cp -f "$SD/installer/fetch_av_set-default.sh" "$DATA/etc/perp/fetch_av/fetch_av_set.sh" || return 25
      ;;
    25)
      [ -f "$SD/bin/fetch_av-fps25" ] || return 30
      [ -f "$SD/lib/libboardav-fps25.so.1.0.0" ] || return 31
      [ -f "$SD/installer/fetch_av_set-fps.sh" ] || return 32
      [ -f "$SD/bin/isp_ae_guard40ms" ] || return 33
      [ -f "$SD/bin/fps-guard-autostart.sh" ] || return 34
      [ -f "$SD/installer/fps-controller.rc.main" ] || return 35
      stop_fps_guard
      cp -f "$SD/bin/fetch_av-fps25" "$DATA/bin/fetch_av" || return 36
      cp -f "$SD/lib/libboardav-fps25.so.1.0.0" "$DATA/lib/libboardav.so.1.0.0" || return 37
      cp -f "$SD/installer/fetch_av_set-fps.sh" "$DATA/etc/perp/fetch_av/fetch_av_set.sh" || return 38
      install_fps_controller || return 39
      ;;
  esac

  chmod 755 "$DATA/bin/fetch_av" "$DATA/etc/perp/fetch_av/fetch_av_set.sh" 2>/dev/null || true
  chmod 644 "$DATA/lib/libboardav.so.1.0.0" 2>/dev/null || true
  sync
  return 0
}

check_profile() {
  FPS="$1"
  case "$FPS" in
    20)
      [ -f "$SD/bin/fetch_av-good" ] || return 20
      [ -f "$SD/lib/libboardav-good.so.1.0.0" ] || return 21
      [ -f "$SD/installer/fetch_av_set-default.sh" ] || return 22
      ;;
    25)
      [ -f "$SD/bin/fetch_av-fps25" ] || return 30
      [ -f "$SD/lib/libboardav-fps25.so.1.0.0" ] || return 31
      [ -f "$SD/installer/fetch_av_set-fps.sh" ] || return 32
      [ -f "$SD/bin/isp_ae_guard40ms" ] || return 33
      [ -f "$SD/bin/fps-guard-autostart.sh" ] || return 34
      [ -f "$SD/installer/fps-controller.rc.main" ] || return 35
      ;;
  esac
  return 0
}

restart_video_services() {
  perpctl A fps25-controller >/dev/null 2>&1 || true
  perpctl A fetch_av >/dev/null 2>&1 || true
  sleep 8
  perpctl A framegrabber >/dev/null 2>&1 || true
  sleep 3
  perpctl A rtsp-server >/dev/null 2>&1 || true
  sleep 2
  perpctl A onvif-server >/dev/null 2>&1 || true
}

. "$CONFIG" 2>/dev/null || true
CURRENT="${VIDEO_FPS:-25}"

if [ "$REQUEST_METHOD" != "POST" ] && [ -z "$1" ]; then
  json_header
  printf '{"ok":true,"fps":"%s"}\n' "$CURRENT"
  exit 0
fi

if [ -n "$1" ]; then
  NEW_FPS="$1"
else
  NEW_FPS=$(read_body_value)
fi

case "$NEW_FPS" in 20|25) ;; *) json_error "invalid FPS";; esac

check_profile "$NEW_FPS"
RET=$?
if [ "$RET" != "0" ]; then
  json_error "profile files missing $RET"
fi

echo "switch fps from $CURRENT to $NEW_FPS at $(date)" > "$LOG"
set_key "$CONFIG" VIDEO_FPS "$NEW_FPS"
set_key "$SD_CONFIG" VIDEO_FPS "$NEW_FPS"

stop_video_services >>"$LOG" 2>&1
apply_profile "$NEW_FPS" >>"$LOG" 2>&1
RET=$?
if [ "$RET" != "0" ]; then
  echo "profile apply failed: $RET" >> "$LOG"
  json_error "profile apply failed $RET"
fi
restart_video_services >>"$LOG" 2>&1
sync

json_header
printf '{"ok":true,"fps":"%s","message":"FPS %s applied"}\n' "$NEW_FPS" "$NEW_FPS"
