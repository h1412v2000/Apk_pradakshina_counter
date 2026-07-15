[app]
title = Pradakshina Tracker
package.name = pradakshinatracker
package.domain = org.yourtempleapp
source.dir = .
source.include_exts = py,png,jpg,kv,json,ttf
version = 0.1

requirements = python3,kivy,plyer,requests,sqlite3

# Permissions needed for sensors + location + notifications
android.permissions = ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,ACCESS_BACKGROUND_LOCATION,POST_NOTIFICATIONS,HIGH_SAMPLING_RATE_SENSORS

android.api = 34
android.minapi = 23
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1
