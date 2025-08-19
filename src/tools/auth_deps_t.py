import math
import json
from random import randint
import requests
import datetime
import logging
from typing import Optional, Dict, Annotated, ForwardRef

from fastapi import HTTPException, Header


from firebase_admin import auth
from firebase_admin.auth import UserRecord

from pydantic import BaseModel, Field

from src.core.configs import configs

from src.tools.exceptions import ExceptionMessage, get_exception_id
from src.tools.auth_deps import TokenMissing, FirebaseCommonException

from src.repository.message import MessageRepository, InjectTestMessageRepository


TRIAL_MESSAGES = 15


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


class Identity(BaseModel):
    profile: Profile

    class Config:
        arbitrary_types_allowed = True

    async def check_subscription(self):
        return True

    async def check_message_count(self):
        messages_total = await self.message_repository.count_messages_today(
            self.profile.user_id,
        )
        return messages_total < TRIAL_MESSAGES

    async def check_message_token_limit(self):
        return True

    async def check_openai_access(self):
        return True

    def check_ownership(self, object: BaseModel):
        return True


class AuthorizationHeader(BaseModel):
    Auth: Optional[str] = None
    Authorization: Optional[str] = None


# async def identify_test_request(
# ) -> Profile:
#     return Identity(
#         profile=Profile(
#             sub="someuserid",
#             iss="asdf",
#             aud='asdf',
#             auth_time=12341234,
#             # user_id="TESTUSER",
#             iat=10,
#             exp=10,
#             email="test@test.com",
#             email_verified=True,
#             phone_number="1234",
#             name="name",
#             picture=None,
#         )
#     )


# def setup_user(

# ) -> Identity:
#     return Identity(
#         profile=Profile(
#             iss="generatedfortestfromtest",
#             aud="generatedfortestfromtest",
#             auth_time=(
#                 datetime.datetime.utcnow()
#                     + datetime.timedelta(seconds=60)
#                     - datetime.datetime(1970, 1, 1)
#             ).total_seconds(),
#         )
#     )


def get_token(
    uid: Optional[str] = None,
    set_email: Optional[bool] = False,
    set_email_verified: Optional[bool] = False,
    custom_claims: Optional[dict] = None,
) -> tuple:
    if not uid:
        user: UserRecord = auth.create_user()
    else:
        user: UserRecord = auth.get_user(uid)

    if custom_claims:
        claims: dict | None = user.custom_claims
        if not claims:
            claims = dict()
        claims.update(custom_claims)
        auth.update_user(user.uid, custom_claims=claims)
    if set_email:
        auth.update_user(
            user.uid, email=f"fromtest-{randint(100_000,999_999)}@test.com"
        )
    else:
        auth.update_user(
            user.uid,
            email=None,
        )
    if set_email_verified:
        if not user.email:
            auth.update_user(
                user.uid, email=f"fromtest-{randint(100_000,999_999)}@test.com"
            )
        auth.update_user(
            user.uid,
            email_verified=True,
        )
    else:
        auth.update_user(
            user.uid,
            email_verified=False,
        )

    token: bytes = auth.create_custom_token(user.uid)
    data = {"token": token.decode(), "returnSecureToken": True}

    url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={}".format(
        configs.FIREBASE_API_KEY
    )

    resp = requests.post(
        url,
        data=json.dumps(data),
    )

    return resp.json()["idToken"], user.uid


anonymouse_user_token, uid = get_token()

user_token, uid = get_token()

expired_token = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImE3MWI1MTU1MmI0ODA5OWNkMGFkN2Y5YmZlNGViODZiMDM5NmUxZDEiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vbG9jYWwtc291bHdpIiwiYXVkIjoibG9jYWwtc291bHdpIiwiYXV0aF90aW1lIjoxNzM1Mzk3Njg3LCJ1c2VyX2lkIjoiM05vTHc3WlVYblljWDlHQVZMdUVab3NHdXBDMyIsInN1YiI6IjNOb0x3N1pVWG5ZY1g5R0FWTHVFWm9zR3VwQzMiLCJpYXQiOjE3MzUzOTc2ODcsImV4cCI6MTczNTQwMTI4NywiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6e30sInNpZ25faW5fcHJvdmlkZXIiOiJjdXN0b20ifX0.Jqooifz6wxsaSJEBldTWC4hIF3SuBH8XtXoDBWy1G8UblegGyR386wqGnYVzOOEYELessL0UoLxAUOYS77dl6WvwVSDqIBOvwiMfHdutk0W3mVc4IyTX-C7lXahGqlm-wdqXZ4E9Pmsm1TqKJxNZ9ubE0S8eyxqr8fuk1beZXFt5toGUExbMnbYI_-4GyPJKgTS0-P5C8trjCtK_SoOHoYWAOS22ahy1e5F2TOZq8wgwvqDFk-M2C8xgq0Q13blc-evS5gsIK-qX2QHO0ZIZ_c3HLLCunJQ7TCgML_79rv8p_j_Haq102ov05TMgACz0ZGtpNYs_fHOo5KfVWtCAzA"

not_verified_email_user_token, _ = get_token(
    uid="wuFloX4sVreh6K5WaPuA9Ywzmxz1",
    set_email=True,
    custom_claims={
        "is_lifetime_paid": None,
        "subscription_expire_at": None,
    },
)

verified_email_user_token, _ = get_token(
    uid="wuFloX4sVreh6K5WaPuA9Ywzmxz1",
    set_email=True,
    set_email_verified=True,
    custom_claims={
        "is_lifetime_paid": None,
        "subscription_expire_at": None,
    },
)

subscription_not_expired_user_token, uid = get_token(
    uid="wuFloX4sVreh6K5WaPuA9Ywzmxz1",
    set_email=True,
    set_email_verified=True,
    custom_claims={
        "is_lifetime_paid": None,
        "subscription_expire_at": int(
            (
                datetime.datetime.utcnow()
                + datetime.timedelta(days=1)
                - datetime.datetime(1970, 1, 1)
            ).total_seconds()
        ),
    },
)

subscription_expired_user_token, uid = get_token(
    uid="wuFloX4sVreh6K5WaPuA9Ywzmxz1",
    set_email=True,
    set_email_verified=True,
    custom_claims={
        "is_lifetime_paid": None,
        "subscription_expire_at": int(
            (
                datetime.datetime.utcnow()
                - datetime.timedelta(days=1)
                - datetime.datetime(1970, 1, 1)
            ).total_seconds()
        ),
    },
)

lifetime_paid_user_token, uid = get_token(
    uid="wuFloX4sVreh6K5WaPuA9Ywzmxz1",
    set_email=True,
    set_email_verified=True,
    custom_claims={
        "is_lifetime_paid": True,
        "subscription_expire_at": None,
    },
)


# TODO: move to non-test
async def identify_request_with_repository(
    headers: Annotated[AuthorizationHeader, Header()],
) -> Profile:
    from src.tools.auth_deps import Profile, Identity

    if not headers.Auth and not headers.Authorization:
        raise TokenMissing()
    try:
        # splitted_token = headers.Auth.split("Bearer ")[-1]
        # logging.warning(splitted_token)
        header = headers.Auth if headers.Auth else headers.Authorization
        if not header.startswith("Bearer "):
            raise auth.InvalidIdTokenError("Invalid token format")
        decoded_token = auth.verify_id_token(
            header[7:],
            clock_skew_seconds=5,
        )
        return Identity(
            profile=Profile(**decoded_token),
            message_repository=await InjectTestMessageRepository(),
        )
    except auth.ExpiredIdTokenError as e:
        raise e
    except auth.InvalidIdTokenError as e:
        raise e
    except Exception as e:
        logging.exception(e)
        raise FirebaseCommonException()
