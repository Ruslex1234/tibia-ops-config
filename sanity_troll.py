import requests
import json

def correct_names():
    updated = False
    with open('trolls.json', 'r') as file:
        trolls = json.load(file)

    # Use enumerate to get both the index (i) and the value (troll)
    for i, troll in enumerate(trolls):
        response = requests.get(f"https://api.tibiadata.com/v4/character/{troll}")
        if response.status_code == 200:
            data = response.json()
            correct_name = data["character"]["character"]["name"]  # Ensure this matches the actual structure of the response
            if troll != correct_name:
                print(f"Correcting name: {troll} to {correct_name}")
                trolls[i] = correct_name  # Update the list item directly
                updated = True

    if updated:
        with open('trolls.json', 'w') as file:
            json.dump(trolls, file, indent=4)
    else:
        print("No corrections needed.")

if __name__ == '__main__':
    correct_names()
