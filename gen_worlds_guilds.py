import json
import urllib.request
import boto3
import gzip
from io import BytesIO

# Replace 'your_bucket_name' with your actual S3 bucket name
S3_BUCKET = 'jokindude'
# Worlds to fetch guilds from
WORLDS = ['Flamera', 'Mykera', 'Kardera', 'Firmera', 'Gravitera', 'Wildera']

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
                print(f"Failed to fetch guilds for world: {world}")
                return []
    except Exception as e:
        print(f"Error fetching guilds for world {world}: {e}")
        return []

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
        print(f"Error fetching data for {guild_name}: {e}")
        return {}

def lambda_handler(event, context):
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

    # Upload the JSON to S3
    s3 = boto3.client('s3')
    try:
        s3.put_object(Bucket=S3_BUCKET, Key='world_guilds_data.txt', Body=json_data)
        print("Successfully uploaded data to S3.")
    except Exception as e:
        print(f"Failed to upload data to S3: {e}")

# For local testing or direct invocation, you might want to call lambda_handler directly
lambda_handler(None, None)
