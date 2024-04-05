import json
import urllib.request
import gzip
from io import BytesIO

# Worlds to fetch guilds from
WORLDS = ['Flamera', 'Mykera', 'Kardera', 'Firmera', 'Gravitera', 'Wildera']

def fetch_data(url):
    with urllib.request.urlopen(url) as response:
        if response.info().get('Content-Encoding') == 'gzip':
            buffer = BytesIO(response.read())
            with gzip.open(buffer, 'rb') as f:
                data = json.loads(f.read().decode('utf-8'))
        else:
            data = json.loads(response.read().decode('utf-8'))
    return data

def fetch_guilds_for_world(world):
    url = f"http://localhost:80/v4/guilds/{world}"
    data = fetch_data(url)
    return data.get('guilds', {}).get('active', [])

def fetch_guild_data(guild_name):
    encoded_guild_name = urllib.parse.quote(guild_name)
    url = f"http://localhost:80/v4/guild/{encoded_guild_name}"
    data = fetch_data(url)
    return data.get('guild', {})

def lambda_handler():
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

# For local testing or direct invocation, you might want to call lambda_handler directly
lambda_handler()
