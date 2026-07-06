#!/bin/sh

json() {
  printf 'Content-Type: application/json\r\nCache-Control: no-store\r\n\r\n%s\n' "$1"
}

plain_error() {
  printf 'Status: 400 Bad Request\r\nContent-Type: text/plain\r\n\r\n%s\n' "$1"
}

qparam() {
  printf '%s' "$QUERY_STRING" | tr '&' '\n' | sed -n "s/^$1=//p" | sed -n '1p'
}

urldecode() {
  printf '%s' "$1" \
    | sed 's/+/ /g;s/%2[fF]/\//g;s/%20/ /g;s/%2[eE]/./g;s/%2[dD]/-/g;s/%5[fF]/_/g;s/%28/(/g;s/%29/)/g;s/%5[bB]/[/g;s/%5[dD]/]/g;s/%40/@/g;s/%3[aA]/:/g;s/%26/\&/g'
}

jesc() {
  printf '%s' "$1" | sed 's/\\/\\\\/g;s/"/\\"/g'
}

safe_dir() {
  p="$1"
  [ -n "$p" ] || p=/mnt/sdcard
  [ -d "$p" ] || return 1
  real=$(cd "$p" 2>/dev/null && pwd -P) || return 1
  case "$real" in
    /mnt/sdcard|/mnt/sdcard/*|/mnt/data|/mnt/data/*|/tmp|/tmp/*|/var/run|/var/run/*) printf '%s' "$real"; return 0 ;;
  esac
  return 1
}

safe_parent_target() {
  target="$1"
  base=$(basename "$target")
  case "$base" in ""|"."|".."|*/*) return 1 ;; esac
  parent=$(dirname "$target")
  real_parent=$(safe_dir "$parent") || return 1
  printf '%s/%s' "$real_parent" "$base"
}

ACTION=$(urldecode "$(qparam action)")
REQ_PATH=$(urldecode "$(qparam path)")
REQ_NAME=$(urldecode "$(qparam name)")

case "$ACTION" in
  list)
    DIR=$(safe_dir "$REQ_PATH") || { json '{"ok":false,"error":"path is not allowed or not a directory"}'; exit 0; }
    PARENT=$(dirname "$DIR")
    if ! safe_dir "$PARENT" >/dev/null 2>&1 || [ "$PARENT" = "$DIR" ]; then
      PARENT=""
    fi
    printf 'Content-Type: application/json\r\nCache-Control: no-store\r\n\r\n'
    printf '{"ok":true,"path":"%s","parent":"%s","items":[' "$(jesc "$DIR")" "$(jesc "$PARENT")"
    first=1
    for item in "$DIR"/* "$DIR"/.[!.]* "$DIR"/..?*; do
      [ -e "$item" ] || continue
      name=$(basename "$item")
      [ "$name" = "." ] || [ "$name" = ".." ] && continue
      type=file
      [ -d "$item" ] && type=dir
      [ -L "$item" ] && type=link
      size=0
      if [ -f "$item" ]; then
        size=$(wc -c < "$item" 2>/dev/null | tr -d ' ')
        [ -n "$size" ] || size=0
      fi
      mtime=$(date -r "$item" +%s 2>/dev/null)
      [ -n "$mtime" ] || mtime=0
      [ "$first" = 1 ] || printf ','
      first=0
      printf '{"name":"%s","type":"%s","size":%s,"mtime":%s}' "$(jesc "$name")" "$type" "$size" "$mtime"
    done
    printf ']}\n'
    ;;

  download)
    FILE=$(safe_parent_target "$REQ_PATH") || { plain_error "path is not allowed"; exit 0; }
    [ -f "$FILE" ] || { plain_error "file not found"; exit 0; }
    NAME=$(basename "$FILE")
    printf 'Content-Type: application/octet-stream\r\nContent-Disposition: attachment; filename="%s"\r\nCache-Control: no-store\r\n\r\n' "$NAME"
    cat "$FILE"
    ;;

  upload)
    DIR=$(safe_dir "$REQ_PATH") || { json '{"ok":false,"error":"target directory is not allowed"}'; exit 0; }
    NAME=$(basename "$REQ_NAME")
    case "$NAME" in ""|"."|".."|*/*) json '{"ok":false,"error":"bad file name"}'; exit 0 ;; esac
    TARGET="$DIR/$NAME"
    if [ -z "$CONTENT_LENGTH" ] || [ "$CONTENT_LENGTH" -le 0 ] 2>/dev/null; then
      json '{"ok":false,"error":"empty upload"}'
      exit 0
    fi
    dd bs=4096 count="$(( (CONTENT_LENGTH + 4095) / 4096 ))" of="$TARGET" 2>/dev/null
    SIZE=$(wc -c < "$TARGET" 2>/dev/null | tr -d ' ')
    if [ "$SIZE" != "$CONTENT_LENGTH" ]; then
      rm -f "$TARGET"
      json "{\"ok\":false,\"error\":\"short upload ${SIZE}/${CONTENT_LENGTH}\"}"
      exit 0
    fi
    json "{\"ok\":true,\"bytes\":${SIZE}}"
    ;;

  mkdir)
    DIR=$(safe_dir "$REQ_PATH") || { json '{"ok":false,"error":"target directory is not allowed"}'; exit 0; }
    NAME=$(basename "$REQ_NAME")
    case "$NAME" in ""|"."|".."|*/*) json '{"ok":false,"error":"bad directory name"}'; exit 0 ;; esac
    mkdir "$DIR/$NAME" 2>/dev/null && json '{"ok":true}' || json '{"ok":false,"error":"mkdir failed"}'
    ;;

  rename)
    OLD=$(safe_parent_target "$REQ_PATH") || { json '{"ok":false,"error":"source path is not allowed"}'; exit 0; }
    [ -e "$OLD" ] || { json '{"ok":false,"error":"source not found"}'; exit 0; }
    NAME=$(basename "$REQ_NAME")
    case "$NAME" in ""|"."|".."|*/*) json '{"ok":false,"error":"bad new name"}'; exit 0 ;; esac
    NEW="$(dirname "$OLD")/$NAME"
    mv "$OLD" "$NEW" 2>/dev/null && json '{"ok":true}' || json '{"ok":false,"error":"rename failed"}'
    ;;

  delete)
    TARGET=$(safe_parent_target "$REQ_PATH") || { json '{"ok":false,"error":"path is not allowed"}'; exit 0; }
    case "$TARGET" in /mnt/sdcard|/mnt/data|/tmp|/var/run) json '{"ok":false,"error":"refuse to delete root"}'; exit 0 ;; esac
    [ -e "$TARGET" ] || { json '{"ok":false,"error":"not found"}'; exit 0; }
    rm -rf "$TARGET" 2>/dev/null && json '{"ok":true}' || json '{"ok":false,"error":"delete failed"}'
    ;;

  *)
    json '{"ok":false,"error":"bad action"}'
    ;;
esac
