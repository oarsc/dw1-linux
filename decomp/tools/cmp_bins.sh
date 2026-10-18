#!/bin/sh

TOP="$(dirname "$(dirname "$(readlink -f -- "$0")")")"

DISK_DIR="$1"
BUILD_DIR="$2"
shift 2

STATUS=0

for BIN in "$@"; do
	cmp "$TOP/$DISK_DIR/$BIN" "$TOP/$BUILD_DIR/$BIN" || STATUS=1
done

if [ "$STATUS" -eq 0 ]; then
	printf 'Compiled binaries match with target binaries\n'
fi

exit "$STATUS"
