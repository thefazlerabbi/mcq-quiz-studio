# MCQ Quiz Studio — Android APK (Python/Kivy)

This project builds an Android APK from Python using Kivy + Buildozer.

## What it does

- Select any `.xlsx` MCQ source from Android's system file picker.
- Detects:
  - Question
  - A / B / C / D
  - Correct
  - Optional: No, Section, Difficulty
- Shows total MCQ count.
- Choose question range: From → To.
- Choose number of questions.
- Choose section.
- Practice mode with instant RIGHT/WRONG.
- Exam mode with result at the end.
- Smart mode with weighted selection for weak/unseen questions.
- Wrong / Repeated Wrong / Weak / Unseen / Mastered / Bookmarked practice.
- Persistent local history.
- Section performance dashboard.
- Bookmark questions.
- Timer.
- Responsive phone-first UI.

## Excel format

Recommended first row:

No. | Section | Difficulty | Question | A | B | C | D | Correct

The parser also works when Section/Difficulty/No are missing.

Correct can be:
- A / B / C / D
- exact answer text matching one option

## Build on Windows

Buildozer's Android toolchain runs under Linux/macOS; on Windows use WSL2 + Ubuntu.

### 1) Install WSL2

Open PowerShell as Administrator:

    wsl --install -d Ubuntu

Restart Windows if asked, then open Ubuntu.

### 2) In Ubuntu, install build dependencies

    sudo apt update
    sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev cmake libffi-dev libssl-dev

### 3) Copy this project into the Linux filesystem

Do NOT build directly from /mnt/c/... if you can avoid it. Copy it to your Ubuntu home:

    mkdir -p ~/mcqquizstudio
    cp -r /mnt/c/Users/YOUR_WINDOWS_USER/Downloads/MCQ_Quiz_Studio_Android/* ~/mcqquizstudio/
    cd ~/mcqquizstudio

### 4) Create a venv and install Buildozer

    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install buildozer cython

### 5) Build debug APK

    buildozer android debug

The first build downloads Android build dependencies and can take a while.

The APK will appear in:

    bin/

### 6) Install to phone

Copy the APK from `bin/` to your Android phone and install it.
You may need to allow installation from unknown sources for the file manager you use.

## Development test on PC

For desktop testing, install Kivy and openpyxl, then:

    python main.py

The Android file picker is used on Android; desktop testing falls back to a file chooser.

## Important

The Android app stores imported Excel data inside its private app storage and saves progress in:
`mcq_progress.json`.

Original Excel files are not modified.

## Current version

1.0.0

============================================================
EASIEST METHOD ON WINDOWS: BUILD THE APK ONLINE FOR FREE
============================================================

You do NOT need WSL, Ubuntu, Android Studio, or Buildozer installed
on your Windows PC if you use GitHub Actions.

GitHub Actions provides free standard-runner usage for public
repositories. The workflow in:
    .github/workflows/build-apk.yml
automatically builds the APK and uploads it as an artifact.

STEP 1 — Create a GitHub account
    https://github.com/

STEP 2 — Create a NEW repository
    Suggested name:
        mcq-quiz-studio

    IMPORTANT:
    For the simplest free build, make the repository PUBLIC.
    Do not upload private/password/API-key information.

STEP 3 — Upload the project files
    Upload the contents of this ZIP, not the ZIP itself.

    Your GitHub repository should look like:

        main.py
        buildozer.spec
        README_BUILD_APK.txt
        .github/
          workflows/
            build-apk.yml

STEP 4 — Wait for GitHub to detect the workflow
    Open:
        Actions
    You should see:
        Build MCQ Quiz Studio APK

STEP 5 — Start the build
    Click:
        Build MCQ Quiz Studio APK
    then:
        Run workflow
        Run workflow

STEP 6 — Wait for the build
    The first Android build can take a while because the Android
    SDK/NDK/build dependencies must be prepared.

STEP 7 — Download the APK
    When the workflow shows a green check:

        Click the completed workflow run
        Scroll to "Artifacts"
        Click "MCQ-Quiz-Studio-APK"

    GitHub downloads a ZIP. Extract it and you will find the .apk.

STEP 8 — Install on Android
    Copy the APK to your phone and install it.
    Android may ask you to allow installation from that file manager.

IMPORTANT
    - This is a DEBUG APK for testing.
    - For Google Play publishing, build a signed release/AAB separately.
    - GitHub says standard GitHub-hosted runners are free for public
      repositories. GitHub Free also has a monthly allowance for
      private repositories; public repositories are the simplest
      no-cost option.
