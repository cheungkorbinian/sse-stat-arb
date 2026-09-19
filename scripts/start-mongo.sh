#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARCH="$(uname -m)"
VERSION="7.0.16"

if [[ "$ARCH" == "arm64" ]]; then
  FILE="mongodb-macos-arm64-${VERSION}.tgz"
else
  FILE="mongodb-macos-x86_64-${VERSION}.tgz"
fi

URL="https://fastdl.mongodb.org/osx/${FILE}"
TOOLS="$ROOT/.tools"
BIN="$TOOLS/mongodb/bin/mongod"

mkdir -p "$TOOLS" "$ROOT/data/mongo"

if [[ ! -x "$BIN" ]]; then
  echo "Downloading MongoDB ${VERSION} (${FILE})..."
  curl -L --fail "$URL" -o "$TOOLS/$FILE"
  tar -xzf "$TOOLS/$FILE" -C "$TOOLS"
  EXTRACTED="$(find "$TOOLS" -maxdepth 1 -type d -name 'mongodb-macos-*' | head -n 1)"
  rm -rf "$TOOLS/mongodb"
  mv "$EXTRACTED" "$TOOLS/mongodb"
fi

echo "Starting mongod on 127.0.0.1:27017 (dbpath=$ROOT/data/mongo)"
exec "$BIN" --dbpath "$ROOT/data/mongo" --bind_ip 127.0.0.1 --port 27017 --logpath "$ROOT/data/mongo/mongod.log"
