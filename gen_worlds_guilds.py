import json
import urllib.request
import urllib.parse
import gzip
from io import BytesIO

# Worlds to fetch guilds from
WORLDS = ['Flamera', 'Temera', 'Mykera', 'Kardera', 'Firmera', 'Gravitera', 'Wildera', 'Lobera']

def fetch_guilds_for_world(world):
    url = f"https://api.tibiadata.com/v4/guilds/{world}"
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request) as response:
            if response.info().get('Content-Encoding') == 'gzip':
                buffer = BytesIO(response.read())
                with gzip.open(buffer, 'rb') as f:
                    data = json.loads(f.read().decode('utf-8'))
            else:
                data = json.loads(response.read().decode('utf-8'))
            if response.status == 200:
                return data.get('guilds', {}).get('active', [])
            else:
                raise ValueError(f"Failed to fetch guilds for world: {world}")
    except Exception as e:
        raise RuntimeError(f"Error fetching guilds for world {world}: {e}")

def fetch_guild_data(guild_name):
    encoded_guild_name = urllib.parse.quote(guild_name)
    url = f"https://api.tibiadata.com/v4/guild/{encoded_guild_name}"
    request = urllib.request.Request(url)
    request.add_header('Accept-Encoding', 'gzip')
    try:
        with urllib.request.urlopen(request) as response:
            if response.info().get('Content-Encoding') == 'gzip':
                buffer = BytesIO(response.read())
                with gzip.open(buffer, 'rb') as f:
                    data = json.loads(f.read().decode('utf-8'))
            else:
                data = json.loads(response.read().decode('utf-8'))
            return data.get('guild', {})
    except Exception as e:
        raise RuntimeError(f"Error fetching data for guild {guild_name}: {e}")

def lambda_handler(event, context):
    print("Starting data fetch...")
    worlds_data = {}

    try:
        for world in WORLDS:
            print(world)
            worlds_data[world] = {}
            guilds = fetch_guilds_for_world(world)
            for guild in guilds:
                print(guild["name"])
                guild_name = guild.get('name')
                guild_data = fetch_guild_data(guild_name)
                if guild_data:
                    worlds_data[world][guild_name] = [member['name'] for member in guild_data.get('members', [])]

        # Convert the data structure to JSON
        json_data = json.dumps(worlds_data, indent=4)

        # Write the JSON to a local file
        with open('world_guilds_data.json', 'w') as f:
            f.write(json_data)
        print("Successfully wrote data to file.")
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

lambda_handler(None, None)
