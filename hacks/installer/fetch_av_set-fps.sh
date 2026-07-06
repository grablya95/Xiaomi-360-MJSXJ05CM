#!/bin/sh
#
ulimit -s 256
[ -f /mnt/data/etc/init.sh ] && /mnt/data/etc/init.sh &
perpctl A fps25-controller >/dev/null 2>&1 || true
