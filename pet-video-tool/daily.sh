#!/usr/bin/env bash
cd "$(dirname "$0")" && mkdir -p output && python3 make_video.py >> output/daily.log 2>&1
