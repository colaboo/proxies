import json


def login():
    with open("keys/envato_cookies.json", "r") as file:
        content = json.load(file)
    return content
