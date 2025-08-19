from typing import Optional, Callable, Dict
from functools import partial

from pydantic import BaseModel, Field

from fastapi.responses import JSONResponse, HTMLResponse
from fastapi import Request, HTTPException, WebSocket

# from fastapi.templating import Jinja2Templates


import logging


global touched_ids
touched_ids = list()

STATUS_TO_HTML_MAP = {
    404: """ <!DOCTYPE html> <html> <head> <title>404 Not Found</title> </head> <body> <h1>404 Not Found</h1> <p>The requested URL was not found on this server.</p> </body> </html> """,
    400: """ <!DOCTYPE html> <html> <head> <title>400 Bad Request</title> </head> <body> <h1>400 Bad Request</h1> <p>Your browser sent a request that this server could not understand.</p> </body> </html> """,
    403: """ <!DOCTYPE html> <html> <head> <title>403 Forbidden</title> </head> <body> <h1>403 Forbidden</h1> <p>You don't have permission to access this resource on this server.</p> </body> </html>""",
    500: """ <!DOCTYPE html> <html> <head> <title>500 Internal Server Error</title> </head> <body> <h1>500 Internal Server Error</h1> <p>The server encountered an internal error and was unable to complete your request.</p> </body> </html>""",
    502: """ <!DOCTYPE html> <html> <head> <title>502 Bad Gateway</title> </head> <body> <h1>502 Bad Gateway</h1> <p>The server received an invalid response from the upstream server.</p> </body> </html> """,
    "_": """ <!DOCTYPE html> <html> <head> <title>500 Internal Server Error</title> </head> <body> <h1>500 Internal Server Error</h1> <p>The server encountered an internal error and was unable to complete your request.</p> </body> </html>""",
}


class ExceptionMessage(BaseModel):
    id: str  # unique exception id to connect with frotend
    status: int  # http status
    title: Optional[str] = None  # exception title
    short: Optional[str] = None  # short exception overview
    detailed: Optional[str] = None  # detailed exception overwiew

    update_func: Optional[Callable] = Field(None, exclude=True)

    def update_me(self, request, exception):
        if self.update_func:
            self.update_func(self, request, exception)


class HandlableException(Exception):
    """
    Handlable exception to be catched and send
    proper response to user

    THIS EXCEPTION PRIVENTS FROM DOUBLE LOGGING,
    SO IF YOU NEED TO LOG YOUR EXCEPTION,
    DO IT IN YOUR CODE WHERE YOU CALL THIS EXCEPTION
    """

    def __init__(
        self,
        unique_exception_id: str,
        http_status: int,
        title: Optional[str] = None,
        short: Optional[str] = None,  # short exception overview
        detailed: Optional[str] = None,  # detailed exception overwiew
        # ws_type: Optional[RespTypes] = None,  # optional response type for websockets
    ):
        super().__init__()
        if not title:
            title = map_status_to_name.get(http_status, "NOTITLE")
        self.handable_message = ExceptionMessage(
            id=unique_exception_id,
            status=http_status,
            title=title,
            short=short,
            detailed=detailed,
        )
        # self.ws_type = ws_type
        self.status = http_status
        self.message = detailed if detailed else short if short else title


# class HTMLException(Exception):
#     def __init__(
#         self,
#         html: str,
#         status_code: int,
#         # item_id: str,
#         *args,
#         # template_name: Optional[str] = None,
#         # swap_id: Optional[str] = None,
#         # proccessed_html_response: Optional[str] = None,
#         headers: Optional[dict] = None,
#         additional_context: Optional[dict] = None,
#         timeout: Optional[int] = 3,
#         **kwargs,
#     ):
#         super().__init__(*args, **kwargs)
#         self.html = html
#         self.status_code = status_code
#         self.headers = headers


class HTMLException(Exception):
    def __init__(
        self,
        template_name: str,
        status_code: int,
        # item_id: str,
        *args,
        # template_name: Optional[str] = None,
        # swap_id: Optional[str] = None,
        # proccessed_html_response: Optional[str] = None,
        headers: Optional[dict] = None,
        additional_context: Optional[dict] = None,
        timeout: Optional[int] = 3,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.template_name = template_name
        self.status_code = status_code
        # self.item_id = item_id
        self.headers = headers
        self.additional_context = additional_context
        self.timeout = timeout


# class HTMXException(Exception):
#     """exception thrown as html for htmx to processshit)
#     """

#     def __init__(
#         self,

#     ):
#         pass


map_status_to_name = {
    404: "Item not exsist",
    403: "Item not accecable",
    422: "Bad Request",
    500: "Server error",
}


def get_exception_id(
    origin: str,
    exception_id: str,
) -> str:
    """
    how exception id is created:
    'ORIGINWITHCAPSNOSPACES-uniqueidlowercasewithnospaces'
    it's consists of 2 parts -- origin and id
    origin is from where exception is raised
    and id -- unque id
    for example:
        PLUGINSCONTROLLERS-unique
        PLCO_1-unique
        X1-100
        A-46451
        1-1
    """
    return f"{origin}-{exception_id}"


# class WSExceptionHandler(BaseModel):
#     # status_to_template_map: Dict
#     # exception_id_to_template_map: Dict

#     # template_settings: Dict
#     # templates: Jinja2Templates
#     # default_exception_content: str
#     # notification_meta_template: str

#     # hx_retarget: Optional[str] = "#notification-container"
#     # hx_reswap: Optional[str] = "beforeend"
#     # default_timeout: Optional[float] = 3

#     async def handle_HTTPException(
#         self,
#         websocket: WebSocket,
#         raised_exception: HTTPException,
#     ) -> HTMLResponse:
#         logging.exception(raised_exception)
#         return await websocket.send_json(
#             WSMessageOut(
#                 type=RespTypes.error,
#                 body=ExceptionMessage(
#                     id=f'UNIFIED_HTTP_EXCEPTION-{raised_exception.status_code}',
#                     status=raised_exception.status_code,
#                     title=raised_exception.detail
#                     if raised_exception.detail
#                     else map_status_to_name.get(raised_exception.status_code, 'NOTITLE'),
#                     detailed="This is unifed HTTPException."
#                 ).model_dump(),
#             ).model_dump()
#         )

#     async def handle_3rd_party_exception(
#         self,
#         exception: Exception,  # exception type
#         message: ExceptionMessage,
#         request: WebSocket,
#         raised_exception: Exception,  # actual raised exception
#     ) -> JSONResponse:
#         logging.exception(raised_exception)
#         message.update_me(request, raised_exception)
#         return await request.send_json(
#             WSMessageOut(
#                 type=RespTypes.error,
#                 body=message.model_dump(),
#             ).model_dump()
#         )

#     async def handle_HandlableException(
#         self,
#         request: Request,
#         raised_exception: HandlableException,
#     ):
#         return await request.send_json(
#             WSMessageOut(
#                 type=raised_exception.ws_type if raised_exception.ws_type else RespTypes.error,
#                 body=raised_exception.handable_message.model_dump(),
#             ).model_dump()
#         )


# class HTMXExceptionHandler(BaseModel):
# status_to_template_map: Dict
# exception_id_to_template_map: Dict

# template_settings: Dict
# templates: Jinja2Templates
# default_exception_content: str
# notification_meta_template: str

# hx_retarget: Optional[str] = "#notification-container"
# hx_reswap: Optional[str] = "beforeend"
# default_timeout: Optional[float] = 3

# def handle_HTTPException(
#     self,
#     request: Request,
#     raised_exception: HTTPException,
# ) -> HTMLResponse:
#     """swap httpexception with default answer"""
#     logging.exception(raised_exception)
#     if not "HX-Request" in request.headers.keys():
#         return self.response_as_simple_html_page(
#             raised_exception.status_code,
#         )
#     context = {
#         "request": request,
#         "conf": self.template_settings,
#         "timeout": self.default_timeout,
#         "notification_content": self.status_to_template_map.get(
#             raised_exception.status_code,
#             self.default_exception_content,
#         )
#     }
#     headers = {
#         "HX-Retarget": self.hx_retarget,
#         "HX-Reswap": self.hx_reswap,
#     }
#     if self.hx_retarget:
#         headers["HX-Retarget"] = self.hx_retarget
#     if raised_exception.headers:
#         headers.update(raised_exception.headers)
#     return self.templates.TemplateResponse(
#         self.notification_meta_template,
#         context=context,
#         status_code=raised_exception.status_code,
#         headers=headers,
#     )

# def handle_3rd_party_exception(
#     self,
#     request: Request,
#     raised_exception: ExceptionMessage,
# ):
#     """swap 3rd party exception with mapped"""
#     logging.exception(raised_exception)
#     if not "HX-Request" in request.headers.keys():
#         return self.response_as_simple_html_page(
#             raised_exception.status,
#         )
#     context = {
#         "request": request,
#         "conf": self.template_settings,
#         "timeout": self.default_timeout,
#         "notification_content": self.exception_to_template_map.get(
#             raised_exception.id,
#             self.default_exception_content,
#         )
#     }
#     headers = {
#         "HX-Retarget": self.hx_retarget,
#         "HX-Reswap": self.hx_reswap,
#     }
#     if self.hx_retarget:
#         headers["HX-Retarget"] = self.hx_retarget
#     if raised_exception.headers:
#         headers.update(raised_exception.headers)
#     return self.templates.TemplateResponse(
#         self.notification_meta_template,
#         context=context,
#         status_code=raised_exception.status_code,
#         headers=headers,
#     )

# def handle_HandlableException(
#     self,
#     request: Request,
#     raised_exception: HandlableException,
# ):
#     """render template/text from exception"""
#     logging.exception(raised_exception)
#     if not "HX-Request" in request.headers.keys():
#         return self.response_as_simple_html_page(
#             raised_exception.handable_message.status,
#         )
#     notification = self.exception_id_to_template_map.get(
#         raised_exception.handable_message.id,
#     )
#     if not notification:
#         notification = self.status_to_template_map.get(
#             raised_exception.handable_message.id,
#             self.default_exception_content,
#         )
#     context = {
#         "request": request,
#         "conf": self.template_settings,
#         "timeout": self.default_timeout,
#         "notification_content": notification
#         # "item_id": e.item_id,
#     }
#     headers = {
#         "HX-Retarget": self.hx_retarget,
#         "HX-Reswap": self.hx_reswap,
#     }
#     return self.templates.TemplateResponse(
#         self.notification_meta_template,
#         context=context,
#         status_code=raised_exception.status,
#         headers=headers,
#     )

# def handle_HTMLException(
#     self,
#     request: Request,
#     raised_exception: HTMLException,
# ):
#     """render template/text from exception"""
#     logging.exception(raised_exception)
#     if not "HX-Request" in request.headers.keys():
#         return self.response_as_simple_html_page(
#             raised_exception.status_code,
#         )
#     context = {
#         "request": request,
#         "conf": self.template_settings,
#         "timeout": raised_exception.timeout,
#         "notification_content": raised_exception.template_name
#     }
#     headers = {
#         "HX-Retarget": self.hx_retarget,
#         "HX-Reswap": self.hx_reswap,
#     }
#     if raised_exception.headers:
#         headers.update(raised_exception.headers)
#     if raised_exception.additional_context:
#         context.update(raised_exception.additional_context)
#     return self.templates.TemplateResponse(
#         self.notification_meta_template,
#         context=context,
#         status_code=raised_exception.status_code,
#         headers=headers,
#     )

# def response_as_simple_html_page(
#     self,
#     status: int,
# ):
#     return HTMLResponse(
#         STATUS_TO_HTML_MAP.get(status, STATUS_TO_HTML_MAP['_']),
#     )


def handle_HTTPException(
    request: Request,
    raised_exception: HTTPException,
) -> JSONResponse:
    logging.exception(raised_exception)
    return JSONResponse(
        ExceptionMessage(
            id=f"UNIFIED_HTTP_EXCEPTION-{raised_exception.status_code}",
            status=raised_exception.status_code,
            title=(
                raised_exception.detail
                if raised_exception.detail
                else map_status_to_name.get(raised_exception.status_code, "NOTITLE")
            ),
            detailed="This is unifed HTTPException.",
        ).model_dump(),
        status_code=raised_exception.status_code,
    )


# def handle_HTTPExceptionWS(
#     request: Request,
#     raised_exception: HTTPException,
# ) -> JSONResponse:
#     logging.exception(raised_exception)
#     return ExceptionMessage(
#         id=f'UNIFIED_HTTP_EXCEPTION-{raised_exception.status_code}',
#         status=raised_exception.status_code,
#         title=raised_exception.detail
#         if raised_exception.detail
#         else map_status_to_name.get(raised_exception.status_code, 'NOTITLE'),
#         detailed="This is unifed HTTPException."
#     )


def handle_HandlableException(
    request: Request | WebSocket,
    raised_exception: HandlableException,
) -> JSONResponse:
    logging.exception(raised_exception)
    return JSONResponse(
        raised_exception.handable_message.model_dump(),
        raised_exception.status,
    )


def handle_HTMLException(
    request: Request,
    raised_exception: HTMLException,
) -> HTMLResponse:
    logging.exception(raised_exception)
    return HTMLResponse(
        STATUS_TO_HTML_MAP.get(raised_exception.status_code, STATUS_TO_HTML_MAP["_"]),
    )


def handle_wrapped_exception_html(
    request: Request,
    raised_exception: HandlableException,
) -> JSONResponse:
    logging.exception(raised_exception)
    return JSONResponse(
        raised_exception.handable_message.model_dump(),
        raised_exception.status,
    )


# def prepare_data(
#     exception_dict: dict[Exception, ExceptionMessage],
#     wrap_exception:Optional[Callable] = wrap_exception,
# ) -> dict:
#     return {
#         key: partial(wrap_exception, key, message)
#         for key, message
#         in exception_dict.items()
#     }


async def handle_3rd_party_exception(
    exception: Exception,  # exception type
    message: ExceptionMessage,
    request: Request | WebSocket,
    raised_exception: Exception,  # actual raised exception
) -> JSONResponse:
    logging.exception(raised_exception)
    message.update_me(request, raised_exception)
    return JSONResponse(
        message.model_dump(),
        message.status,
    )


# def wrap_exception_html(
#     exception: Exception,  # exception type
#     message: ExceptionMessage,
#     request: Request,
#     raised_exception: Exception,  # actual raised exception
# ) -> HTMLResponse:
#     logging.exception(raised_exception)
#     return HTMLResponse(

#     )
#     # return JSONResponse(
#     #     message.dict(),
#     #     message.status,
#     # )


def prepare_exceptions(
    *args: Dict[Exception, ExceptionMessage],
    handle_HandlableException: Optional[Callable] = handle_HandlableException,
    handle_HTTPException: Optional[Callable] = handle_HTTPException,
    handle_3rd_party_exception: Optional[Callable] = handle_3rd_party_exception,
    handle_HTMLException: Optional[Callable] = handle_HTMLException,
    skip_check: Optional[bool] = False,
    # handle_WebsocketException: Optional[Callable] = handle_WebsocketException,
) -> dict:
    handlable_exceptions = {
        HandlableException: handle_HandlableException,
        HTTPException: handle_HTTPException,
        HTMLException: handle_HTMLException,
    }
    for exception_dict in args:
        if not skip_check:
            assert check_for_unique_id(exception_dict)
        handlable_exceptions.update(
            {
                key: partial(handle_3rd_party_exception, key, message)
                for key, message in exception_dict.items()
            }
        )
    return handlable_exceptions


def check_for_unique_id(
    exception_dict: dict[Exception, ExceptionMessage],
) -> None:
    for exception_message in exception_dict.values():
        global touched_ids
        if exception_message.id in touched_ids:
            return False
        touched_ids.append(exception_message.id)
    return True
