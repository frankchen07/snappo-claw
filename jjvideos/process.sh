#!/bin/bash
set -euo pipefail

# === JJ Video Processing Pipeline ===
#
# Input structure:
#   jjvideos/           ← 10p (no playlist)
#   jjvideos/10psj/     ← 10psj (10PSJ Rolling Footage playlist, unlisted)
#   jjvideos/10psm/     ← 10psm (10PSM Rolling Footage playlist, unlisted)
#
# Pipeline per file:
#   1. Parse creation_time → canonical name: YYYYMMDD-dayofweektimeofday-LOC-rolling-footage-viewN.mov
#   2. Compress with audio → sstready/ (archive)
#   3. Compress without audio → ytready/ (upload)
#   4. If 10psm + Mon/Wed/Fri + ~6am PST → create teaching copies in both:
#      - sstready/ as YYYYMMDD-teaching-class-fc.mov (archive)
#      - ytready/  as YYYYMMDD-teaching-class-fc-ytready.mov (upload)
#   5. Upload to YouTube with playlist routing
#   6. Move original and uploaded ytready artifact to .trash/
#   7. After confirmed upload, move matching sstready archive to sstready/.uncopied/
#
# Teaching videos: public + Teaching Snippets playlist (10psm morning classes only)
# Rolling videos: unlisted + location playlist (if 10psj/10psm)
#
# Time of day (PST): 4am-12pm=morning, 12pm-6pm=afternoon, 6pm-midnight=night
# Views: auto-numbered by creation time within same date+timeofday+location session

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSTREADY="$SCRIPT_DIR/sstready"
SST_UNCOPIED="$SSTREADY/.uncopied"
YTREADY="$SCRIPT_DIR/ytready"
TRASH="$SCRIPT_DIR/.trash"
LOG_DIR="$SCRIPT_DIR/../rawlogs"
LOG_DATE=$(TZ="America/Los_Angeles" date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/${LOG_DATE}-youtuber.md"

mkdir -p "$SSTREADY" "$SST_UNCOPIED" "$YTREADY" "$TRASH" "$LOG_DIR"

# --- Logging (rawlogs/YYYY-MM-DD-youtuber.md) ---
{
  echo "## Run: $(TZ=\"America/Los_Angeles\" date '+%Y-%m-%d %H:%M:%S %Z')"
  echo ""
} >> "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

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
  local ts=$(ffprobe -v quiet -show_entries format_tags=creation_time \
    -of csv=p=0 "$input_file" 2>/dev/null | head -1)
  if [[ -z "$ts" ]]; then echo ""; return; fi
  local clean=$(echo "$ts" | sed 's/\.[0-9]*Z$//' | sed 's/Z$//')
  date -j -u -f "%Y-%m-%dT%H:%M:%S" "$clean" +%s 2>/dev/null || echo ""
}

yt_upload() {
  local file="$1" title="$2" privacy="$3" playlist_id="${4:-}"
  local meta="$SCRIPT_DIR/.meta-tmp.json"

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
    local vid=$(echo "$result" | grep "Video ID:" | sed 's/.*Video ID: //')
    echo "  [upload] Success! ID: ${vid} → https://studio.youtube.com/video/${vid}/edit"
    return 0
  else
    echo "  [upload] FAILED: $result"
    return 1
  fi
}

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

  # --- Compress without audio → ytready ---
  yt_out="$YTREADY/${canonical_base}-ytready.mov"
  if [[ -f "$yt_out" ]]; then
    echo "  [ytready] Already exists, skipping."
  else
    echo "  [ytready] Compressing without audio..."
    ffmpeg -y -loglevel error -hide_banner -nostats -i "$input_file" \
      -c:v libx264 -profile:v high -level 4.1 -preset veryfast -crf 23 \
      -vf "scale=1280:720,fps=30" \
      -b:v 8083k \
      -an \
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
  [[ $total_min -ge 345 && $total_min -le 375 ]] && is_teaching_time=true

  if [[ "$loc" == "10psm" ]] && $is_teaching_day && $is_teaching_time; then
    teaching_base="${datestamp}-teaching-class-fc"
    teaching_sst_out="$SSTREADY/${teaching_base}.mov"
    teaching_yt_out="$YTREADY/${teaching_base}-ytready.mov"

    if [[ -f "$teaching_sst_out" ]]; then
      echo "  [teaching] SST already exists: $(basename "$teaching_sst_out")"
    else
      echo "  [teaching] 10psm Mon/Wed/Fri ~6am → creating SST $(basename "$teaching_sst_out")"
      cp "$sst_out" "$teaching_sst_out"
    fi

    if [[ -f "$teaching_yt_out" ]]; then
      echo "  [teaching] YT already exists: $(basename "$teaching_yt_out")"
    else
      echo "  [teaching] 10psm Mon/Wed/Fri ~6am → creating YT $(basename "$teaching_yt_out")"
      cp "$yt_out" "$teaching_yt_out"
    fi
  else
    echo "  [teaching] No teaching copy ($(day_name "$dow"), ${hour}:${minute}, loc=${loc})"
  fi

  # --- Upload ytready to YouTube ---
  # Determine playlist and privacy for rolling footage
  rolling_playlist=""
  case "$loc" in
    10psj) rolling_playlist="$PLAYLIST_10PSJ" ;;
    10psm) rolling_playlist="$PLAYLIST_10PSM" ;;
  esac

  if ! yt_upload "$yt_out" "${canonical_base}-ytready" "unlisted" "$rolling_playlist"; then
    echo "  [skip] Upload failed — keeping original, skipping trash."
    echo ""
    continue
  fi

  # --- Upload teaching video if created ---
  teaching_uploaded=false
  if [[ -n "$teaching_yt_out" && -f "$teaching_yt_out" ]]; then
    teaching_title=$(basename "$teaching_yt_out" -ytready.mov)
    if yt_upload "$teaching_yt_out" "$teaching_title" "public" "$PLAYLIST_TEACHING"; then
      teaching_uploaded=true
    fi
  fi

  # --- Move original to .trash ---
  trash_dest="$TRASH/$filename"
  if [[ -f "$trash_dest" ]]; then
    echo "  [trash] Original already in .trash, removing source copy."
    rm -f "$input_file"
  else
    echo "  [trash] Moving original to .trash/"
    mv "$input_file" "$trash_dest"
  fi

  # --- Move uploaded ytready artifact to .trash ---
  yt_name=$(basename "$yt_out")
  yt_trash_dest="$TRASH/$yt_name"
  if [[ -f "$yt_out" ]]; then
    if [[ -f "$yt_trash_dest" ]]; then
      ts=$(date +%s)
      yt_trash_dest="$TRASH/${yt_name%.mov}-$ts.mov"
    fi
    echo "  [trash] Moving uploaded ytready to .trash/"
    mv "$yt_out" "$yt_trash_dest"
  fi

  # --- Move teaching ytready artifact to .trash (if uploaded) ---
  if $teaching_uploaded && [[ -n "$teaching_yt_out" && -f "$teaching_yt_out" ]]; then
    teach_name=$(basename "$teaching_yt_out")
    teach_trash_dest="$TRASH/$teach_name"
    if [[ -f "$teach_trash_dest" ]]; then
      ts=$(date +%s)
      teach_trash_dest="$TRASH/${teach_name%.mov}-$ts.mov"
    fi
    echo "  [trash] Moving uploaded teaching ytready to .trash/"
    mv "$teaching_yt_out" "$teach_trash_dest"
  fi

  # --- Move matching sstready archive(s) to sstready/.uncopied after successful upload(s) ---
  if [[ -f "$sst_out" ]]; then
    echo "  [sstready] Moving uploaded archive to sstready/.uncopied/"
    mv "$sst_out" "$SST_UNCOPIED/" || true
  fi

  if $teaching_uploaded && [[ -n "$teaching_sst_out" && -f "$teaching_sst_out" ]]; then
    echo "  [sstready] Moving uploaded teaching archive to sstready/.uncopied/"
    mv "$teaching_sst_out" "$SST_UNCOPIED/" || true
  fi

  echo ""
done

echo "=== All done ==="
echo "  Archive (with audio): $SSTREADY/"
echo "  YouTube (no audio):   $YTREADY/"
ls -lh "$SSTREADY/" "$YTREADY/"
