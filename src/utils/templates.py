def load_heartbeat():
     with open("templates/heartbeat.html", "r", encoding="utf-8") as f:
        return f.read()


def load_heartbeat_with_firebase():
     with open("templates/firebase_heartbeat.html", "r", encoding="utf-8") as f:
        return f.read()


def login_html(token):
     with open("templates/login.html", "r", encoding="utf-8") as f:
        return f.read().format(token=token)


