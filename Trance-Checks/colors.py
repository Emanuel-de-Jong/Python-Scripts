import os
import re
import pickle
import pandas as pd
import numpy as np
from PIL import Image
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

playlist_ids = {
    "trance": "https://open.spotify.com/playlist/50tBRPNUzxkOzlT6KGixdk",
    # "upbeat": "https://open.spotify.com/playlist/2aRDR4WJr9AoOyP7F9my0Q",
    # "downbeat": "https://open.spotify.com/playlist/5t9rSDRlAGpivgRnydqL7c",
    "uplifting": "https://open.spotify.com/playlist/0D7KTFSRmsJDofhdkhEBCk",
    # "temp_vocal": "https://open.spotify.com/playlist/13Lq2Y3hAy8aEzlzWEZ3fC",
    "breakcore": "https://open.spotify.com/playlist/05nsmLglaAmlvwZNV4uA2Y",
}

playlists = {}
playlist_track_colors = {}
playlist_colors = {}
sp = None

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

def download_playlist_imgs(playlist_name, playlist):
    for item in playlist:
        os.makedirs(f"cache/imgs/{playlist_name}", exist_ok=True)

        track = item['track']

        title = track['name']
        artists = [artist['name'] for artist in track['artists']]
        img_url = track['album']['images'][-1]['url']

        file_name = f"{', '.join(artists)} - {title}.jpg"
        file_name = re.sub(r'[^a-zA-Z0-9_\- .()~!@#$%^&+=]', '', file_name)

        file_path = f"cache/imgs/{playlist_name}/{file_name}"
        if not os.path.exists(file_path):
            img_data = requests.get(img_url).content
            with open(file_path, 'wb') as file:
                file.write(img_data)

def get_track_colors(playlist_name):
    playlist_track_colors[playlist_name] = {}
    img_folder = f"cache/imgs/{playlist_name}"
    for filename in os.listdir(img_folder):
        if filename.endswith(".jpg"):
            img_path = os.path.join(img_folder, filename)
            avg_color = get_average_color(img_path)
            playlist_track_colors[playlist_name][filename[:-4]] = avg_color

def get_average_color(image_path):
    img = Image.open(image_path)

    if img.mode != "RGB":
        img = img.convert("RGB")

    pixels = img.load()

    width, height = img.size
    
    total_color = np.array([0, 0, 0], dtype=int)
    count = 0

    for x in range(0, width, 5):
        for y in range(0, height, 5):
            pixel_color = pixels[x, y]
            total_color += np.array(pixel_color[:3])
            count += 1

    avg_color = total_color // count
    return tuple(avg_color)

def get_average_color_of_playlist(playlist):
    total_color = np.array([0, 0, 0], dtype=int)
    for color in playlist.values():
        total_color += np.array(color)

    playlist_color = total_color // len(playlist)
    playlist_color = list(playlist_color)
    lowest = int(min(playlist_color) * 0.9)
    highest = max(playlist_color)
    times = min(int(highest * 1.3), 255) // (highest - lowest)
    for channel in range(3):
        playlist_color[channel] -= lowest
        playlist_color[channel] = int(playlist_color[channel] * times)
    
    return tuple(playlist_color)

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
        download_playlist_imgs(playlist_name, playlist)
    
    for playlist_name in playlists.keys():
        get_track_colors(playlist_name)

    for playlist_name, playlist in playlist_track_colors.items():
        playlist_colors[playlist_name] = get_average_color_of_playlist(playlist)


def main():
    create_playlists()

    for playlist_name, color in playlist_colors.items():
        print(f"{playlist_name}: {color}")

        color_img = Image.new("RGB", (64, 64), color)
        color_img.save(f"results/colors/{playlist_name}.jpg")

if __name__ == "__main__":
    main()
