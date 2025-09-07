from typing import Optional
from fastapi import Header, HTTPException, Request
from core.configs import configs


class ProxyError(HTTPException):
    pass

class SiteNotSupportedError(ProxyError):
    def __init__(self, site: str):
        super().__init__(
            status_code=400,
            detail=f"Site '{site}' is not supported by this instance"
        )

class MissingSiteHeaderError(ProxyError):
    def __init__(self):
        super().__init__(
            status_code=400,
            detail=f"Missing required header '{configs.PROXY_HEADER_NAME}'. Please specify target site."
        )


async def get_target(
    x_proxy_site: Optional[str] = Header(None, alias=configs.PROXY_HEADER_NAME)
) -> str:
    if not x_proxy_site:
        raise MissingSiteHeaderError()
    
    site = x_proxy_site.lower().strip()
    
    if site not in configs.TARGETS:
        raise SiteNotSupportedError(site)
    
    return site


async def get_target_from_host(request: Request) -> str:
    host = request.headers.get("host", "")

    if "." in host:
        subdomain = host.split(".")[0]
        if subdomain == "elements":
            return "envato"
        elif subdomain == "uxmove":
            return "uxmovement"
        return subdomain
    
    raise MissingSiteHeaderError()