from bs4 import BeautifulSoup


def inject_heartbeat(html, soup=None):
    heartbeat = """
    setInterval(() => { fetch('/proxy-heartbeat', { method: 'POST' }); }, 5 * 60 * 1000); // every 15 mins
    """
    inject_js_into_html(html, heartbeat, soup)


def inject_js_into_html(html, js_code, soup=None):
    if not soup:
        soup = BeautifulSoup(html, "html.parser")
    script_tag = soup.new_tag("script")
    script_tag.string = js_code

    # Inject into <head> if exists, otherwise end of <body>
    if soup.head:
        soup.head.append(script_tag)
    elif soup.body:
        soup.body.append(script_tag)
    else:
        soup.append(script_tag)

    return str(soup), soup
