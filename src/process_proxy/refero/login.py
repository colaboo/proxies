import json


def login():
    with open("keys/refero_cookies.json", "r") as file:
        content = json.load(file)
    return content
