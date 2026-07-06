#!/bin/sh

# MJSXJ05CM status LEDs: GPIO76 = blue, GPIO77 = yellow.
# Both LEDs are active-high.
STATE="${1:-off}"
case "${STATE}" in
  on|off) ;;
  *) exit 1 ;;
esac

gpio_write() {
  GPIO="$1"
  VALUE="$2"
  DIR="/sys/class/gpio/gpio${GPIO}"

  if [ ! -d "${DIR}" ]; then
    printf '%s' "${GPIO}" > /sys/class/gpio/export 2>/dev/null || true
    I=0
    while [ ! -d "${DIR}" ] && [ "${I}" -lt 20 ]; do
      sleep 1
      I=$((I + 1))
    done
  fi
  [ -d "${DIR}" ] || return 1
  printf 'out' > "${DIR}/direction" 2>/dev/null || true
  printf '%s' "${VALUE}" > "${DIR}/value" 2>/dev/null
}

if [ "${STATE}" = "off" ]; then
  gpio_write 76 0
  gpio_write 77 0
else
  # Normal ready indication: blue on, yellow off.
  gpio_write 77 0
  gpio_write 76 1
fi
