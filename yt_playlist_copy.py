#!/usr/bin/env python3
"""
Copy every video from any public/unlisted YouTube playlist into a playlist you own.

Setup:
  pip install google-api-python-client google-auth-oauthlib
  Put your OAuth client file next to this script as client_secret.json

Usage:
  python yt_playlist_copy.py SOURCE TARGET
  python yt_playlist_copy.py SOURCE --create "My new playlist"
  python yt_playlist_copy.py SOURCE TARGET --dry-run

SOURCE / TARGET can be a full playlist URL or just the playlist ID.
Re-running is safe: videos already in the target are skipped, so if you hit
the daily quota you can just run it again tomorrow and it picks up where it stopped.
"""

import argparse
import json
import os
import sys
from urllib.parse import urlparse, parse_qs

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRET = "client_secret.json"
TOKEN_FILE = "token.json"


def get_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET):
                sys.exit(f"Missing {CLIENT_SECRET}. See setup steps in the script header.")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def extract_playlist_id(value):
    """Accept a full URL or a raw playlist ID."""
    if "://" in value or "youtube.com" in value:
        if "://" not in value:
            value = "https://" + value
        qs = parse_qs(urlparse(value).query)
        if "list" in qs:
            return qs["list"][0]
        sys.exit(f"Couldn't find a playlist ID in: {value}")
    return value.strip()


def fetch_playlist_videos(yt, playlist_id):
    """Return a list of (video_id, title) in playlist order. Skips deleted/private."""
    videos, token = [], None
    while True:
        resp = yt.playlistItems().list(
            part="snippet,contentDetails,status",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=token,
        ).execute()
        for item in resp.get("items", []):
            title = item["snippet"].get("title", "")
            if title in ("Deleted video", "Private video"):
                continue
            vid = item["contentDetails"]["videoId"]
            videos.append((vid, title))
        token = resp.get("nextPageToken")
        if not token:
            return videos


def create_playlist(yt, name, privacy="private"):
    resp = yt.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {"title": name},
            "status": {"privacyStatus": privacy},
        },
    ).execute()
    return resp["id"]


def is_quota_error(err: HttpError):
    try:
        data = json.loads(err.content.decode())
        reasons = [e.get("reason") for e in data["error"].get("errors", [])]
        return "quotaExceeded" in reasons or "rateLimitExceeded" in reasons
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description="Copy a YouTube playlist into one of yours.")
    ap.add_argument("source", help="Source playlist URL or ID (anyone's)")
    ap.add_argument("target", nargs="?", help="Target playlist URL or ID (must be yours)")
    ap.add_argument("--create", metavar="NAME", help="Create a new playlist with this name instead of using TARGET")
    ap.add_argument("--public", action="store_true", help="Make a newly created playlist public (default: private)")
    ap.add_argument("--dry-run", action="store_true", help="Show what would be added without changing anything")
    args = ap.parse_args()

    if not args.target and not args.create:
        ap.error("Provide a TARGET playlist or use --create NAME")

    yt = get_service()
    source_id = extract_playlist_id(args.source)

    print("Reading source playlist...")
    try:
        source = fetch_playlist_videos(yt, source_id)
    except HttpError as e:
        sys.exit(f"Couldn't read source playlist (private or wrong ID?): {e}")
    print(f"  {len(source)} available videos found.")

    if args.create:
        if args.dry_run:
            target_id, existing = "(new playlist)", set()
        else:
            target_id = create_playlist(yt, args.create, "public" if args.public else "private")
            existing = set()
            print(f"Created playlist '{args.create}' ({target_id})")
    else:
        target_id = extract_playlist_id(args.target)
        try:
            existing = {vid for vid, _ in fetch_playlist_videos(yt, target_id)}
        except HttpError as e:
            sys.exit(f"Couldn't read target playlist: {e}")
        print(f"  Target already has {len(existing)} videos.")

    todo = [(v, t) for v, t in source if v not in existing]
    skipped = len(source) - len(todo)
    print(f"\nTo add: {len(todo)}  |  Already there: {skipped}")
    print(f"Estimated quota: {len(todo) * 50} units (default daily limit is 10,000)\n")

    if args.dry_run:
        for i, (_, title) in enumerate(todo, 1):
            print(f"  {i:>4}. {title}")
        return

    added = 0
    for i, (vid, title) in enumerate(todo, 1):
        try:
            yt.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": target_id,
                        "resourceId": {"kind": "youtube#video", "videoId": vid},
                    }
                },
            ).execute()
            added += 1
            print(f"  [{i}/{len(todo)}] added: {title}")
        except HttpError as e:
            if is_quota_error(e):
                print(f"\nDaily quota hit after {added} videos. Run the same command tomorrow to continue.")
                break
            print(f"  [{i}/{len(todo)}] FAILED: {title} -> {e.resp.status}")

    print(f"\nDone. Added {added} video(s).")


if __name__ == "__main__":
    main()
