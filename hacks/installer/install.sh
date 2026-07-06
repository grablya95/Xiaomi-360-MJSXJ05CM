#!/bin/sh
# shellcheck disable=SC1090,SC2039

CONFIG_FILE="/mnt/sdcard/hacks/installer/config.sh"
PERSISTENT_CONFIG_FILE="/mnt/data/config/config.sh"
LOG_FILE="/mnt/sdcard/log/hack_installer.log"
DATA_BLOCK="/dev/mtdblock3"
CONFIG_BLOCK="/dev/mtdblock4"
FORCE_INSTALL_FILE="/mnt/sdcard/hacks/installer/.force_install"

# redirect stdout and stderr to the log file
mkdir -p /mnt/sdcard/log
exec 1>>${LOG_FILE}
exec 2>&1

log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] ${1}" >>${LOG_FILE}
}

die() {
  log "$1"
  log "Installer failed; removing force flag to avoid repeating the same boot failure"
  rm -f ${FORCE_INSTALL_FILE}
  sync
  log "Rebooting after failed install so existing services can start again"
  reboot now
  exit 1
}

# check if there is a new config file on sdcard
if [ ! -f ${FORCE_INSTALL_FILE} ] && [ -f ${CONFIG_FILE} ] && [ -f ${PERSISTENT_CONFIG_FILE} ]; then
  if (cmp -s ${CONFIG_FILE} ${PERSISTENT_CONFIG_FILE}); then
    log "Hack already installed and no new config found on SD card"
    exit 0
  fi
fi

log "Start installing hack"

# load configs
if [ -f ${CONFIG_FILE} ]; then
  source ${CONFIG_FILE}
else
  die "Can't load config file (${CONFIG_FILE})"
fi

# deactivate all services
no_stop="mortox"
for service in /etc/perp/*; do
  sleep 1
  if (echo "${no_stop}" | grep -w "$(basename ${service})" &>/dev/null); then
    continue
  fi
  perpctl X ${service} || log "WARN: can't deactivate ${service}"
done
killall -9 miio_record 2>/dev/null || true # it's still alive

/etc/init.d/S99netcheck stop
/etc/init.d/S61crond stop
#/etc/init.d/S15watchdog stop # this causes reboot
killall imi_watchdog
/etc/init.d/S11mdev stop
/etc/init.d/S01logging stop
sleep 5
log "Services stopped"

# backup NVRAM
nvram_config_file="/mnt/data/.config.nvram"
if [ -f "${nvram_config_file}" ]; then
  mortoxc sync nvram
  dd if=${nvram_config_file} of=${CONFIG_BLOCK} bs=64K count=1
fi
perpctl X mortox && log "mortox service stopped" || log "WARN: can't stop mortox service"

# stop perp service
/etc/init.d/S50perp stop && log "perp service stopped" || log "WARN: can't stop perp service"
sleep 5
rm -f /var/run/perp/perp*
# stop remaining services using data block
killall -9 wpa_supplicant hostapd dhcpd ntpd miio_cloud wpa_cli 2>/dev/null || true
data_pids="$(lsof | grep "/mnt/data" | awk '{print $1}' | sort -u)"
[ -n "${data_pids}" ] && kill -9 ${data_pids} 2>/dev/null || true

# A previous hack init can still be running its long audio-start delay while
# the SD installer starts. BusyBox lsof does not report those processes' cwd,
# so they keep /mnt/data busy and make a reinstall fail at umount.
killall -9 init.sh 2>/dev/null || true
killall -9 ntpd 2>/dev/null || true
killall -9 sleep 2>/dev/null || true
cd /
sync
sleep 1

# for debugging
ps aux >> ${LOG_FILE}
lsof >> ${LOG_FILE}

# unmount data block and later remount it back to make sure no process is still using it
for _ in $(seq 10); do
  sleep 5
  umount -f ${DATA_BLOCK} && break
done

# check if data block is still mounted
if (grep -qs "${DATA_BLOCK} " /proc/mounts); then
  log "WARN: can't unmount data block; continuing with mounted /mnt/data"
else
  log "Data block unmounted"
fi

# remount data block
cat ${DATA_BLOCK} >/mnt/sdcard/log/data.bin && log "Data block backed up" || log "WARN: Can't back up data block"
if (grep -qs "${DATA_BLOCK} " /proc/mounts); then
  log "Data block already mounted"
else
  mount -a
fi

# check if data block is remounted
if (grep -qs "${DATA_BLOCK} " /proc/mounts); then
  log "Data block remounted"
else
  die "Can't remount data block"
fi

# remove useless Xiaomi binaries
# keep miio_algo for auto night-vision switching, miio_sdcard for sdcard checking, miio_record for recording
cd /mnt/data/bin || die "Can't open /mnt/data/bin"
rm -f agent_client ipc_client log2mi.sh log2tf.sh miio_agent miio_client miio_client_helper_nomqtt.sh miio_cloud miio_devicekit miio_log miio_md miio_nas miio_nas_syncer miio_ota miio_qrcode miio_recv_line miio_send_line miio_stream play_audio_test post-ota.sh pre-ota.sh shbf_client

# add hacks
ln -sf /mnt/sdcard/hacks/framegrabber/bin/ipc019/framegrabber framegrabber
ln -sf /mnt/sdcard/hacks/rtsp-server/bin/rtspserver rtspserver
ln -sf /mnt/sdcard/hacks/motor-control/bin/motord motord
ln -sf /mnt/sdcard/hacks/onvif-server/bin/onvif_srvd onvif_srvd
ln -sf /mnt/sdcard/hacks/audio-bridge/bin/audio-bridge audio-bridge
ln -sf /mnt/sdcard/hacks/bin/busybox ntpd
ln -sf /mnt/sdcard/hacks/bin/busybox busybox

# remove useless Xiaomi perp services
# keep miio_algo for auto night-vision switching, miio_sdcard for sdcard checking, miio_record for recording
cd /mnt/data/etc/perp || die "Can't open /mnt/data/etc/perp"
rm -rf miio_agent miio_client miio_client_helper miio_cloud miio_devicekit miio_nas miio_ota miio_qrcode miio_stream

# add hack perp services
cp -rf /mnt/sdcard/hacks/installer/etc/* /mnt/data/etc/
chmod +t /mnt/data/etc/perp/*
chmod +x /mnt/data/etc/perp/*/rc.main
chmod +x /mnt/data/etc/init.sh
chmod +x /mnt/sdcard/hacks/web/cgi-bin/*.cgi
chmod +x /mnt/sdcard/hacks/bin/led-indicator.sh

# add hack configs
mkdir -p /mnt/data/config
echo "0 0 " >/mnt/data/config/position
cp -f /mnt/sdcard/hacks/rtsp-server/config/config.json /mnt/data/config/rtsp.json
cp -f ${CONFIG_FILE} ${PERSISTENT_CONFIG_FILE}

# optional binary overrides from the hack package
if [ -f /mnt/sdcard/hacks/lib/libboardav.so.1.0.0 ]; then
  mkdir -p /mnt/data/lib
  cp -f /mnt/sdcard/hacks/lib/libboardav.so.1.0.0 /mnt/data/lib/libboardav.so.1.0.0
fi

# optional native FPS profile. 20 FPS uses the original stable runtime;
# 25 FPS replaces only the video timing pieces and runs an exposure guard.
VIDEO_FPS="${VIDEO_FPS:-25}"
mkdir -p /mnt/data/bin /mnt/data/lib /mnt/data/etc/perp/fetch_av
if [ "${VIDEO_FPS}" = "20" ] && \
   [ -f /mnt/sdcard/hacks/bin/fetch_av-good ] && \
   [ -f /mnt/sdcard/hacks/lib/libboardav-good.so.1.0.0 ] && \
   [ -f /mnt/sdcard/hacks/installer/fetch_av_set-default.sh ]; then
  rm -rf /mnt/data/etc/perp/fps25-controller
  cp -f /mnt/sdcard/hacks/bin/fetch_av-good /mnt/data/bin/fetch_av
  cp -f /mnt/sdcard/hacks/lib/libboardav-good.so.1.0.0 /mnt/data/lib/libboardav.so.1.0.0
  cp -f /mnt/sdcard/hacks/installer/fetch_av_set-default.sh /mnt/data/etc/perp/fetch_av/fetch_av_set.sh
  chmod 755 /mnt/data/bin/fetch_av /mnt/data/etc/perp/fetch_av/fetch_av_set.sh
  chmod 644 /mnt/data/lib/libboardav.so.1.0.0
  log "FPS20 profile installed"
elif [ -f /mnt/sdcard/hacks/bin/fetch_av-fps25 ] && \
   [ -f /mnt/sdcard/hacks/lib/libboardav-fps25.so.1.0.0 ] && \
   [ -f /mnt/sdcard/hacks/bin/isp_ae_guard40ms ] && \
   [ -f /mnt/sdcard/hacks/bin/fps-guard-autostart.sh ] && \
   [ -f /mnt/sdcard/hacks/installer/fps-controller.rc.main ] && \
   [ -f /mnt/sdcard/hacks/installer/fetch_av_set-fps.sh ]; then
  mkdir -p /mnt/data/etc/perp/fps25-controller
  cp -f /mnt/sdcard/hacks/bin/fetch_av-fps25 /mnt/data/bin/fetch_av
  cp -f /mnt/sdcard/hacks/lib/libboardav-fps25.so.1.0.0 /mnt/data/lib/libboardav.so.1.0.0
  cp -f /mnt/sdcard/hacks/installer/fetch_av_set-fps.sh /mnt/data/etc/perp/fetch_av/fetch_av_set.sh
  cp -f /mnt/sdcard/hacks/installer/fps-controller.rc.main /mnt/data/etc/perp/fps25-controller/rc.main
  chmod 755 /mnt/data/bin/fetch_av /mnt/data/etc/perp/fetch_av/fetch_av_set.sh \
    /mnt/data/etc/perp/fps25-controller/rc.main /mnt/sdcard/hacks/bin/isp_ae_guard40ms \
    /mnt/sdcard/hacks/bin/fps-guard-autostart.sh
  chmod 644 /mnt/data/lib/libboardav.so.1.0.0
  chmod +t /mnt/data/etc/perp/fps25-controller
  log "FPS25 profile installed"
fi

# clear crontab
cp -f /mnt/sdcard/hacks/installer/etc/crontab /mnt/data/etc/crontab

# set timezone
TZ_PATH="${TIMEZONE}"
[ "${TZ_PATH}" = "Europe/Kyiv" ] && [ ! -f /usr/share/zoneinfo/Europe/Kyiv ] && TZ_PATH="Europe/Kiev"
ln -sf /usr/share/zoneinfo/${TZ_PATH} /mnt/data/etc/TZ

# restore NVRAM
chmod 777 ${nvram_config_file}
dd if=${CONFIG_BLOCK} of=${nvram_config_file} bs=64K count=1
chmod 000 ${nvram_config_file}
log "NVRAM restored"

# restart perp service
/etc/init.d/S50perp start && log "perp service restarted" || log "WARN: can't restart perp service"
sleep 5
perpctl A mortox && log "mortox reactivated" || log "WARN: can't reactivate mortox"
mortoxc sync nvram && log "NVRAM synced" || log "WARN: can't sync NVRAM"
sleep 5

# save configs to NVRAM
mortoxc set nvram default motor "[51,51]"
mortoxc set nvram default timezone "/usr/share/zoneinfo/${TZ_PATH}"
mortoxc set nvram default light "${LED_INDICATOR}"
mortoxc set nvram default full_color "${FULL_COLOR}"
if [ "${NIGHT_VISION}" == "on" ]; then
  NIGHT_MODE="2"
elif [ "${NIGHT_VISION}" == "off" ]; then
  NIGHT_MODE="1"
else # auto
  NIGHT_MODE="0"
fi
mortoxc set nvram default night_mode "${NIGHT_MODE}"
mortoxc set nvram default wdr "${WDR}"
mortoxc set nvram default watermark "${WATERMARK}"
mortoxc set nvram default flip "${VIDEO_FLIP}"
mortoxc set nvram default miio_ssid "${WIFI_SSID}"
mortoxc set nvram default key_mgmt "${WIFI_SECURITY}"
mortoxc set nvram default miio_passwd "${WIFI_PASSWORD}"
mortoxc set nvram default bind_status "ok"
mortoxc sync nvram
sleep 5

# finishing
log "Installed successfully"
rm -f ${FORCE_INSTALL_FILE}
sleep 5

reboot now
