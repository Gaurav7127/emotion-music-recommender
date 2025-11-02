import os
import json
import cv2
import random
import spotipy
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials

# ---------------- Load Environment Variables ----------------
load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "180d104b33f14c838cb8576c76a06ba6")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "93c54c54e6dd442da022d927d7cf34cf")

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- User Data (JSON File) ----------------
USERS_FILE = "users.json"
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

# ---------------- Webcam Setup ----------------
camera = cv2.VideoCapture(0)

def generate_frames():
    """Continuously capture frames from webcam."""
    while True:
        success, frame = camera.read()
        if not success:
            break
        frame = cv2.flip(frame, 1)
        ret, buffer = cv2.imencode(".jpg", frame)
        frame = buffer.tobytes()
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

@app.route("/video_feed")
def video_feed():
    """Stream webcam feed to browser."""
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

# ---------------- Simple Emotion Detection (Mock) ----------------
def detect_emotion(frame):
    emotions = ["happy", "sad", "angry", "neutral"]
    return random.choice(emotions)

# ---------------- Spotify Setup ----------------
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

# 🎵 Your Custom Playlists for Each Emotion
EMOTION_PLAYLISTS = {
    "happy": "1u2zThsNr5yGIPvYYhffRa",
    "sad": "7ymUBqQy9JAvuajmF7U2xh",
    "angry": "0N7bTAuO8ejUjW2YkyZfRB",
    "neutral": "7EClwmhqu7mg4JvUI9z5DT"
}

# ---------------- Login / Register System ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        users = load_users()
        if username in users:
            return "User already exists. Try logging in.", 400

        users[username] = {"password": generate_password_hash(password)}
        save_users(users)
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        users = load_users()
        user = users.get(username)

        if not user or not check_password_hash(user["password"], password):
            return "Invalid username or password.", 401

        session["user"] = username
        return redirect(url_for("index"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# ---------------- Routes ----------------
@app.route("/")
def index():
    """Home page — choose webcam or emoji."""
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", username=session["user"])

@app.route("/webcam")
def webcam_page():
    """Webcam-based emotion detection."""
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("emotion.html", username=session["user"])

@app.route("/emoji")
def emoji_page():
    """Emoji-based song recommendation."""
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("emoji.html", username=session["user"])

@app.route("/get_emotion")
def get_emotion():
    """Detect emotion via webcam (mocked) and return songs."""
    success, frame = camera.read()
    if not success:
        return jsonify({"error": "Unable to access camera"})

    emotion = detect_emotion(frame)
    print(f"🎭 Detected Emotion: {emotion}")
    return jsonify(get_spotify_tracks(emotion))

@app.route("/emoji_select", methods=["POST"])
def emoji_select():
    """When user selects an emoji manually."""
    data = request.get_json()
    emotion = data.get("emotion", "neutral")
    print(f"😊 Emoji Selected: {emotion}")
    return jsonify(get_spotify_tracks(emotion))

# ---------------- Spotify Recommendation Logic ----------------
def get_spotify_tracks(emotion):
    """Fetch up to 20 tracks from your curated emotion playlists."""
    tracks_out = []
    playlist_id = EMOTION_PLAYLISTS.get(emotion)

    if playlist_id:
        try:
            results = sp.playlist_tracks(playlist_id, limit=20)
            for item in results["items"]:
                track = item.get("track")
                if track:
                    tracks_out.append({
                        "id": track["id"],
                        "name": track["name"],
                        "artists": ", ".join([a["name"] for a in track["artists"]]),
                        "album_cover": track["album"]["images"][0]["url"] if track["album"]["images"] else "",
                        "preview_url": track["preview_url"],
                        "spotify_url": track["external_urls"]["spotify"]
                    })
        except Exception as e:
            print("⚠️ Playlist fetch error:", e)
    else:
        print("⚠️ No playlist found for emotion:", emotion)

    return {"emotion": emotion, "tracks": tracks_out[:20]}

# ---------------- Run Flask ----------------
if __name__ == "__main__":
    print("🚀 Flask running at: http://127.0.0.1:5000")
    app.run(debug=True)
