# Clip Export for Decky Loader

Export saved Steam Game Recording clips from Gaming Mode and send the MP4 to a paired computer on your local network. The Decky menu lists clips by game, date, and length. Exports remux the original H.264/AAC media with `ffmpeg`; they do not re-encode it.

## Set up the computer

For a clean install, download [ClipExportKit-0.1.1.zip](./ClipExportKit-0.1.1.zip), unpack it on your computer, and run the commands below from the resulting `ClipExportKit` folder. A source checkout also works directly.

The receiver needs Python 3.10 or newer and no extra packages. Run it from this project folder:

| Computer | Command |
| --- | --- |
| macOS or Linux | `python3 receiver/receiver.py` |
| Windows | `py -3 receiver\receiver.py` |

On macOS you can also double-click `receiver/Start Clip Receiver.command`. Keep the receiver running while transferring. It prints:

- A URL such as `http://192.168.1.20:57321`
- A six-digit pairing code, valid for 15 minutes
- A Decky installation URL ending in `/ClipExport.zip`

The computer and Deck must be on the same local network. If macOS or Windows asks whether to allow incoming connections to Python, allow them on your private network. Files arrive in `~/Movies/Steam Deck Clips` on macOS or `~/Videos/Steam Deck Clips` on Windows/Linux. Use `--dest "/your/preferred/folder"` to change that.

### Optional macOS login startup

After pairing once, stop the foreground receiver with Ctrl+C and run:

```sh
python3 receiver/install_autostart_macos.py
```

The receiver then starts at login. Keep this project folder in place because the LaunchAgent points to the script here. Its log is `~/Library/Logs/ClipExport-receiver.log`; that log also shows a fresh pairing code if you ever need to pair again.

## Install and pair on Steam Deck

1. Start the receiver on your computer.
2. In Decky Loader, enable **Developer mode** in settings. Under **Developer**, choose **Install Plugin from URL** and enter the installation URL printed by the receiver. You can also copy [ClipExport-0.1.1.zip](./ClipExport-0.1.1.zip) to the Deck and use **Install Plugin from ZIP File**.
3. Open **Clip Export** in the Decky Quick Access Menu. In **Pair a computer**, enter the receiver URL and six-digit code, then select **Pair computer**.
4. Select a clip in the list. Choose **Send to _computer name_** or **Save MP4 on Deck**. Local saves go to `~/Videos/Steam Deck Clips` on the Deck.

Pairing is needed only once for each computer. You can pair multiple computers and choose a destination for each export. After a successful transfer, the receiver checks the byte count and SHA-256 digest before the plugin reports success. It adds a numeric suffix if a file with the same name already exists.

## Why this endpoint

The included receiver is a small HTTP service on your computer. It gives the Decky plugin a stable destination and stores a long random token after one-time six-digit pairing. This is simpler for a dedicated computer than FTP credentials or implementing LocalSend's device discovery and upload negotiation. LocalSend support could be added later as another destination. Valve's [Game Recording help](https://help.steampowered.com/en/faqs/view/23B7-49AD-4A28-9590) also describes a built-in **Send to Other Device** action, which may already work for clips you share through Steam.

The receiver uses plain HTTP, so use it only on a trusted home network. Do not forward port 57321 to the internet. A paired token is stored in Decky's plugin settings and in `~/.config/decky-clip-receiver/config.json` on the computer.

## Recording support

The plugin finds clips under Steam's `userdata/*/gamerecordings/clips` directories. It gets the game ID, date, and recording order from `clip.pb`, and game names from local Steam `appmanifest_*.acf` files. If a game manifest is unavailable, it shows `App <ID>`. It lists saved clips; it does not export the unsaved rolling recording buffer. `ffmpeg` must be available on the Deck (it is included in standard SteamOS installations).

Exports use temporary files in the destination's storage, with a free-space check before starting. Allow roughly twice the size of the raw clip plus 64 MiB of free space.

The package has been tested on macOS and Linux with local export and paired upload, including a 3:12 Steam clip. The Decky menu has automated interaction tests. Pairing worked on Steam Deck hardware; export after the library-path fix still needs a hardware retest. The Deck plugin requests no root access and writes only to its settings/runtime directories and the user's Videos folder.

## Build from source

```sh
npm ci
npm run typecheck
npm run build
npm run test:ui
python3 package_plugin.py
python3 -m unittest discover -s tests -v
```

`ClipExport-0.1.1.zip` is the Decky installation archive. `ClipExportKit-0.1.1.zip` also includes the computer receiver and setup instructions, without the source build dependencies.

For a real saved clip, set `CLIP_SAMPLE_DIR` to its `clip_*` directory and rerun `python3 -m unittest discover -s tests -p test_integration.py -v`.
