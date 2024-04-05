import json
import requests

# Worlds to fetch guilds from
WORLDS = ['Flamera', 'Mykera', 'Kardera', 'Firmera', 'Gravitera', 'Wildera']

def fetch_guilds_for_world(world):
    url = f"http://localhost:80/v4/guilds/{world}"
    print(f"Fetching guilds for world: {world}")
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"Successfully fetched guilds for world: {world}")
            data = response.json()
            return data.get('guilds', {}).get('active', [])
        else:
            print(f"Failed to fetch guilds for world: {world}, status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching guilds for world {world}: {e}")
        return []

def fetch_guild_data(guild_name):
    encoded_guild_name = requests.utils.quote(guild_name)
    url = f"http://localhost:80/v4/guild/{encoded_guild_name}"
    print(f"Fetching data for guild: {guild_name}")
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"Successfully fetched data for guild: {guild_name}")
            data = response.json()
            return data.get('guild', {})
        else:
            print(f"Failed to fetch data for guild: {guild_name}, status code: {response.status_code}")
            return {}
    except Exception as e:
        print(f"Error fetching data for {guild_name}: {e}")
        return {}

def lambda_handler(event, context):
    try:
        print("Starting data fetch...")
        worlds_data = {}

        for world in WORLDS:
            print(f"Processing world: {world}")
            worlds_data[world] = {}
            guilds = fetch_guilds_for_world(world)
            for guild in guilds:
                print(f"Processing guild: {guild['name']}")
                guild_name = guild.get('name')
                guild_data = fetch_guild_data(guild_name)
                if guild_data:
                    worlds_data[world][guild_name] = [member['name'] for member in guild_data.get('members', [])]

        # Convert the data structure to JSON
        json_data = json.dumps(worlds_data, indent=4)

        # Write the JSON to a local file
        with open('world_guilds_data.json', 'w') as f:
            print("Writing data to file...")
            f.write(json_data)
        print("Successfully wrote data to file.")
    except Exception as e:
        print(f"Failed to fetch data or write to file: {e}")
        raise e  # Raise the exception to stop execution

# For local testing or direct invocation, you might want to call lambda_handler directly
lambda_handler(None, None)
