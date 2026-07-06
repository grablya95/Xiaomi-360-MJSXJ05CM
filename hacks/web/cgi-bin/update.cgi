#!/bin/sh

ACTION=$(printf '%s' "${QUERY_STRING}" | sed -n 's/^action=\([a-z_]*\).*$/\1/p')
UPDATE=/mnt/sdcard/update.zip
LOG=/mnt/sdcard/log/ftp_update.log

json() {
  printf 'Content-Type: application/json\r\nCache-Control: no-store\r\n\r\n%s\n' "$1"
}

case "${ACTION}" in
  upload)
    # The web UI sends raw application/zip bytes, not multipart/form-data.
    # BusyBox httpd gives the body on stdin and CONTENT_LENGTH in env.
    if [ -z "${CONTENT_LENGTH}" ] || [ "${CONTENT_LENGTH}" -le 0 ] 2>/dev/null; then
      json '{"ok":false,"error":"empty upload"}'
      exit 0
    fi
    dd bs=4096 count="$(( (CONTENT_LENGTH + 4095) / 4096 ))" of="${UPDATE}" 2>/dev/null
    SIZE=$(wc -c < "${UPDATE}" 2>/dev/null)
    if [ "${SIZE}" != "${CONTENT_LENGTH}" ]; then
      rm -f "${UPDATE}"
      json "{\"ok\":false,\"error\":\"short upload ${SIZE}/${CONTENT_LENGTH}\"}"
      exit 0
    fi
    json "{\"ok\":true,\"file\":\"update.zip\",\"bytes\":${SIZE}}"
    ;;
  install)
    if [ ! -s "${UPDATE}" ]; then
      json '{"ok":false,"error":"update.zip not found"}'
      exit 0
    fi
    (
      echo "manual web update: $(date)"
      cd /mnt/sdcard || exit 1
      unzip -o update.zip >>"${LOG}" 2>&1
      [ -x /mnt/sdcard/hacks/installer/install.sh ] && /mnt/sdcard/hacks/installer/install.sh >>"${LOG}" 2>&1
      rm -f update.zip
    ) >/dev/null 2>&1 &
    json '{"ok":true,"message":"install started"}'
    ;;
  reboot)
    ( sleep 1; reboot ) >/dev/null 2>&1 &
    json '{"ok":true,"message":"rebooting"}'
    ;;
  *)
    json '{"ok":false,"error":"bad action"}'
    ;;
esac
