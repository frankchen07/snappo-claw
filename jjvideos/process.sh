#!/bin/bash
set -euo pipefail

# --- Prevent macOS idle/disk sleep for the duration of this script ---
if [[ -z "${CAFFEINATED:-}" ]]; then
  export CAFFEINATED=1
  exec caffeinate -i "$0" "$@"
fi

# === JJ Video Processing Pipeline ===
#
# Input structure:
#   jjvideos/           ← 10p (no playlist)
#   jjvideos/10psj/     ← 10psj (10PSJ Rolling Footage playlist, unlisted)
#   jjvideos/10psm/     ← 10psm (10PSM Rolling Footage playlist, unlisted)
#
# Pipeline per file:
#   1. Read creation_time in UTC, convert to America/Los_Angeles, then derive canonical name:
#      YYYYMMDD-dayofweektimeofday-LOC-rolling-footage-viewN.mov
#   2. Compress with audio → sstready/ (archive)
#   3. Compress without audio → ytready/ (upload)
#   4. If 10psm + Mon/Wed/Fri + 05:45-06:30 PST → create teaching copies in both:
#      - sstready/ as YYYYMMDD-teaching-class-fc.mov (archive)
#      - ytready/  as YYYYMMDD-teaching-class-fc-ytready.mov (upload)
#   5. Upload to YouTube with playlist routing
#   6. After both conversions confirmed: move original → macOS Trash, sstready → sstready/.uncopied/
#   7. After confirmed upload: move ytready artifact → macOS Trash
#
# Rules:
# - 10psj morning classes are never teaching videos.
# - Root jjvideos/ files are 10p fallback and have no playlist.
# - Rolling videos are unlisted + location playlist (if 10psj/10psm).
# - Every rename is recorded in a dated ledger for backtracking.
#
# Time of day in PST/PDT local time:
#   morning = 04:00-11:59
#   afternoon = 12:00-17:59
#   night = 18:00-23:59
# Views: auto-numbered by creation time within same date+timeofday+location session

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSTREADY="$SCRIPT_DIR/sstready"
SST_UNCOPIED="$SSTREADY/.uncopied"
YTREADY="$SCRIPT_DIR/ytready"
TRASH="$SCRIPT_DIR/.trash"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_DATE=$(TZ="America/Los_Angeles" date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/${LOG_DATE}-process.md"
RENAME_LEDGER="$LOG_DIR/${LOG_DATE}-renames.tsv"

mkdir -p "$SSTREADY" "$SST_UNCOPIED" "$YTREADY" "$TRASH" "$LOG_DIR"
touch "$RENAME_LEDGER"

# --- Upload state: daily quota management ---
UPLOAD_STATE="$LOG_DIR/${LOG_DATE}-upload-state.tsv"
MAX_DAILY_UPLOADS="${YT_DAILY_LIMIT:-6}"
QUOTA_EXCEEDED=false
touch "$UPLOAD_STATE"

UPLOAD_ONLY=false
CONVERT_ONLY=false
[[ "${1:-}" == "--upload-only" ]] && UPLOAD_ONLY=true
[[ "${1:-}" == "--convert-only" ]] && CONVERT_ONLY=true

# --- Logging (logs/YYYY-MM-DD-process.md) ---
{
  echo "## Run: $(TZ=\"America/Los_Angeles\" date '+%Y-%m-%d %H:%M:%S %Z')"
  echo ""
} >> "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

STATUS_FILE="$LOG_DIR/${LOG_DATE}-process.status"
PROGRESS_FILE="$LOG_DIR/${LOG_DATE}-process.progress"
PIDFILE="$LOG_DIR/${LOG_DATE}-process.pid"
echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT

echo "starting | $(TZ=\"America/Los_Angeles\" date '+%Y-%m-%d %H:%M %Z') | pid: $$" > "$STATUS_FILE"

command -v ffmpeg >/dev/null 2>&1 || { echo "ffmpeg not found"; exit 1; }
command -v ffprobe >/dev/null 2>&1 || { echo "ffprobe not found"; exit 1; }
command -v youtubeuploader >/dev/null 2>&1 || { echo "youtubeuploader not found"; exit 1; }

# YouTube credentials
YT_SECRETS="$SCRIPT_DIR/client_secrets.json"
YT_TOKEN="$SCRIPT_DIR/request.token"

[[ -f "$YT_SECRETS" ]] || { echo "Missing $YT_SECRETS"; exit 1; }
[[ -f "$YT_TOKEN" ]] || { echo "Missing $YT_TOKEN"; exit 1; }

# Playlist IDs
PLAYLIST_TEACHING="PLqn-1QlUBKlCBo9J2Pc63uJL-YkgOMzf-"
PLAYLIST_10PSJ="PLqn-1QlUBKlDGWyP6FKdvPui8W74wLB3m"
PLAYLIST_10PSM="PLqn-1QlUBKlCyjUBDOYWXW1Wtw5SI4wNI"

# --- Helper functions ---

day_name() {
  case "$1" in
    1) echo "monday" ;; 2) echo "tuesday" ;; 3) echo "wednesday" ;;
    4) echo "thursday" ;; 5) echo "friday" ;; 6) echo "saturday" ;; 7) echo "sunday" ;;
  esac
}

time_of_day() {
  local h=$((10#$1))
  if [[ $h -ge 4 && $h -lt 12 ]]; then echo "morning"
  elif [[ $h -ge 12 && $h -lt 18 ]]; then echo "afternoon"
  else echo "night"
  fi
}

get_epoch() {
  local input_file="$1"
  local ts
  ts=$(ffprobe -v quiet -show_entries format_tags=creation_time \
    -of csv=p=0 "$input_file" 2>/dev/null | head -1)
  if [[ -z "$ts" ]]; then echo ""; return; fi
  local clean
  clean=$(echo "$ts" | sed 's/\.[0-9]*Z$//' | sed 's/Z$//')
  date -j -u -f "%Y-%m-%dT%H:%M:%S" "$clean" +%s 2>/dev/null || echo ""
}

log_rename() {
  local src="$1" dest="$2"
  printf '%s\t%s\t%s\n' "$(TZ=\"America/Los_Angeles\" date '+%Y-%m-%d %H:%M:%S %Z')" "$src" "$dest" >> "$RENAME_LEDGER"
}

move_to_trash() {
  local file="$1"
  local bname
  bname=$(basename "$file")
  local dest="$TRASH/$bname"
  [[ -e "$dest" ]] && dest="$TRASH/${bname%.mov}-$(date +%s).mov"
  mv "$file" "$dest"
}

daily_upload_count() {
  grep -c "^$(TZ="America/Los_Angeles" date +%Y-%m-%d)" "$UPLOAD_STATE" 2>/dev/null || true
}

already_uploaded() {
  local name="$1"
  grep -qF $'\t'"$name"$'\t' "$UPLOAD_STATE" 2>/dev/null
}

yt_upload() {
  local file="$1" title="$2" privacy="$3" playlist_id="${4:-}"
  local meta="$SCRIPT_DIR/.meta-tmp.json"
  local bname
  bname=$(basename "$file" .mov)

  # Skip if already recorded in state (any date)
  if already_uploaded "$bname"; then
    echo "  [upload] Already uploaded, skipping: $bname"
    return 0
  fi

  # Enforce daily cap before attempting
  local today_count
  today_count=$(daily_upload_count)
  if [[ $today_count -ge $MAX_DAILY_UPLOADS ]]; then
    echo "  [upload] Daily limit reached ($today_count/$MAX_DAILY_UPLOADS). Override: YT_DAILY_LIMIT=N. Run again tomorrow."
    return 2
  fi

  cat > "$meta" <<EOF
{
  "title": "${title}",
  "description": "",
  "selfDeclaredMadeForKids": false
}
EOF

  local playlist_flag=""
  if [[ -n "$playlist_id" ]]; then
    playlist_flag="-playlistID $playlist_id"
  fi

  echo "  [upload] '${title}' → ${privacy}${playlist_id:+ + playlist}..."
  echo "uploading | $(TZ=\"America/Los_Angeles\" date '+%Y-%m-%d %H:%M %Z') | ${bname} | ${privacy}" > "$PROGRESS_FILE"
  local result
  result=$(youtubeuploader \
    -filename "$file" \
    -cache "$YT_TOKEN" \
    -secrets "$YT_SECRETS" \
    -metaJSON "$meta" \
    -privacy "$privacy" \
    -notify=false \
    -quiet \
    $playlist_flag 2>&1) || true

  rm -f "$meta"

  if echo "$result" | grep -q "Video ID:"; then
    local vid
    vid=$(echo "$result" | grep "Video ID:" | sed 's/.*Video ID: //')
    echo "  [upload] Success! ID: ${vid} → https://studio.youtube.com/video/${vid}/edit"
    printf '%s\t%s\t%s\n' "$(TZ="America/Los_Angeles" date +%Y-%m-%d)" "$bname" "$vid" >> "$UPLOAD_STATE"
    echo "uploaded | $(TZ=\"America/Los_Angeles\" date '+%Y-%m-%d %H:%M %Z') | ${bname} | ${vid}" > "$PROGRESS_FILE"
    return 0
  elif echo "$result" | grep -qi "quota\|quotaExceeded"; then
    echo "  [upload] QUOTA EXCEEDED — stopping uploads for today. Run again tomorrow."
    return 2
  else
    echo "  [upload] FAILED: $result"
    return 1
  fi
}

# --- Upload-only mode: upload remaining ytready files, skip conversion ---
if $UPLOAD_ONLY; then
  echo "=== Upload-only mode ==="
  shopt -s nullglob
  ytready_files=("$YTREADY"/*.mov)
  shopt -u nullglob
  if [[ ${#ytready_files[@]} -eq 0 ]]; then
    echo "No .mov files in ytready/. Nothing to upload."
    exit 0
  fi
  echo "Found ${#ytready_files[@]} file(s) in ytready/"
  echo ""
  for f in "${ytready_files[@]}"; do
    bname=$(basename "$f" .mov)
    title="${bname%-ytready}"
    privacy="unlisted"
    playlist=""
    if [[ "$bname" == *"teaching-class-fc-ytready"* ]]; then
      privacy="public"
      playlist="$PLAYLIST_TEACHING"
    elif [[ "$bname" == *"-10psj-"* ]]; then
      playlist="$PLAYLIST_10PSJ"
    elif [[ "$bname" == *"-10psm-"* ]]; then
      playlist="$PLAYLIST_10PSM"
    fi
    upload_exit=0
    yt_upload "$f" "$title" "$privacy" "$playlist" || upload_exit=$?
    if [[ $upload_exit -eq 0 ]]; then
      move_to_trash "$f"
    elif [[ $upload_exit -eq 2 ]]; then
      echo ""
      break
    fi
    echo ""
  done
  echo "=== Upload-only done ==="
  exit 0
fi

# --- Collect all input files with location tags ---
# Format per line: epoch|filepath|location
work_list=""

# Scan location subdirectories
for loc_dir in "$SCRIPT_DIR/10psj" "$SCRIPT_DIR/10psm"; do
  if [[ -d "$loc_dir" ]]; then
    loc=$(basename "$loc_dir")
    while IFS= read -r f; do
      [[ -z "$f" ]] && continue
      fname=$(basename "$f")
      # Skip processed files
      [[ "$fname" == *"-ytready"* || "$fname" == *"-compressed"* || "$fname" == *"-teaching-class-fc"* || "$fname" == *"-rolling-footage"* ]] && continue
      ep=$(get_epoch "$f")
      [[ -z "$ep" ]] && { echo "WARN: No creation_time for $fname, skipping."; continue; }
      work_list="${work_list}${ep}|${f}|${loc}"$'\n'
    done < <(find "$loc_dir" -maxdepth 1 -iname "*.mov" 2>/dev/null)
  fi
done

# Scan top-level (10p fallback)
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  fname=$(basename "$f")
  [[ "$fname" == *"-ytready"* || "$fname" == *"-compressed"* || "$fname" == *"-teaching-class-fc"* || "$fname" == *"-rolling-footage"* ]] && continue
  # Skip process.sh itself and non-video files
  [[ "$fname" == "process.sh" ]] && continue
  ep=$(get_epoch "$f")
  [[ -z "$ep" ]] && { echo "WARN: No creation_time for $fname, skipping."; continue; }
  work_list="${work_list}${ep}|${f}|10p"$'\n'
done < <(find "$SCRIPT_DIR" -maxdepth 1 -iname "*.mov" 2>/dev/null)

# Remove trailing empty lines
work_list=$(echo "$work_list" | sed '/^$/d')

if [[ -z "$work_list" ]]; then
  echo "No .mov files found to process."
  exit 0
fi

# Sort by epoch (creation time) globally
work_list=$(echo "$work_list" | sort -t'|' -k1,1n)

echo "Found $(echo "$work_list" | wc -l | tr -d ' ') file(s) to process."
echo ""

# --- Assign view numbers per session (same date + time_of_day + location) ---
# Build canonical names with view numbers
declare -a FILE_LIST=()
declare -a CANONICAL_LIST=()
declare -a LOCATION_LIST=()
declare -a EPOCH_LIST=()

# Track view counts per session key
prev_session=""
view_counter=0

while IFS='|' read -r ep filepath loc; do
  dow=$(TZ="America/Los_Angeles" date -r "$ep" +%u)
  hour=$(TZ="America/Los_Angeles" date -r "$ep" +%H)
  minute=$(TZ="America/Los_Angeles" date -r "$ep" +%M)
  datestamp=$(TZ="America/Los_Angeles" date -r "$ep" +%Y%m%d)
  day_str=$(day_name "$dow")
  tod_str=$(time_of_day "$hour")

  session_key="${datestamp}-${tod_str}-${loc}"

  if [[ "$session_key" == "$prev_session" ]]; then
    view_counter=$((view_counter + 1))
  else
    view_counter=1
    prev_session="$session_key"
  fi

  if [[ "$loc" == "10p" ]]; then
    canonical="${datestamp}-${day_str}${tod_str}-rolling-footage-view${view_counter}"
  else
    canonical="${datestamp}-${day_str}${tod_str}-${loc}-rolling-footage-view${view_counter}"
  fi

  FILE_LIST+=("$filepath")
  CANONICAL_LIST+=("$canonical")
  LOCATION_LIST+=("$loc")
  EPOCH_LIST+=("$ep")
done <<< "$work_list"

# --- Process each file ---
for i in "${!FILE_LIST[@]}"; do
  echo "processing | $(TZ=\"America/Los_Angeles\" date '+%Y-%m-%d %H:%M %Z') | $(basename "${FILE_LIST[$i]}") | $((i+1))/${#FILE_LIST[@]}" > "$PROGRESS_FILE"
  input_file="${FILE_LIST[$i]}"
  canonical_base="${CANONICAL_LIST[$i]}"
  loc="${LOCATION_LIST[$i]}"
  ep="${EPOCH_LIST[$i]}"
  filename=$(basename "$input_file")

  dow=$(TZ="America/Los_Angeles" date -r "$ep" +%u)
  hour=$(TZ="America/Los_Angeles" date -r "$ep" +%H)
  minute=$(TZ="America/Los_Angeles" date -r "$ep" +%M)
  datestamp=$(TZ="America/Los_Angeles" date -r "$ep" +%Y%m%d)

  echo "=== Processing: $filename ==="
  echo "  [rename] → ${canonical_base} (${loc})"

  # --- Compress with audio → sstready ---
  sst_out="$SSTREADY/${canonical_base}.mov"
  if [[ -f "$sst_out" ]]; then
    echo "  [sstready] Already exists, skipping."
  else
    echo "  [sstready] Compressing with audio..."
    ffmpeg -y -loglevel error -hide_banner -nostats -i "$input_file" \
      -c:v libx264 -profile:v high -level 4.1 -preset veryfast -crf 23 \
      -vf "scale=1280:720,fps=30" \
      -b:v 8083k \
      -c:a aac -b:a 191k -ar 44100 \
      -movflags +faststart \
      "$sst_out"
    echo "  [sstready] Done: $(du -h "$sst_out" | cut -f1)"
  fi

  # --- Strip audio from sstready → ytready (stream copy, near-instant) ---
  yt_out="$YTREADY/${canonical_base}-ytready.mov"
  if [[ -f "$yt_out" ]]; then
    echo "  [ytready] Already exists, skipping."
  elif [[ ! -f "$sst_out" ]]; then
    echo "  [ytready] WARN: sstready missing, cannot create ytready."
  else
    echo "  [ytready] Stripping audio from sstready (stream copy)..."
    ffmpeg -y -loglevel error -hide_banner -nostats -i "$sst_out" \
      -c:v copy -an \
      -movflags +faststart \
      "$yt_out"
    echo "  [ytready] Done: $(du -h "$yt_out" | cut -f1)"
  fi

  # --- Teaching video detection ---
  # Rule: create teaching copy only for 10psm Mon/Wed/Fri ~6am videos.
  # 10psj morning classes should NOT create a teaching copy.
  teaching_sst_out=""
  teaching_yt_out=""
  is_teaching_day=false
  [[ "$dow" == "1" || "$dow" == "3" || "$dow" == "5" ]] && is_teaching_day=true
  total_min=$((10#$hour * 60 + 10#$minute))
  is_teaching_time=false
  [[ $total_min -ge 345 && $total_min -le 390 ]] && is_teaching_time=true

  if [[ "$loc" == "10psm" ]] && $is_teaching_day && $is_teaching_time; then
    teaching_base="${datestamp}-teaching-class-fc"
    teaching_sst_out="$SSTREADY/${teaching_base}.mov"
    teaching_yt_out="$YTREADY/${teaching_base}-ytready.mov"

    if [[ -f "$teaching_sst_out" ]]; then
      echo "  [teaching] SST already exists: $(basename "$teaching_sst_out")"
    else
      echo "  [teaching] 10psm Mon/Wed/Fri ~6am → creating SST $(basename "$teaching_sst_out")"
      cp "$sst_out" "$teaching_sst_out"
      log_rename "$sst_out" "$teaching_sst_out"
    fi

    if [[ -f "$teaching_yt_out" ]]; then
      echo "  [teaching] YT already exists: $(basename "$teaching_yt_out")"
    else
      echo "  [teaching] 10psm Mon/Wed/Fri ~6am → creating YT $(basename "$teaching_yt_out")"
      cp "$yt_out" "$teaching_yt_out"
      log_rename "$yt_out" "$teaching_yt_out"
    fi
  else
    echo "  [teaching] No teaching copy ($(day_name "$dow"), ${hour}:${minute}, loc=${loc})"
  fi

  # --- Post-conversion cleanup: source → macOS Trash, sstready → .uncopied ---
  # Decoupled from upload — runs as soon as both conversion outputs are confirmed.
  if [[ -f "$sst_out" && -f "$yt_out" ]]; then
    echo "  [cleanup] Conversions confirmed — trashing source, archiving sstready"
    move_to_trash "$input_file"
    log_rename "$input_file" "$TRASH/$(basename "$input_file")"
    mv "$sst_out" "$SST_UNCOPIED/"
    log_rename "$sst_out" "$SST_UNCOPIED/$(basename "$sst_out")"
    if [[ -n "$teaching_sst_out" && -f "$teaching_sst_out" ]]; then
      mv "$teaching_sst_out" "$SST_UNCOPIED/"
      log_rename "$teaching_sst_out" "$SST_UNCOPIED/$(basename "$teaching_sst_out")"
    fi
  else
    echo "  [cleanup] WARNING: conversion output missing — skipping source cleanup"
  fi

  # --- Skip upload if convert-only mode or quota already exceeded this run ---
  if $CONVERT_ONLY; then
    echo "  [convert-only] Conversions done. Skipping upload — run --upload-only to finish."
    echo ""
    continue
  fi
  if $QUOTA_EXCEEDED; then
    echo "  [upload] Skipping — daily quota reached. Run --upload-only tomorrow."
    echo ""
    continue
  fi

  # --- Upload ytready to YouTube ---
  # Determine playlist and privacy for rolling footage
  rolling_playlist=""
  case "$loc" in
    10psj) rolling_playlist="$PLAYLIST_10PSJ" ;;
    10psm) rolling_playlist="$PLAYLIST_10PSM" ;;
  esac

  upload_exit=0
  yt_upload "$yt_out" "${canonical_base}-ytready" "unlisted" "$rolling_playlist" || upload_exit=$?
  if [[ $upload_exit -eq 2 ]]; then
    QUOTA_EXCEEDED=true
    echo ""
    continue
  elif [[ $upload_exit -ne 0 ]]; then
    echo "  [skip] Upload failed — source already trashed, sstready archived. ytready kept for retry."
    echo ""
    continue
  fi

  # --- Move uploaded rolling ytready to macOS Trash ---
  echo "  [trash] Moving uploaded ytready to .trash/"
  move_to_trash "$yt_out"
  log_rename "$yt_out" "$TRASH/$(basename "$yt_out")"

  # --- Upload teaching video if created ---
  if [[ -n "$teaching_yt_out" && -f "$teaching_yt_out" ]]; then
    teaching_title=$(basename "$teaching_yt_out" .mov)
    teaching_title="${teaching_title%-ytready}"
    upload_exit=0
    yt_upload "$teaching_yt_out" "$teaching_title" "public" "$PLAYLIST_TEACHING" || upload_exit=$?
    if [[ $upload_exit -eq 2 ]]; then
      QUOTA_EXCEEDED=true
    elif [[ $upload_exit -eq 0 ]]; then
      echo "  [trash] Moving uploaded teaching ytready to .trash/"
      move_to_trash "$teaching_yt_out"
      log_rename "$teaching_yt_out" "$TRASH/$(basename "$teaching_yt_out")"
    fi
  fi

  echo ""
done

echo "done | $(TZ="America/Los_Angeles" date '+%Y-%m-%d %H:%M %Z') | mode: ${1:-full} | files: ${#FILE_LIST[@]} | uploaded: $(wc -l < "$UPLOAD_STATE" | tr -d ' ')" > "$STATUS_FILE"
rm -f "$PROGRESS_FILE"
echo "=== All done ==="
echo "  Archive (with audio): $SSTREADY/"
echo "  YouTube (no audio):   $YTREADY/"
ls -lh "$SSTREADY/" "$YTREADY/"
