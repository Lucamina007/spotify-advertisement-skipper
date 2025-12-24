import time
import psutil
import subprocess
import os
import keyboard
import asyncio

# Attempt to import WinRT, with a fallback flag
try:
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as SessionManager
    WINRT_AVAILABLE = True
except ImportError:
    WINRT_AVAILABLE = False
    print("Warning: WinRT modules not found. Falling back to window title detection.")

# Configuration
CHECK_INTERVAL = 2 
RESTART_COOLDOWN = 20  # Safe buffer for 2025 Spotify updates
SPOTIFY_PATH = os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Roaming\Spotify\Spotify.exe")

async def is_ad_playing():
    """Detects ads using Media Session (Primary) or Window Titles (Fallback)."""
    if WINRT_AVAILABLE:
        try:
            manager = await SessionManager.request_async()
            sessions = manager.get_sessions()
            for session in sessions:
                if "spotify" in session.source_app_user_model_id.lower():
                    info = await session.try_get_media_properties_async()
                    # 2025 Detection: Ads have empty artists or specific titles
                    if not info.artist or info.title.lower() in ["advertisement", "spotify", "sponsored"]:
                        return True
        except Exception:
            pass # Fallback to window check if API glitche

    # Fallback/Safety: Basic window check but with strict "No Artist" logic
    import pygetwindow as gw
    for window in gw.getWindowsWithTitle('Spotify'):
        if window.title.lower() == "advertisement":
            return True
    return False

def kill_spotify():
    for p in psutil.process_iter(['name']):
        try:
            if p.info['name'] and 'spotify' in p.info['name'].lower():
                p.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

def open_spotify():
    if os.path.isfile(SPOTIFY_PATH):
        subprocess.Popen([SPOTIFY_PATH], creationflags=subprocess.DETACHED_PROCESS)
    else:
        os.startfile("spotify:")

async def main():
    print("--- Spotify Ad-Skipper (2025 Multi-Engine) ---")
    while True:
        try:
            if await is_ad_playing():
                print("Ad Detected! Restarting...")
                kill_spotify()
                time.sleep(2)
                open_spotify()
                
                time.sleep(8) # Wait for Spotify 2025 UI to load
                keyboard.send("play/pause media")
                # To skip to the next track automatically after restarting
                keyboard.send("next track")

                
                print(f"Cooldown: {RESTART_COOLDOWN}s")
                await asyncio.sleep(RESTART_COOLDOWN)
            
            await asyncio.sleep(CHECK_INTERVAL)
        except Exception as e:
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())

