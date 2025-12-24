import time
import psutil
import subprocess
import pygetwindow as gw
import keyboard
import os
import threading
import signal
import sys

CHECK_INTERVAL = 5

SPOTIFY_PATH = os.path.expandvars(
    r"C:\Users\%USERNAME%\AppData\Roaming\Spotify\Spotify.exe"
)

STOP_EVENT = threading.Event()


def is_spotify_running():
    for p in psutil.process_iter(['name']):
        if p.info['name'] and 'spotify' in p.info['name'].lower():
            return True
    return False


def close_spotify():
    for p in psutil.process_iter(['name']):
        if p.info['name'] and 'spotify' in p.info['name'].lower():
            try:
                p.terminate()
            except Exception:
                pass


def open_spotify():
    if os.path.isfile(SPOTIFY_PATH):
        subprocess.Popen(SPOTIFY_PATH)
    else:
        os.startfile("spotify:")


def spotify_ad_playing():
    keywords = ("advertisement", "spotify free", "sponsored", "ad:")
    try:
        titles = gw.getAllTitles()
    except Exception:
        return False

    for t in titles:
        if not t:
            continue
        t = t.lower()
        if any(k in t for k in keywords):
            return True
    return False


def press_play():
    time.sleep(4)
    try:
        keyboard.send("play/pause media")
    except Exception:
        pass


def watcher():
    print("Spotify watcher running (headless)")
    spotify_seen = False

    while not STOP_EVENT.is_set():
        try:
            if is_spotify_running():
                spotify_seen = True
                if spotify_ad_playing():
                    print("Ad detected → restarting Spotify")
                    close_spotify()
                    time.sleep(3)
                    open_spotify()
                    press_play()
            else:
                spotify_seen = False

            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print("Error:", e)
            time.sleep(CHECK_INTERVAL)


def shutdown_handler(sig, frame):
    STOP_EVENT.set()
    sys.exit(0)

def main():
    while True:
        try:
            watcher()
        except Exception as e:
            with open("sopty_error.log", "a") as f:
                f.write(str(e) + "\n")
            time.sleep(5)  # prevent restart storm


if __name__ == "__main__":
    main()
