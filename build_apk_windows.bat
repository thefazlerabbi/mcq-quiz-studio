
@echo off
echo This project uses Buildozer for Android packaging.
echo Buildozer's Android toolchain needs Linux/macOS.
echo On Windows, use WSL2 + Ubuntu.
echo.
echo 1. Open Ubuntu (WSL)
echo 2. cd to the project inside the Linux filesystem
echo 3. Run:
echo    python3 -m venv .venv
echo    source .venv/bin/activate
echo    pip install --upgrade pip
echo    pip install buildozer cython
echo    buildozer android debug
echo.
pause
