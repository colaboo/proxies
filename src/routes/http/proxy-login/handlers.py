@app.get("/proxy-login")
async def login(
        token: str,
        request: Request,
):
    return HTMLResponse(
        login_html(token)
    )