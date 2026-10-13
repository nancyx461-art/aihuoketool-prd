@echo off
chcp 65001 >nul
cd /d %~dp0
if not exist output mkdir output
python make_video.py >> output\daily.log 2>&1
