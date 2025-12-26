# Spotify Ad Watcher - Widget

This is a small GUI wrapper around the Spotify ad watcher that can be packaged into a standalone Windows executable so users don't need a separate Python install.

How to build a single-file exe (Windows):

1. Install requirements and PyInstaller in a build environment:

```powershell
python -m pip install -r requirements.txt pyinstaller
```

2. Build a one-file, windowed executable:

```powershell
pyinstaller --onefile --noconsole --name SpotifyAdWatcher sopty_gui.py
```

3. The built executable will be in the `dist\SpotifyAdWatcher.exe`. Distribute that file to users.

Notes:
- The app uses OS window titles to detect ads; this may not catch every ad case.
- Running media-key emulation (`keyboard`) may require accessibility permissions.



