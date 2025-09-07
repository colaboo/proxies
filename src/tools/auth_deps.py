from functools import reduce
import datetime
from fastapi.responses import FileResponse, RedirectResponse
import logging
from typing import Optional, Dict, Annotated, ForwardRef

from fastapi import HTTPException, Header, Request, Cookie


from firebase_admin import auth

# from core.configs import firebase_app

from pydantic import BaseModel, Field

from core.configs import configs

from tools.exceptions import ExceptionMessage, get_exception_id
from dateutil.relativedelta import relativedelta

from tools.duration import duration_to_month


# from repository.message import MessageRepository


TTL_FOR_MAP_ACCESS = datetime.timedelta(minutes=1)

DEFAULT_STRP_MASK = "%Y-%m-%d %H:%M:%S"

# TODO: move to in-memory database (Redis) with optional ttl later

# map_access = dict()


class Map(BaseModel):
    map_access: dict


map = Map(map_access=dict())


async def check_map_access(req: Request):
    if value := map.map_access.get(
        (req.headers.get("X-Real-IP"), req.headers.get("User-Agent"))
    ):
        return value > datetime.datetime.now()


async def set_map_access(req: Request):
    map.map_access[(req.headers.get("X-Real-IP"), req.headers.get("User-Agent"))] = (
        datetime.datetime.now() + TTL_FOR_MAP_ACCESS
    )


class Profile(BaseModel):
    # Standard JWT Claims
    iss: str  # Issuer
    aud: str  # Audience (Firebase project ID)
    auth_time: Optional[int]  # Authenticated time (Unix timestamp)
    user_id: str = Field(alias="sub")  # Subject (User UID)
    iat: int  # Issued-at time (Unix timestamp)
    exp: int  # Expiration time (Unix timestamp)
    email: Optional[str] = None
    # User's email
    email_verified: Optional[bool] = False
    # Is the email verified?
    phone_number: Optional[str] = None
    # User's phone number (if available)
    name: Optional[str] = None
    # User's display name
    picture: Optional[str] = None
    # URL to the user's profile picture
    firebase: Optional[Dict[str, str | dict]] = None
    # Firebase-specific fields (see below)
    custom_claims: Optional[Dict[str, str | dict]] = None
    # Custom claims added to the user's account
    is_lifetime_paid: Optional[bool] = None
    subscription_expire_at: Optional[int] = None
    is_admin: Optional[bool] = None

    def load_claims(self):
        if not self.custom_claims:
            return
        is_admin = self.custom_claims.get("is_admin")
        if is_admin is not None:
            self.is_admin = is_admin


class Identity(BaseModel):
    profile: Profile
    # message_repository: MessageRepository

    class Config:
        arbitrary_types_allowed = True

    def check_ownership(self, object: BaseModel):
        user_id = getattr(object, "user_id", None)
        if not user_id:
            user_id = getattr(object, "user_uid", None)
        if not user_id:
            user_id = getattr(object, "owner_id", None)
        if not user_id:
            user_id = getattr(object, "owner", None)
        if not user_id:
            return False
        return self.profile.user_id == user_id

    def check_admin(self):
        return self.profile.is_admin

    async def basic_check(self):
        # await self.check_subscription()
        # await self.check_openai_access()
        return True

    async def check_subscription(self):
        if configs.DEBUG:
            return self.profile.email_verified
        if self.profile.is_lifetime_paid:
            return True
        if self.profile.subscription_expire_at:
            return (
                datetime.datetime.utcfromtimestamp(self.profile.subscription_expire_at)
                > datetime.datetime.utcnow()
            )
        if self.profile.custom_claims:
            if self.profile.custom_claims.get("is_lifetime_paid"):
                return True
            if self.profile.custom_claims.get("subscription_expire_at"):
                return (
                    datetime.datetime.utcfromtimestamp(
                        self.profile.custom_claims.get("subscription_expire_at")
                    )
                    > datetime.datetime.utcnow()
                )
        return False

        # if (
        #     not self.profile.custom_claims
        #     and not self.profile.is_lifetime_paid
        #     and not self.profile.subscription_expire_at
        # ):
        #     return False
        # if self.profile.custom_claims.get("is_lifetime_paid"):
        #     return True
        # if timestamp := self.profile.custom_claims.get("subscription_expire_at"):
        #     print('~~~~~~~~~~~~')
        #     print('CHECK TIMESTAMP')
        #     print('~~~~~~~~~~~~')
        # return False

        # raise NotImplementedError("Subscription check is not implemented")
        # should use custom_claims to check payment data or something

    # async def check_message_limit(self):
    #     all_messages = await self.message_repository.get_user_message_stats(
    #         self.profile.user_id,
    #     )
    #     message_counter = 0
    #     user_sent_messages = filter(
    #         lambda message: message.role == 'user',
    #         all_messages
    #     )
    #     message_counter += len(list(user_sent_messages))
    #     retry_messages = reduce(
    #         lambda acc, message: acc + (
    #             1 * len(message.messages)
    #             if message.messages
    #             else 0
    #         ),
    #         all_messages,
    #         0
    #     )
    #     message_counter += retry_messages
    #     if configs.DEBUG:
    #         logging.debug(f"MESSAGE COUNTED: {message_counter}")
    #     return message_counter < TRIAL_MESSAGES

    async def check_proxy_access(self, proxy_relations):
        if not proxy_relations:
            return False
        return any(filter(validate_time, proxy_relations))
        # for relation in proxy_relations:
        #     if
        # for relatt
        # if self.profile.custom_claims and self.profile.custom_claims.get(f'pass_{proxy}'):
        #     return datetime.datetime.now() > datetime.datetime.strptime(
        #         self.profile.custom_claims.get(f"pass_{proxy}")
        #     )

    async def check_message_token_limit(self):
        raise NotImplementedError("Token-based check is not implemented")


class AuthorizationHeader(BaseModel):
    Auth: Optional[str] = None
    Authorization: Optional[str] = None


class FirebaseCommonException(Exception):
    pass
class RequiresLogin(Exception):
    pass

class TokenMissing(Exception):
    pass


async def identify_request(
    # authorization: Optional[str] = Header(None),
    headers: Annotated[AuthorizationHeader, Header()],
    req: Request,
) -> Profile:
    
    if not req.cookies.get("authToken") and not headers.Authorization:
        raise RequiresLogin("login")
    token = "Bearer " + req.cookies.get("authToken")
    if not token:
        token = headers.Authorization
    return None
   # return await process_token(token)


async def process_token(token: str):
    try:
        if not token.startswith("Bearer "):
            raise auth.InvalidIdTokenError("Invalid token format")
        decoded_token = auth.verify_id_token(
            token[7:],
            clock_skew_seconds=5,
        )
        profile = Profile(**decoded_token)
        profile.load_claims()
        return Identity(
            profile=profile,
        )
    except Exception as e:
        logging.exception(e)
        print(e)
        raise RequiresLogin("login")


def validate_time(value):
    time = datetime.datetime.fromisoformat(value["created_at"])
    monthes = relativedelta(months=duration_to_month(value["duration"]))
    return time + monthes > datetime.datetime.now()


ORIGIN = "FIREBASETOKENS"


exceptions = {
    auth.ExpiredIdTokenError: ExceptionMessage(
        id=get_exception_id(ORIGIN, "expiredtoken"),
        status=401,
        title="Firebase: expired token",
        short="Id token expired",
    ),
    auth.InvalidIdTokenError: ExceptionMessage(
        id=get_exception_id(ORIGIN, "invalidtoken"),
        status=401,
        title="Firebase: invalid token",
        short="Id token corrupted or passed in wrong way",
    ),
    FirebaseCommonException: ExceptionMessage(
        id=get_exception_id(ORIGIN, "commonexception"),
        status=500,
        title="General (not handled) exception",
        short="This exception is not handled properly or raised due\
            a bug. Check server logs for more.",
    ),
    TokenMissing: ExceptionMessage(
        id=get_exception_id(ORIGIN, "tokenmissing"),
        status=401,
        title="id token missing",
    ),
}
