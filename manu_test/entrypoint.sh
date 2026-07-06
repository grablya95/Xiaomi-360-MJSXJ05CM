#!/bin/sh
echo "Xiaomi Hacks enabled"

/mnt/sdcard/manu_test/disable_factory_mode.sh
#/mnt/sdcard/hacks/bin/busybox telnetd &

# An FTP-delivered update is unpacked before services are replaced.  Future
# update archives intentionally omit installer/config.sh to preserve Wi-Fi.
UPDATE_FILE="/mnt/sdcard/update.zip"
UPDATE_LOG="/mnt/sdcard/log/ftp_update.log"
if [ -f "${UPDATE_FILE}" ]; then
  mkdir -p /mnt/sdcard/log
  echo "[$(date)] applying update.zip" >>"${UPDATE_LOG}"
  if /mnt/sdcard/hacks/bin/busybox unzip -o "${UPDATE_FILE}" -d /mnt/sdcard >>"${UPDATE_LOG}" 2>&1; then
    rm -f "${UPDATE_FILE}"
    touch /mnt/sdcard/hacks/installer/.force_install
    echo "[$(date)] update extracted" >>"${UPDATE_LOG}"
  else
    mv "${UPDATE_FILE}" "/mnt/sdcard/update.failed.zip"
    echo "[$(date)] update failed" >>"${UPDATE_LOG}"
  fi
fi

/mnt/sdcard/hacks/installer/install.sh &
