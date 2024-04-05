import json
import urllib.request
import gzip
from io import BytesIO

# Worlds to fetch guilds from
WORLDS = ['Flamera', 'Mykera', 'Kardera', 'Firmera', 'Gravitera', 'Wildera']

def fetch_guilds_for_world(world):
    url = f"http://localhost:80/v4/guilds/{world}"
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
                print(f"Failed to fetch guilds for world: {world}")
                return []
    except Exception as e:
        print(f"Error fetching guilds for world {world}: {e}")
        return []

def fetch_guild_data(guild_name):
    encoded_guild_name = urllib.parse.quote(guild_name)
    url = f"http://localhost:80/v4/guild/{encoded_guild_name}"
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
        print(f"Error fetching data for {guild_name}: {e}")
        return {}

def lambda_handler(event, context):
    try:
        print("Starting data fetch...")
        worlds_data = {}

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
        print(f"Failed to fetch data or write to file: {e}")
        raise e  # Raise the exception to stop execution

# For local testing or direct invocation, you might want to call lambda_handler directly
lambda_handler(None, None)
