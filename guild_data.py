import json
import requests
import tibiapy
from tibiapy.parsers import GuildsSectionParser, GuildParser

# Worlds to fetch guilds from
WORLDS = ['Flamera', 'Mykera', 'Kardera', 'Firmera', 'Gravitera', 'Wildera', 'Lobera']

def fetch_guilds_for_world(world):
    url = tibiapy.urls.get_world_guilds_url(world)
    try:
        response = requests.get(url)
        response.raise_for_status()
        content = response.text
        guilds_section = GuildsSectionParser.from_content(content)
        return guilds_section.entries
    except Exception as e:
        raise RuntimeError(f"Error fetching guilds for world {world}: {e}")

def fetch_guild_data(guild_name):
    url = tibiapy.urls.get_guild_url(guild_name)
    try:
        response = requests.get(url)
        response.raise_for_status()
        content = response.text
        guild = GuildParser.from_content(content)
        return guild
    except Exception as e:
        raise RuntimeError(f"Error fetching data for guild {guild_name}: {e}")

def lambda_handler(event, context):
    print("Starting data fetch...")
    worlds_data = {}

    try:
        for world in WORLDS:
            print(f"Processing world: {world}")
            worlds_data[world] = {}
            guilds = fetch_guilds_for_world(world)
            for guild_entry in guilds:
                guild_name = guild_entry.name
                print(f"Processing guild: {guild_name}")
                guild_data = fetch_guild_data(guild_name)
                if guild_data:
                    worlds_data[world][guild_name] = [member.name for member in guild_data.members]

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
