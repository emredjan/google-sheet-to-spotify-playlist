import os.path
from pprint import pprint

import pandas as pd
import spotipy

# import click
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from spotipy.oauth2 import SpotifyOAuth

from resources import PLAYLIST_ID, SPREADSHEET_ID

# Google Things
# If modifying these scopes, delete the file token.json.
GOOGLE_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Spotify things
SPOTIFY_SCOPES = [
    'user-library-read',
    'playlist-modify-private',
    'playlist-read-private',
    'playlist-modify-public',
    'playlist-read-collaborative',
]
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SPOTIFY_SCOPES))


MAX_RANGE = 500
RANGE_OFFSET = 3
RANGE = f'A{RANGE_OFFSET}:C{MAX_RANGE}'
WRITE_COLUMN = 'K'


def connect_to_sheets():

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('google_token.json'):
        creds = Credentials.from_authorized_user_file(
            'google_token.json', GOOGLE_SCOPES
        )
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'google_credentials.json', GOOGLE_SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('google_token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('sheets', 'v4', credentials=creds)

    return service


def get_data_from_sheets():

    service = connect_to_sheets()

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return

    df = (
        pd.DataFrame(values, columns=['Artist', 'Track', 'Suggested By'])
        .dropna()
        .reset_index(drop=True)
    )

    return df


def main():

    df = get_data_from_sheets()

    service = connect_to_sheets()
    sheet = service.spreadsheets()

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
    spotify_urls = []
    for index, row in df.iterrows():

        query = 'track:' + row['Track'].replace('\'', '') + ' NOT live NOT feat artist:' + row['Artist']

        track = sp.search(query, limit=1, type='track', market='NL')

        print(
            ('For: ' + row['Artist']).ljust(35) + row['Track'].ljust(40),
            end='',
            # fg='bright_white',
        )

        if not track['tracks']['items']:
            print('Found: NOTHING!')  # , fg='bright_red')

            spotify_urls.append('')

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

            spotify_urls.append(track['tracks']['items'][0]['external_urls']['spotify'])

    print('\nWriting Spotify links back to sheet...', end='')
    write_range = f'{WRITE_COLUMN}{RANGE_OFFSET}:{WRITE_COLUMN}{len(spotify_urls)+RANGE_OFFSET-1}'

    try:
        body = {'values': [[x] for x in spotify_urls]}
        result = (
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=SPREADSHEET_ID,
                range=write_range,
                valueInputOption='RAW',
                body=body,
            )
            .execute()
        )
        print('Done.')
    except HttpError:
        print('Failed.')

    # print(tracks)
    print()
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
