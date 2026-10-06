# YouTube Playlist Copier

Copy every video from **any public or unlisted YouTube playlist** into a playlist **you own**, in one command. No more adding videos one by one.

YouTube's "Save playlist" button only saves someone's playlist as a separate copy. This tool lets you merge it into a playlist you already have, or spin up a new one.

## Features

- Works with full playlist URLs or raw playlist IDs
- Copy into an existing playlist or create a new one with `--create`
- Skips videos already in the target, so re-running is always safe
- Skips deleted and private videos automatically
- `--dry-run` previews what would be added without changing anything
- Handles YouTube's daily API quota gracefully: it stops cleanly and resumes next time

## Requirements

- Python 3.9+
- A free Google Cloud project with the YouTube Data API v3 enabled

## Setup

### 1. Install dependencies

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Get Google API credentials (one-time, free)

1. Go to the [Google Cloud Console](https://console.cloud.google.com) and create a new project.
2. Open **APIs & Services → Library**, search for **YouTube Data API v3**, and click **Enable**.
3. Go to **Credentials → Create credentials** and choose **User data** (this creates an OAuth client, not an API key).
4. Configure the consent screen: choose **External**, enter an app name and your email.
5. Create the OAuth client with application type **Desktop app**.
6. Download the JSON file and rename it to **`client_secret.json`**, then place it next to the script.
7. Under **Google Auth Platform → Audience**, add your own Google account as a **Test user**.

> Keep the app in **Testing** mode. You don't need to publish it for personal use.

## Usage

```bash
# Copy into an existing playlist of yours
python yt_playlist_copy.py "SOURCE_PLAYLIST_URL" "YOUR_PLAYLIST_URL"

# Create a new private playlist and copy into it
python yt_playlist_copy.py "SOURCE_PLAYLIST_URL" --create "My new playlist"

# Make the new playlist public
python yt_playlist_copy.py "SOURCE_PLAYLIST_URL" --create "My new playlist" --public

# Preview only, nothing is changed
python yt_playlist_copy.py "SOURCE_PLAYLIST_URL" "YOUR_PLAYLIST_URL" --dry-run
```

Always wrap URLs in quotes. On Windows, an unquoted `&` splits the command and cuts the link short.

On the first run, a browser window opens for Google login. Click **Advanced → Go to (your app name)** past the "unverified app" warning (expected for your own project) and allow access. The login is then cached in `token.json`.

## How it works

1. Reads the source playlist through the YouTube Data API (`playlistItems.list`), paginating 50 videos at a time.
2. Reads the target playlist to find videos already there.
3. Adds each missing video with `playlistItems.insert`.

## API quota

Each added video costs **50 quota units**, and the default daily limit is **10,000 units**, which is about **200 videos per day**. If the limit is hit, the script stops and tells you. Run the same command the next day and it continues where it left off.

## Troubleshooting

| Problem | Fix |
|---|---|
| `access blocked` at login | Add your Google account as a Test user (Audience page in Google Auth Platform) |
| `Missing client_secret.json` | Download the OAuth Desktop credentials and rename the file exactly |
| `Couldn't read source playlist` | The playlist is private, or the ID is wrong |
| Insert calls fail with 403 | You logged in with an account that doesn't own the target playlist. Delete `token.json` and log in again |
| Login expires after a week | Normal while the app is in Testing mode. Just log in again |
| Link cut off on Windows | Put the URL in quotes |

## Security

`client_secret.json` and `token.json` are personal credentials. They are listed in `.gitignore`, so **never commit them**. If you leak either, delete the credential in the Cloud Console and create a new one.

## License

MIT
https://docs.google.com/document/d/1lfXUhg2SESIR0j-3ztEQeuxj2nBEzY0TBspsaojPdnI/edit?usp=sharing
