import requests
import json

def correct_names():
    updated = False
    with open('trolls.json', 'r') as file:
        trolls = json.load(file)

    for troll in trolls:
        response = requests.get(f"https://api.tibiadata.com/v4/character/{troll}")
        if response.status_code == 200:
            data = response.json()
            correct_name = data["character"]["character"]["name"]  # Adjust based on actual API response structure
            if troll != correct_name:
                print(f"Correcting name: {troll} to {correct_name}")
                troll['name'] = correct_name
                updated = True

    if updated:
        with open('trolls.json', 'w') as file:
            json.dump(trolls, file, indent=4)

if __name__ == '__main__':
    correct_names()
