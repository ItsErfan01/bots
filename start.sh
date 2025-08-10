#!/bin/bash

# اجرای بات اینستاگرام
python instagram_reel_bot.py > reel.log 2>&1 &

# اجرای بات موزیک
python music-downloder.py > music.log 2>&1
