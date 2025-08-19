import time


def dump_to_file(content: str, filename: str = None):
    """Writes content to a new file if no filename is given, else overwrites the given file."""
    if filename is None:
        filename = f"dumps/dump_{int(time.time() * 1000)}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return filename
