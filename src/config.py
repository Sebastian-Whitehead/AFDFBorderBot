import json

with open('ids.json') as f:
    IDS = json.load(f)
    ROLES = IDS['roles']
    CHANNELS = IDS['channels']

with open('Settings.json') as f:
    SETTINGS = json.load(f)