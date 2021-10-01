import os.path
from pprint import pprint

import pandas as pd
import spotipy

# import click
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from spotipy.oauth2 import SpotifyOAuth

from resources import PLAYLIST_ID, SPREADSHEET_ID

# Google Things
# If modifying these scopes, delete the file token.json.
GOOGLE_SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Spotify things
SPOTIFY_SCOPES = [
    'user-library-read',
    'playlist-modify-private',
    'playlist-read-private',
    'playlist-modify-public',
    'playlist-read-collaborative',
]
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SPOTIFY_SCOPES))


def get_data_from_sheets():

    max_range = 500
    RANGE = f'A3:C{max_range}'

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', GOOGLE_SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', GOOGLE_SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return

    df = pd.DataFrame(values, columns=['Artist', 'Track', 'Suggested By']).dropna()

    return df


def main():

    df = get_data_from_sheets()

    # print(df)

    existing_tracks = []
    offset = 0
    while True:
        response = sp.playlist_items(
            PLAYLIST_ID,
            offset=offset,
            fields='items.track.id,total',
            additional_types=['track'],
        )

        if len(response['items']) == 0:
            break
        offset = offset + len(response['items'])
        existing_tracks += [i['track']['id'] for i in response['items']]

    tracks = []
    for index, row in df.iterrows():

        query = row['Track'] + ' NOT live NOT feat artist:' + row['Artist']

        track = sp.search(query, limit=1, type='track', market='NL')

        print(
            ('For: ' + row['Artist']).ljust(35) + row['Track'].ljust(35),
            end='',
            # fg='bright_white',
        )

        if not track['tracks']['items']:
            print('Found: NOTHING!')  # , fg='bright_red')

        else:

            track_id = track['tracks']['items'][0]['id']
            print(
                'Found: '
                + track_id
                + '\t'
                + (
                    ', '.join(
                        [a['name'] for a in track['tracks']['items'][0]['artists']]
                    )
                ).ljust(35)
                + track['tracks']['items'][0]['name'],
                # fg='bright_green',
            )

            if not track_id in existing_tracks:
                tracks.append(track_id)

    # print(tracks)

    if tracks:
        print(
            f'Adding {len(tracks)} track(s) to playlist...', end=''
        )  # nl=False, fg='bright_white')
        sp.playlist_add_items(PLAYLIST_ID, tracks)
        print(' Done.')  # , fg='bright_green')
    else:
        print('No tracks to add.')  # , fg='bright_yellow')


if __name__ == '__main__':
    main()
