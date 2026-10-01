# Copyright (c) 2026-present CyberSport Masters
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlparse
from base64 import b64encode

import pytz
import requests

# Module imports
from plane.authentication.adapter.oauth import OauthAdapter
from plane.license.utils.instance_value import get_configuration_value
from plane.authentication.adapter.error import (
    AuthenticationException,
    AUTHENTICATION_ERROR_CODES,
)


def _is_valid_http_url(value, *, allow_query=False):
    if not isinstance(value, str):
        return False

    try:
        parsed_url = urlparse(value)
        hostname = parsed_url.hostname
        port = parsed_url.port
    except ValueError:
        return False

    return (
        parsed_url.scheme in ("http", "https")
        and bool(hostname)
        and (port is None or 0 <= port <= 65535)
        and not parsed_url.fragment
        and (allow_query or not parsed_url.query)
    )


class OpenIDConnectProvider(OauthAdapter):
    provider = "oidc"
    scope = "openid profile email"

    def __init__(self, request, code=None, state=None, callback=None):
        OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_ISSUER_URL = get_configuration_value(
            [
                {
                    "key": "OIDC_CLIENT_ID",
                    "default": os.environ.get("OIDC_CLIENT_ID"),
                },
                {
                    "key": "OIDC_CLIENT_SECRET",
                    "default": os.environ.get("OIDC_CLIENT_SECRET"),
                },
                {
                    "key": "OIDC_ISSUER_URL",
                    "default": os.environ.get("OIDC_ISSUER_URL"),
                },
            ]
        )

        issuer_url = OIDC_ISSUER_URL.strip() if isinstance(OIDC_ISSUER_URL, str) else ""
        if not (OIDC_CLIENT_ID and OIDC_CLIENT_SECRET and _is_valid_http_url(issuer_url)):
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["OIDC_NOT_CONFIGURED"],
                error_message="OIDC_NOT_CONFIGURED",
            )

        discovery_url = f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"
        try:
            discovery_response = requests.get(discovery_url, timeout=10)
            discovery_response.raise_for_status()
            discovery_document = discovery_response.json()

            if not isinstance(discovery_document, dict) or discovery_document.get("issuer") != issuer_url:
                raise ValueError("Invalid OIDC discovery document")

            authorization_url = discovery_document.get("authorization_endpoint")
            token_url = discovery_document.get("token_endpoint")
            userinfo_url = discovery_document.get("userinfo_endpoint")
            if not all(
                _is_valid_http_url(endpoint, allow_query=True)
                for endpoint in (authorization_url, token_url, userinfo_url)
            ):
                raise ValueError("Invalid OIDC discovery endpoint")

            if "token_endpoint_auth_methods_supported" not in discovery_document:
                token_endpoint_auth_method = "client_secret_basic"
            else:
                token_auth_methods = discovery_document["token_endpoint_auth_methods_supported"]
                if not isinstance(token_auth_methods, list):
                    raise ValueError("Invalid OIDC token endpoint authentication methods")
                if "client_secret_basic" in token_auth_methods:
                    token_endpoint_auth_method = "client_secret_basic"
                elif "client_secret_post" in token_auth_methods:
                    token_endpoint_auth_method = "client_secret_post"
                else:
                    raise ValueError("Unsupported OIDC token endpoint authentication method")
        except (requests.RequestException, TypeError, ValueError):
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["OIDC_OAUTH_PROVIDER_ERROR"],
                error_message="OIDC_OAUTH_PROVIDER_ERROR",
            ) from None

        self.token_url = token_url
        self.userinfo_url = userinfo_url
        self.token_endpoint_auth_method = token_endpoint_auth_method

        client_id = OIDC_CLIENT_ID
        client_secret = OIDC_CLIENT_SECRET

        redirect_uri = f"""{"https" if request.is_secure() else "http"}://{request.get_host()}/auth/oidc/callback/"""
        url_params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.scope,
            "state": state,
        }
        separator = "&" if "?" in authorization_url else "?"
        auth_url = f"{authorization_url}{separator}{urlencode(url_params)}"
        super().__init__(
            request,
            self.provider,
            client_id,
            self.scope,
            redirect_uri,
            auth_url,
            self.token_url,
            self.userinfo_url,
            client_secret,
            code,
            callback=callback,
        )

    def set_token_data(self):
        data = {
            "code": self.code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        headers = {
            "Accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
        }
        if self.token_endpoint_auth_method == "client_secret_post":
            data.update({"client_id": self.client_id, "client_secret": self.client_secret})
        else:
            basic_auth = b64encode(f"{self.client_id}:{self.client_secret}".encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {basic_auth}"
        token_response = self.get_user_token(data=data, headers=headers)
        expires_in = token_response.get("expires_in")
        super().set_token_data(
            {
                "access_token": token_response.get("access_token"),
                "refresh_token": token_response.get("refresh_token", None),
                "access_token_expired_at": (
                    datetime.now(tz=pytz.utc) + timedelta(seconds=expires_in) if expires_in is not None else None
                ),
                "refresh_token_expired_at": (
                    datetime.fromtimestamp(token_response.get("refresh_token_expired_at"), tz=pytz.utc)
                    if token_response.get("refresh_token_expired_at")
                    else None
                ),
                "id_token": token_response.get("id_token", ""),
            }
        )

    def set_user_data(self):
        user_info_response = self.get_user_response()
        email = user_info_response.get("email")
        super().set_user_data(
            {
                "email": email,
                "user": {
                    "provider_id": user_info_response.get("sub"),
                    "email": email,
                    "avatar": user_info_response.get("picture") or user_info_response.get("avatar_url", ""),
                    "first_name": user_info_response.get("given_name") or user_info_response.get("name", ""),
                    "last_name": user_info_response.get("family_name", ""),
                    "is_password_autoset": True,
                },
            }
        )
