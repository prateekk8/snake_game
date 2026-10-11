# Snake Game (Kivy)

A classic Nokia-style Snake game, built in Python with Kivy so the same
code runs on desktop, Android, and iOS.

## 1. Run it in PyCharm (desktop test)

1. Create a new virtual environment for this project in PyCharm
   (File → Settings → Project → Python Interpreter → Add Interpreter).
2. Install Kivy:
   ```
   pip install kivy
   ```
3. Open `main.py` and hit Run. Use arrow keys / WASD, or click the
   on-screen buttons, to steer the snake.

## 2. Package for Android (Google Play Store)

Buildozer packages Kivy apps into APK/AAB files. It requires **Linux**
(or WSL on Windows — it does not run natively on Windows or macOS
without a VM/container).

1. On a Linux machine or WSL:
   ```
   pip install buildozer cython
   sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf \
       libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
       libtinfo5 cmake libffi-dev libssl-dev
   ```
2. Copy this whole project folder onto that machine (the included
   `buildozer.spec` is already configured).
3. Build a debug APK to test on your own phone:
   ```
   buildozer android debug
   ```
   The APK appears in `bin/`. Install it on a phone with
   `adb install bin/snakegame-1.0-arm64-v8a-debug.apk` or just copy it over.
4. Build a signed release AAB (the format Play Store requires) — see
   Buildozer's release docs: you'll generate a keystore with
   `keytool`, then run:
   ```
   buildozer android release
   ```
5. Create a Google Play Developer account (one-time $25 fee) at
   https://play.google.com/console, create a new app, and upload the
   `.aab` file under Production (or Internal Testing first, which is
   recommended).

## 3. Package for iOS (Apple App Store)

This step **requires a Mac** with Xcode installed — there's no way
around this, Apple only allows iOS builds/signing on macOS.

1. On the Mac:
   ```
   pip install kivy-ios
   toolchain build python3 kivy
   toolchain create Snake /path/to/this/project
   ```
2. This generates an Xcode project. Open it in Xcode:
   ```
   open Snake-ios/Snake.xcodeproj
   ```
3. In Xcode, set your Apple Developer team/signing certificate, set
   the app icon and launch screen, and set the bundle identifier
   (e.g. `com.yourname.snakegame`).
4. You'll need an Apple Developer account ($99/year) at
   https://developer.apple.com.
5. Archive the build (Product → Archive) and upload it via Xcode's
   Organizer to App Store Connect, then submit for review at
   https://appstoreconnect.apple.com.

## Notes / tweaks you might want

- `MOVE_INTERVAL` in `main.py` controls speed — lower it for a
  faster/harder game, or make it decrease as the score rises.
- `GRID_SIZE` controls how many cells wide/tall the board is.
- Add a real icon: drop a 512x512 `icon.png` (and optional
  `presplash.png`) into the project folder and uncomment the
  relevant lines in `buildozer.spec`.
- For sound effects, add `.wav` files and play them with
  `kivy.core.audio.SoundLoader`.
- Consider adding a high-score save using Kivy's `Storage` or a
  simple local JSON file so scores persist between sessions.
