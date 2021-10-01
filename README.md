# Google Sheet to Spotify Playlist

This script reads a range from a Google Sheet, parses artist and track names, and uses the Spotify api to find tracks and add them to a playlist

Prerequisites:

- Enabled Google Sheets API and credentials in a `google_credentials.json` file
- Spotify app access credentials in a `spotify_credentials.json` file
- ID of the spreadsheet (`SPREADSHEET_ID`) and playlist (`PLAYLIST_ID`) in a `resources.py` file
