import json


def login():
    with open("keys/uxmovement_cookies.json", "r") as file:
        content = json.load(file)
    return content
