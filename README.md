# ObsidianSync

Sync your Obsidian vault from your Mac to your Android device over local Wi-Fi — no cloud, no
account, just a QR code and your local network.

- **`desktop-client/`** — Python (tkinter) app. Shows a pairing QR code, runs a local HTTP server,
  and serves your vault's file manifest and contents.
- **`mobile-app/`** — Android (Kotlin + Jetpack Compose) app. Scans the QR code, connects to the
  desktop over Wi-Fi, and syncs the vault into a folder you choose.

Sync is one-way: Mac → Android. Each sync compares file hashes and only transfers what changed,
and removes files on Android that no longer exist in the Mac vault.

## Screenshots / states

The desktop app is a single card that walks through:

- **Waiting** — shows the pairing QR code
- **Connected** — phone has paired, ready to sync
- **Syncing** — live progress (spinner + `done/total` files)
- **Complete** — green checkmark with a summary of what changed
- **Error** — shown on sync failure or if the phone drops off the network mid-sync (auto-detected
  after 15s of silence), with a **Retry** button

Settings (vault folder, port) and the activity log live behind the ⚙ and ☰ icons in the header.

## Running the desktop app

```bash
cd desktop-client
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

> tkinter needs Tcl/Tk support. On macOS with Homebrew Python, if `import tkinter` fails, run
> `brew install python-tk@<your-python-version>`.

1. Click the ⚙ icon → **Choose Vault…** and select your Obsidian vault folder.
2. Scan the QR code from the Android app.
3. Click **New QR Code** any time to invalidate the old pairing and generate a fresh token.

Both devices must be on the same Wi-Fi network (or one device's personal hotspot) — this app never
talks to the internet.

## Running the Android app

Open `mobile-app/` in Android Studio and run it on a physical device (recommended, for the camera)
or an emulator with a virtual camera configured.

1. Tap **Scan QR Code** and point the camera at the desktop's QR code.
   - On first launch you'll be asked to grant **local network access** — this is required on
     Android 17+ (`ACCESS_LOCAL_NETWORK`) for the app to reach devices on your LAN at all; without
     it, connections silently time out.
2. Tap **Choose Folder** and pick (or create) a folder on your phone to receive the vault.
3. Tap **Sync Now**. Status and last-synced time are shown on screen.

## How it works

- The desktop exposes a small Flask API, all guarded by a per-session token embedded in the QR
  code:
  - `GET /pair` — confirms the token and reports the desktop's device name
  - `GET /manifest` — the full file list (path, SHA-256 hash, size, mtime)
  - `GET /sync-begin?total=N` — phone reports how many files it's about to download, so the desktop
    can show real progress
  - `GET /file?path=...` — file contents; each call also advances the desktop's progress counter
  - `GET /sync-complete?status=...&updated=...&deleted=...` — phone reports the final result
  - `GET /health` — plain liveness check
- The Android app keeps a small local record (`sync_state.json`, in app-private storage) of what it
  last wrote, so repeat syncs only download changed files and delete files removed from the vault.
- Vault files on Android are written via the Storage Access Framework (SAF) to the folder you
  picked, so no broad storage permission is needed.
- If the phone goes silent mid-sync (Wi-Fi drop, app killed, etc.) the desktop times out after 15s
  of no progress and moves to the error state instead of hanging on "Syncing…" forever.

## Notes / limitations

- Pairing token is per-session (regenerated on desktop restart or "New QR Code"); there's no
  persistent device pairing list yet.
- Sync is one-way only (Mac → Android); editing notes on the phone and syncing them back isn't
  supported.
- If the phone and Mac are on different Wi-Fi networks — or the network enforces AP/client
  isolation — pairing will fail; there is no cloud fallback by design.

## Contributing

Issues and PRs welcome. This is a small personal-use tool kept intentionally simple — please open
an issue to discuss anything beyond a small fix or improvement before sending a large PR.

## License

MIT — see [LICENSE](LICENSE).
