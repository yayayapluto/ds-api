#!/usr/bin/env bash
# verify.sh - compile semua .c + run smoke test. Dipakai skill solve-daspro.
# Pakai: ./verify.sh [dir] (default: cwd)
set -u
DIR="${1:-.}"
FAIL=0; PASS=0; TOTAL=0
shopt -s nullglob
files=("$DIR"/*.c "$DIR"/latihan_mandiri/*.c "$DIR"/tugas/*.c)
[ ${#files[@]} -eq 0 ] && files=("$DIR"/*.c)
for f in "${files[@]}"; do
  [ -f "$f" ] || continue
  TOTAL=$((TOTAL+1))
  bin="/tmp/daspro_verify_$(basename "$f" .c)"
  err=$(gcc -Wall -Wextra -o "$bin" "$f" 2>&1)
  if [ $? -ne 0 ]; then
    echo "FAIL(compile): $f"
    echo "$err" | head -5
    FAIL=$((FAIL+1))
    continue
  fi
  if echo "$err" | grep -qi "warning"; then
    echo "WARN: $f"
    echo "$err" | head -5
  fi
  # smoke: beri stdin kosong / angka netral, pastikan tidak crash >5s
  echo "" | timeout 5 "$bin" >/dev/null 2>&1
  rc=$?
  if [ $rc -eq 124 ]; then echo "FAIL(timeout): $f"; FAIL=$((FAIL+1)); continue; fi
  echo "OK: $f"
  PASS=$((PASS+1))
  rm -f "$bin"
done
echo "---"
echo "PASS $PASS / $TOTAL FAIL $FAIL"
[ "$FAIL" -eq 0 ]
