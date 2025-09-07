@app.post("/proxy-heartbeat")
async def heartbeat(
        request: Request,
        identity: Annotated[Identity, Depends(identify_request)],
):
    proxy_relation = await subs_req.get_user_proxy_relation(
        identity.profile.user_id,
        configs.PROXY_TARGET,
    )
    logging.warning(proxy_relation)
    logging.warning(identity.profile.user_id)
    if not await identity.check_proxy_access(
            proxy_relation,
    ):
        raise HTTPException(401)
    await set_map_access(request)
    return 'ok'