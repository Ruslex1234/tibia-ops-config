import urllib.request
import json
import boto3
import gzip
from io import BytesIO
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# TibiaData API URL for fetching online players in a world
base_url = "https://api.tibiadata.com/v4/world/{world_name}"

# Worlds to fetch online players from
worlds = ['Flamera', 'Mykera', 'Kardera', 'Firmera', 'Gravitera', 'Wildera']

special_guilds = ['Bastex', 'Pentagrama', 'Demon Horde', 'Pink Mango', 'Partners', 'Bastex Flamera Owners', 'Bad Boysz', 'Bastex Boys', 'Bastex Rushback', 'Vidiuneta Bastex']

# trolls
trolls = ['trip wick', 'crowley saint', 'savage kley', 'willy saint', 'true sanielon codioff', 'parcher',
    'Nix Dametc', 'Inquieto Ed', 'Sleeping Booty', 'Krod', 'Amm Sky', 'Legend Thegoat',
        'rodryk style', 'parangarih', 'morinor', 'besas tan biien', 'rod sin plata', 
            'el rod', 'mykera da rod', 'yelsew element', 'pelon rod sinleche', 'rod sin jotape',
                'diez minibankers incluyendome', 'retro rod', 'sleeping booty', 'kleening up',
                    'bvbe rindofull', 'danny veneco king', 'Qorothor Alar', 'true samix', 'Bell luben' ,
                        'helboy knight', 'rampage loony', 'leyva disaster', 'Tatami Warlover', 'Valcru Machine', 'Kothe',
                            'Sir Kurogane', 'geb hatshepsut', 'Totixi', 'Leozin Rajada', 'Mrchampions Pluma', 'Scobith Iv',
                                'Panoramics', 'Javier Good Boy', 'horkside', 'corridoss tumbadoss']

alert = ["Bladexz Bad Boy", "Fego", "Bolt ada", "Elreon", "Kazo Bait Voi", "Rod Mimascota Eterna", "Scarlet Cifer",
    "Lucy Cifer", "Exu star", "Escorpion Ruler", "Aztek Ruler", "Tathrion Elvotton", "Udyr Tanker", "Julio Warrior", "Yoshua Cobra Ruler"]

telegram =""
chat_id_rod = ""
chat_id_mykera = ""


bucket_name = ""  # Change to your bucket name

def lambda_handler(event, context):
    print("starting lambda_handler")
    
    # Send a message to a Telegram chat
    def send_alert(chat_id, message, bot_token=telegram):
        encoded_message = urllib.parse.quote(message)  # URL-encode the message
        encoded_chat_id = urllib.parse.quote(chat_id)   # URL-encode the chat_id
        send_url = f'https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={encoded_chat_id}&parse_mode=Markdown&text={encoded_message}'
        
        # Prepare the request
        req = urllib.request.Request(send_url)
    
        try:
            with urllib.request.urlopen(req) as response:
                response_body = response.read()
                print("Message sent successfully:", response_body.decode('utf-8'))
                return {
                    'statusCode': 200,
                    'body': json.dumps('Message sent!')
                }
        except Exception as e:
            print(f"Failed to send message: {e}")
            return {
                'statusCode': 400,
                'body': json.dumps('Failed to send message')
            }

    # Update the online status of players in S3
    def update_player_online_status(online_players):
        # Fetch the current status from S3
        s3_client = boto3.client('s3')
        try:
            # Fetch the current online status from S3
            response = s3_client.get_object(Bucket=bucket_name, Key='online_status_v2.txt')
            online_status = json.loads(response['Body'].read().decode('utf-8'))
        except s3_client.exceptions.NoSuchKey:
            # If the object does not exist, create an empty status object
            online_status = {}
        # Get the current time
        current_time = datetime.now()

        # Update online status
        for world, players in online_players.items():
            if world not in online_status:
                online_status[world] = {}
            if players is None:
                continue
            for player in players:
                if player['name'] not in online_status[world]:
                    online_status[world][player['name']] = current_time.strftime("%Y-%m-%d %H:%M:%S")
                    if player['name'] in alert:
                        message = "*" + player["name"] + " just logged on!*"
                        send_alert(chat_id_mykera, message)

        # Remove players who are no longer online
        for world in online_status:
            if online_players.get(world, []) is not None:
                # Get the names of players who are currently online
                online_names = [player['name'] for player in online_players.get(world, [])]
                # Remove players who are not in the current list of online players
                online_status[world] = {name: time for name, time in online_status[world].items() if name in online_names}

        # Upload the updated status to S3
        s3_client.put_object(Bucket=bucket_name, Key='online_status_v2.txt', Body=json.dumps(online_status), ContentType='application/json')
        # Return the updated status
        return online_status


    # Format a timedelta as a string
    def format_timedelta_as_string(start_timestamp, end_timestamp):
    # Parse the timestamps into datetime objects if they are strings
        if isinstance(start_timestamp, str):
            start_timestamp = datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S")
        if isinstance(end_timestamp, str):
            end_timestamp = datetime.strptime(end_timestamp, "%Y-%m-%d %H:%M:%S")
        
        # Calculate the difference between the two timestamps
        time_difference = end_timestamp - start_timestamp
        
        # Extract hours and minutes from the timedelta
        hours, remainder = divmod(time_difference.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        
        # Conditionally format the result based on the value of hours
        if hours > 0:
            result = f"{int(hours)}h{int(minutes)}m"
        else:
            result = f"{int(minutes)}m"
        
        return result

    # Fetch the online players in a world
    def fetch_all_worlds(worlds):
        with ThreadPoolExecutor(max_workers=len(worlds)) as executor:
            future_to_world = {executor.submit(fetch_world_online_players, world): world for world in worlds}
            results = {}
            for future in as_completed(future_to_world):
                world = future_to_world[future]
                try:
                    data = future.result()
                    results[world] = data['world']['online_players']
                except Exception as exc:
                    print('%r generated an exception: %s' % (world, exc))
            return results
    
    # Fetch the online players in a world
    def fetch_world_online_players(world_name):
        url = base_url.format(world_name=world_name)
        request = urllib.request.Request(url)
        request.add_header('Accept-Encoding', 'gzip')
        with urllib.request.urlopen(request) as response:
            if response.info().get('Content-Encoding') == 'gzip':
                # The response is gzip compressed, so decompress it
                buf = BytesIO(response.read())
                with gzip.open(buf) as gz:
                    data = json.loads(gz.read().decode())
            else:
                # The response is not compressed
                data = json.loads(response.read().decode())
            return data

    def fetch_enemy_json():
        # open s3 bucket filename and load the json
        # filename = guilds_data.json
        print("fetching enemy json")
        s3 = boto3.resource('s3')
        obj = s3.Object(bucket_name, 'world_guilds_data.txt')
        data = obj.get()['Body'].read().decode('utf-8')
        return json.loads(data)
    
    def sort_categories(categorized_players, special_guilds):
        # Create a new ordered dictionary to hold the sorted categories
        from collections import OrderedDict
        ordered_categories = OrderedDict()

        # Add Trolls first if it exists
        if 'Trolls' in categorized_players:
            ordered_categories['Trolls'] = categorized_players['Trolls']
            
        # Add Alerts first if it exists
        if 'Alerts' in categorized_players:
            ordered_categories['Alerts'] = categorized_players['Alerts']

        # Add special guilds in order
        for guild in special_guilds:
            if guild in categorized_players:
                ordered_categories[guild] = categorized_players[guild]

        # Add other guilds
        for category, players in categorized_players.items():
            if category not in ordered_categories and category != 'Others':
                ordered_categories[category] = players

        # Add Others last if it exists
        if 'Others' in categorized_players:
            ordered_categories['Others'] = categorized_players['Others']

        return ordered_categories

    def sort_and_html(worlds_data, compare_data, last_updated_time):
        print("sort_and_html")
        # Update the online status of players and fetch the updated status
        online_tracker = update_player_online_status(worlds_data)
        # Convert last_updated_time to an ISO 8601 string for JavaScript compatibility
        last_updated_iso = last_updated_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        html = "<!DOCTYPE html><html>"
        html += '<head>'
        html += '<meta http-equiv="refresh" content="10">'
        html += '<style>body {color: #eee;background-color:#2E2E2E;}a{color: #1DAAE5;} h1, h2, h3 { margin: 0; }</style>'
        html += '</head>'
        html += "<body>"
        html += "<center><h1>Bastex</h1></center>"
        now = datetime.now()
        html += """<center><h4 id="lastUpdatedText">Last Updated: </h4></center>
                    <script>
                        var lastUpdated = "{last_updated_iso}";
                        document.addEventListener('DOMContentLoaded', function() {{
                            var lastUpdatedElement = document.getElementById('lastUpdatedText');
                            var lastUpdatedTime = new Date(lastUpdated);
                            var now = new Date();
                            var differenceInMinutes = Math.floor((now - lastUpdatedTime) / 60000); // Convert to minutes
                            var text = "Last Updated: " + differenceInMinutes + " minutes ago";
                            lastUpdatedElement.textContent = text;
                            
                            if (differenceInMinutes <= 5) {{
                                lastUpdatedElement.style.color = "green";
                            }} else if (differenceInMinutes <= 10) {{
                                lastUpdatedElement.style.color = "orange";
                            }} else {{
                                lastUpdatedElement.style.color = "red";
                            }}
                        }});
                    </script>
                    <!-- Your dynamic content generation goes here -->
                </body>
                </html>
                """.format(last_updated_iso=last_updated_iso)  # Use the format method to insert the last_updated_iso variable
        
        html += '<table style="border:1px solid black; margin-left:auto;margin-right:auto;"><tr>'
        # Generate HTML content for each world
        for world in worlds:
            online_timer = online_tracker[world]
            data = fetch_world_online_players(world)
            # If there are players online in the world, sort and display them
            if data['world']['players_online'] != 0:
                online_players = data['world']['online_players']
                online_players_sorted = sorted(online_players, key=lambda x: x['level'], reverse=True)
                
                # Classify players into categories
                categorized_players = {'Trolls': [], 'Alerts':[], 'Others': []}
                for player in online_players_sorted:
                    player_category = 'Others'
                    player_found_in_guild = False

                    if player['name'].lower() in map(str.lower, trolls):
                        player_category = 'Trolls'
                    elif player['name'].lower() in map(str.lower, alert):
                        player_category = 'Alerts'
                    else:
                        for guild_name, guild_members in compare_data[world].items():
                            if player['name'] in guild_members:
                                player_found_in_guild = True
                                # Check if guild category exists, if not create it
                                if guild_name not in categorized_players:
                                    categorized_players[guild_name] = []
                                player_category = guild_name
                                break
                    categorized_players[player_category].append(player)
                    # In case the player wasn't found in any specific guild, but isn't a troll
                    # if not player_found_in_guild and player_category == 'Others':
                        # categorized_players[player_category].append(player)
                
                html += '<td style="width: 259px; vertical-align:top">\n'
                html += "=================================\n"
                html += f"<center><h2>{world} ({str(sum(len(players) for players in categorized_players.values()))})</h2></center>\n"
                html += "=================================<br>"
                html += "<table>"

                # Define colors for each category type
                color_map = {
                    "Trolls": "#1D8102",
                    "Alerts": "#FF0000",
                    "Others": "#1DAAE5"  # Default color for Others
                    # Special guilds will get the "Hunted" color dynamically
                }

                categorized_players = sort_categories(categorized_players, special_guilds)
                # Generate HTML content for each category
                for category, players in categorized_players.items():
                    if players:
                        html += f'<tr><td colspan="3"><center><h3>{category} ({len(categorized_players[category])})</h3></center></td></tr>'
                        for player in players:
                            # print(f"Player type: {type(player)}, content: {player}")  # Debug print
                            # Use the current time as the default value if the player's name is not found in online_timer
                            default_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                            online_since = format_timedelta_as_string(online_timer.get(player['name'], default_time), now.strftime("%Y-%m-%d %H:%M:%S"))
                            
                            # Determine color based on category, special treatment for 'special_guilds'
                            if category in special_guilds:
                                color = "#FFD700"  # "Hunted" color for special guilds
                            else:
                                color = color_map.get(category, "#1DAAE5")  # Default color or specific category color
                            
                            html += f'<tr><td>[{player["level"]}]</td><td>{"".join([v[0] for v in player["vocation"].split()])}</td><td><a href="https://www.tibia.com/community/?name={player["name"]}" target="_blank" rel="noopener noreferrer" style="color: {color};">{player["name"]}</a> ({online_since})</td></tr>'

                html += "</table></p></td>"

        
        html += "</tr></table>"
        html += "<center>=====================================</center>"
        html += "<center>=====================================</center>"
        html += "</body>"
        html += "</html>"
        return html


    worlds_data = fetch_all_worlds(worlds)
    enemy_guilds = fetch_enemy_json()
    html_content = sort_and_html(worlds_data, enemy_guilds, datetime.utcnow())
    print("uploading")

    # Upload the HTML content to S3
    file_name = "bastex_players.html"
    my_acl = "public-read"
    content_type = "text/html"
    s3 = boto3.resource('s3')
    object = s3.Object(bucket_name, file_name)
    object.put(Body=html_content, ACL=my_acl, ContentType=content_type)

    # write to local file
    # with open("bastex_players.html", "w") as file:
        # file.write(html_content)
    # print('HTML updated and uploaded to S3 successfully!')

#lambda_handler(None, None)
