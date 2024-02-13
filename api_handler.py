import datetime
import json

import requests

AUTH_URL = 'https://www.humanity.com/oauth2/token.php'
API_BASE_URL = 'https://www.humanity.com/api/v2'


# Function to handle error response from API
def handle_api_error(response: requests.Response) -> None:
    if response.status_code != 200:
        raise Exception(
            f'Failed to retrieve data. Status code: {response.status_code}')


# Function to retrieve access token using provided credentials
def get_access_token(credentials_file: str) -> str:
    # Retrieve access token using provided credentials
    with open(credentials_file) as json_file:
        credentials = json.load(json_file)

    response = requests.post(url=AUTH_URL, data=credentials)
    handle_api_error(response)
    return json.loads(response.text).get('access_token')


def get_positions(access_token: str) -> dict | None:
    # Construct API URL
    url = f'{API_BASE_URL}/positions'
    headers = {'accept': 'application/json'}
    params = {'access_token': access_token}

    # Get position data
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        position_data = response.json().get('data')
        positions_dict = {}
        for index, position in enumerate(position_data):
            positions_dict[index] = {
                'id':
                str(position.get('id')),
                'name':
                position.get('name'),
                'location':
                position['location'].get('name', 'Internal')
                if 'location' in position else 'Internal'
            }
        return positions_dict
    else:
        print(
            f'Failed to retrieve shifts. Status code: {response.status_code}')
        return None


def get_shifts(start_date: datetime.date,
               end_date: datetime.date,
               access_token: str,
               positions: dict = {},
               mode: str = 'overview') -> dict | None:
    # Construct API URL
    url = f'{API_BASE_URL}/shifts'
    headers = {'accept': 'application/json'}

    # Format URL parameters
    params = {
        'start_date': str(start_date),
        'end_date': str(end_date),
        'mode': mode,
        'access_token': access_token
    }
    if positions:
        params['schedule'] = ', '.join(positions.keys())

    # Get shift data
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(
            f'Failed to retrieve shifts. Status code: {response.status_code}')
        return None
