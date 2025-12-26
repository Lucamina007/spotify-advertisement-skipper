import time
import psutil
import subprocess
import os
import keyboard
import asyncio
try:
    from mutagen import File as MutagenFile
    MUTAGEN_AVAILABLE = True
except Exception:
    MutagenFile = None
    MUTAGEN_AVAILABLE = False
import wave

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
DEBUG = True  # set False to silence WinRT/media debug output
# Heuristic keywords (multilingual) often found in ad titles/descriptions
AD_KEYWORDS = [
    'advert', 'sponsored', 'sponsor', 'promo', 'offerta', 'acquista', 'acquista',
    'scopri', 'compra', 'visita', 'deal', 'scont', 'sponsorizzato', 'spot',
    'sponsor', 'advertisement', 'buy', 'purchase'
]
AD_BRANDS = [
    'disney', 'netflix', 'prime video', 'amazon', 'youtube',
    'vodafone', 'sony', 'coca-cola', 'pepsi', 'mcdonald', 'burger king', 'autoteam',
    'spotify',  'google', 'microsoft'
]
AD_BROADCAST_TOKENS = ['+', 'italia', 'tv', 'channel', 'official']

# (Title-change timing heuristic and ad-look helper removed — using metadata heuristics only)

async def is_ad_playing():
    """Detects ads using Media Session (Primary) or Window Titles (Fallback)."""
    if WINRT_AVAILABLE:
        try:
            manager = await SessionManager.request_async()
            sessions = manager.get_sessions()
            for session in sessions:
                if "spotify" in session.source_app_user_model_id.lower():
                    info = await session.try_get_media_properties_async()
                    if DEBUG:
                        try:
                            print("DEBUG: session app:", session.source_app_user_model_id)
                            print("DEBUG: title:", getattr(info, 'title', None))
                            print("DEBUG: artist:", getattr(info, 'artist', None))
                            print("DEBUG: duration (raw):", getattr(info, 'duration', None))
                            props = getattr(info, 'properties', None)
                            if props:
                                sample_keys = list(props.keys())[:12]
                                sample = {k: props[k] for k in sample_keys}
                                print("DEBUG: properties sample:", sample)
                        except Exception as _e:
                            print("DEBUG: failed to print media info:", _e)
                    # 1) Duration-based detection (when available from media session)
                    try:
                        duration_seconds = None
                        dur = getattr(info, 'duration', None)
                        if dur is not None:
                            try:
                                duration_seconds = float(dur.total_seconds())
                            except Exception:
                                try:
                                    duration_seconds = float(dur)
                                except Exception:
                                    duration_seconds = None

                        # WinRT may expose duration via properties in 100-ns units
                        if duration_seconds is None:
                            props = getattr(info, 'properties', None)
                            if props:
                                for key in ('System.Media.Duration', 'Duration', 'duration'):
                                    if key in props:
                                        try:
                                            val = props[key]
                                            duration_seconds = int(val) / 10_000_000
                                        except Exception:
                                            try:
                                                duration_seconds = float(val)
                                            except Exception:
                                                duration_seconds = None
                                        break

                        if duration_seconds is not None:
                            if duration_seconds < 60.0:
                                return True
                        # (playback position-based remaining-time detection removed)
                    except Exception:
                        pass

                    # 2) Existing metadata checks: empty artist or known ad titles
                    try:
                        title = (info.title or '').lower()
                        artist = info.artist
                    except Exception:
                        title = ''
                        artist = None

                    # 3) Heuristic checks: artist empty OR explicit titles
                    if not artist or title in ["advertisement", "spotify", "sponsored"]:
                        if DEBUG:
                            print("DEBUG: detected ad by empty-artist/title rule:", title, artist)
                        return True

                    # 4) Heuristic: title equals artist (common for short promo clips)
                    try:
                        if title and artist and title == (str(artist).lower()):
                            if DEBUG:
                                print("DEBUG: detected ad because title == artist:", title)
                            return True
                    except Exception:
                        pass

                    # 5) Heuristic: keyword matching in title or artist
                    lt = title.lower() if title else ''
                    la = str(artist).lower() if artist else ''
                    for kw in AD_KEYWORDS:
                        if kw in lt or kw in la:
                            if DEBUG:
                                print(f"DEBUG: detected ad by keyword '{kw}' in title/artist:", title, artist)
                            return True

                    # 6) Brand/broadcaster heuristics (catch "Disney+ Italia", etc.)
                    for b in AD_BRANDS:
                        if b in lt or b in la:
                            if DEBUG:
                                print(f"DEBUG: detected ad by brand '{b}' in title/artist:", title, artist)
                            return True

                    for token in AD_BROADCAST_TOKENS:
                        if token in lt or token in la:
                            if DEBUG:
                                print(f"DEBUG: detected ad by broadcast token '{token}' in title/artist:", title, artist)
                            return True

                    # (title-change timing heuristic removed)
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


def get_duration_seconds(path):
    """Return duration in seconds for a local audio file or None if unknown.

    Uses mutagen when available (supports many formats) and falls back to
    the stdlib `wave` reader for WAV files.
    """
    if not path:
        return None
    # Try mutagen first (broad format support)
    try:
        if MUTAGEN_AVAILABLE:
            audio = MutagenFile(path)
            if audio is not None and hasattr(audio, 'info'):
                length = getattr(audio.info, 'length', None)
                if length:
                    return float(length)
    except Exception:
        pass

    # WAV fallback using stdlib
    try:
        if path.lower().endswith('.wav'):
            with wave.open(path, 'rb') as w:
                frames = w.getnframes()
                rate = w.getframerate()
                return frames / float(rate)
    except Exception:
        pass

    return None


def is_ad_file(path, threshold_seconds=60.0):
    """Return True if the file at `path` is shorter than `threshold_seconds`.

    This is useful for local files (downloads, local previews). For streaming
    sources like Spotify's online stream, you'll need a URI that points to a
    local file (e.g., file://...) or a downloaded copy.
    """
    dur = get_duration_seconds(path)
    if dur is None:
        return False
    return dur < float(threshold_seconds)


def is_ad_from_uri(uri, threshold_seconds=60.0):
    """Handle simple file:// URIs or plain filesystem paths."""
    if not uri:
        return False
    if uri.startswith('file://'):
        path = uri[len('file://'):]
    else:
        path = uri
    return is_ad_file(path, threshold_seconds)

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

