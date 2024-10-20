import os
import re
import pickle
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

TITLE_WORD_BLACKLIST = [
    "mix", "mixed", "remix", "edit",
    "extended", "radio",
    "feat", "ft", "featuring",
    "original", "version", "live", "edition", "anthem",
    "asot"
]
blacklist_str = "|".join(TITLE_WORD_BLACKLIST)

playlist_ids = {
    "trance": "https://open.spotify.com/playlist/50tBRPNUzxkOzlT6KGixdk",
    "upbeat": "https://open.spotify.com/playlist/2aRDR4WJr9AoOyP7F9my0Q",
    "downbeat": "https://open.spotify.com/playlist/5t9rSDRlAGpivgRnydqL7c",
    "uplifting": "https://open.spotify.com/playlist/0D7KTFSRmsJDofhdkhEBCk",
}

playlists = {}
playlist_tracks = {}
sp = None

intentionally_deleted_tracks = [
    "CJ Stone - Shining Star - Rework",
    "Delerium, Sarah McLachlan, Airscape - Silence - Airscape Remix Edit",
    "Delerium, Tiësto - Silence - DJ Tiësto's in Search of Sunrise Remix",
    "Miyuki - River Flows in You",
    "Husman - Desire",
    "Natalie Gioia, Ultimate, Moonsouls - Frozen",
    "Kiyoi & Eky, Ade DokQ, Angel Falls - Away From Home",
    "Roger Shah, Ambedo, Yelow, Capri - Greatest Gift",
    "Roger Shah, Ambedo - Birds Of Prey",
    "Armin van Buuren, Trevor Guthrie - This Is What It Feels Like - Armin van Buuren 2023 Remix",
    "Paul Denton - Tremor",
    "Jerome Isma-Ae, Weekend Heroes - In The Dark - Extended Mix",
    "Armin van Buuren - Space Case - Extended Mix",
    "Lost Emotions, Anthya - Heal - Mike van Fabio Remix",
    "M6 - Fade 2 Black - Original Mix",
    "Paul van Dyk - Words",
    "Majai, Alex M.O.R.P.H. - Phoria (ASOT 1151) - Alex M.O.R.P.H. Remix",
]

def get_local_playlist(playlist_name):
    if os.path.exists(f"cache/{playlist_name}.pkl"):
        with open(f"cache/{playlist_name}.pkl", "rb") as f:
            return pickle.load(f)

def get_playlist_tracks(playlist_id):
    global sp

    if not sp:
        # Client info is in environment variables
        creds = SpotifyClientCredentials()
        sp = spotipy.Spotify(client_credentials_manager=creds)

    try:
        results = sp.playlist_items(playlist_id)
        tracks = results['items']
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
    except Exception as e:
        print(f"Error accessing playlist: {str(e)}")
        return
    
    return tracks

def playlist_to_tracks(playlist):
    tracks = []
    for item in playlist:
        track = item['track']

        title = track['name']
        title = sanitize_title(title)
        artists = [artist['name'] for artist in track['artists']]
        artists = sanitize_artists(artists)
        album = track['album']['name']
        album = sanitize_title(album)

        tracks.append({
            "id": track['id'],
            "title": title,
            "artists": artists,
            "album": album
        })

    return tracks

def sanitize_title(title):
    title = title.split(" - ")[0]
    title = re.sub(r'[^a-zA-Z0-9 ]', '', title).lower()
    title = re.sub(r'\b(?:' + blacklist_str + r')\b', '', title)
    title = re.sub(r'\s+', ' ', title).strip()

    return title

def sanitize_artists(artists):
    for i, artist in enumerate(artists):
        artist = re.sub(r'[^a-zA-Z0-9, ]', '', artist).lower()
        artist = re.sub(r'\s+', ' ', artist).strip()

        artists[i] = artist

    return artists

def create_playlists():
    os.makedirs("cache", exist_ok=True)

    for playlist_name in playlist_ids.keys():
        playlists[playlist_name] = get_local_playlist(playlist_name)

    for playlist_name, playlist in playlists.items():
        if not playlist:
            playlist = get_playlist_tracks(playlist_ids[playlist_name])
            playlists[playlist_name] = playlist
            with open(f"cache/{playlist_name}.pkl", "wb") as f:
                pickle.dump(playlist, f)

    for playlist_name, playlist in playlists.items():
        playlist_tracks[playlist_name] = playlist_to_tracks(playlist)

def get_matches(main_playlist):
    main_tracks = playlist_tracks[main_playlist]
    matches = {}
    seen_pairs = set()

    for playlist_name, tracks in playlist_tracks.items():
        matches[playlist_name] = {}
        for main_track in main_tracks:
            main_id = main_track["id"]

            for track in tracks:
                track_id = track["id"]
                track_pair = frozenset([main_id, track_id])

                if main_id == track_id or track_pair in seen_pairs:
                    continue

                if main_track["title"] in track["title"]:
                    for artist in main_track["artists"]:
                        if artist in track["artists"]:
                            matches[playlist_name][main_id + track_id] = (main_track, track)
                            seen_pairs.add(track_pair)
                            break
        
        if len(matches[playlist_name]) == 0:
            del matches[playlist_name]
    
    return matches

def write_matches(main_playlist, matches):
    lines = []
    lines.append(f"===============================")
    lines.append(f"Main playlist: {main_playlist}")
    for playlist_name, matches in matches.items():
        lines.append(f"Matches for {playlist_name}:")

        for match in matches.values():
            main_track = match[0]
            track = match[1]
            lines.append(f"{main_track['title']} VS {track['title']} || {main_track['artists']} VS {track['artists']}")
        
        lines.append("")
    
    return lines

def get_old_tracks():
    old_playlist = pd.read_csv('data/dj_kbot_trance.csv')
    old_tracks = []
    for _, row in old_playlist.iterrows():
        title = sanitize_title(row['Track Name'])
        artists = sanitize_artists(row['Artist Name(s)'].split(','))
        old_tracks.append({
            "title": title,
            "artists": artists,
            "og_title": row['Track Name'],
            "og_artists": row['Artist Name(s)'].split(',')
        })
    
    return old_tracks

def get_missing_tracks(old_tracks):
    missing_tracks = []
    for old_track in old_tracks:
        is_track_found = False
        for tracks in playlist_tracks.values():
            for track in tracks:
                if track['title'] in old_track['title'] and any(artist in old_track['artists'] for artist in track['artists']):
                    is_track_found = True
                    break

            if is_track_found:
                break
        
        if not is_track_found:
            missing_tracks.append(old_track)
    
    return missing_tracks

def write_missing(missing_tracks):
    lines = []
    lines.append("intentionally_deleted_tracks = [")
    for track in missing_tracks:
        track_str = f"{', '.join(track['og_artists'])} - {track['og_title']}"
        if track_str in intentionally_deleted_tracks:
            continue
        
        lines.append(f"    \"{track_str}\",")
    lines.append("]")
    
    return lines

def find_dupes():
    create_playlists()

    should_write_all_playlists = True # True False
    main_playlist = "trance" # trance upbeat downbeat uplifting
    
    lines = []
    for playlist_name in playlists.keys():
        if should_write_all_playlists or playlist_name == main_playlist:
            matches = get_matches(playlist_name)
            lines.extend(write_matches(playlist_name, matches))

    os.makedirs("results", exist_ok=True)
    with open(f"results/dupes.txt", "w") as f:
        for line in lines:
            # print(line)
            f.write(f"{line}\n")

def find_missing():
    create_playlists()

    old_tracks = get_old_tracks()
    missing_tracks = get_missing_tracks(old_tracks)
    
    lines = write_missing(missing_tracks)

    os.makedirs("results", exist_ok=True)
    with open(f"results/missing.txt", "w") as f:
        for line in lines:
            # print(line)
            f.write(f"{line}\n")

def find_not_album():
    create_playlists()

    not_album_tracks = {}
    for playlist_name, tracks in playlist_tracks.items():
        not_album_tracks[playlist_name] = []
        for track in tracks:
            if track['title'] not in track['album']:
                not_album_tracks[playlist_name].append(track)
    
    lines = []
    for playlist_name, tracks in not_album_tracks.items():
        lines.append(f"\n{playlist_name}:")
        for track in tracks:
            lines.append(f"{track['title']} || {track['album']}")
    
    os.makedirs("results", exist_ok=True)
    with open(f"results/not_album.txt", "w") as f:
        for line in lines:
            # print(line)
            f.write(f"{line}\n")

if __name__ == "__main__":
    find_dupes()
    find_missing()
    find_not_album()
