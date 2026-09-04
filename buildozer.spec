[app]
title = MCQ Quiz Studio
package.name = mcqquizstudio
package.domain = org.mcqquiz
source.dir = .
source.include_exts = py,png,jpg,kv,xlsx,json
version = 1.0.0
requirements = python3,kivy,openpyxl,pyjnius
orientation = portrait
fullscreen = 0

android.api = 35
android.minapi = 23
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True
android.private_storage = True
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
