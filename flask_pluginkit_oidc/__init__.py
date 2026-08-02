# -*- coding: utf-8 -*-
"""
Copyright 2025 Hiroshi.tao

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from os import getenv

from flask import Blueprint, url_for, request, session, redirect, current_app
from authlib.integrations.flask_client import OAuth

__plugin_name__ = "oidc"
__description__ = "OIDC Client for staugur/passportd"
__version__ = "0.1.0"
__author__ = "Hiroshi.tao <me@tcw.im>"
__license__ = "BSD 3-Clause License"
__license_file__ = "LICENSE"
__readme_file__ = "README.md"
__state__ = getenv("PASSPORTD_OIDC_STATE", "enabled")

# 模块级只创建 OAuth 空实例，延迟到首次请求时初始化
oauth = OAuth()
_oauth_ready = False
bp = Blueprint(__plugin_name__, __plugin_name__)


def _ensure_oauth():
    """延迟初始化 OAuth：register() 不在应用上下文，但 before_request 钩子在。

    Authlib 自动从 app.config 读取 {NAME}_CLIENT_ID 等键（如 PASSPORTD_OIDC_CLIENT_ID），
    无需手动传入 client_id / client_secret。
    """
    global _oauth_ready
    if not _oauth_ready:
        oauth.init_app(current_app)
        oauth.register(
            name="passportd_oidc",
            server_metadata_url=current_app.config.get(
                "PASSPORTD_OIDC_SERVER_METADATA_URL",
                "https://passport.saintic.com/.well-known/openid-configuration",
            ),
            client_kwargs=current_app.config.get(
                "PASSPORTD_OIDC_CLIENT_KWARGS",
                {"scope": "openid profile"},
            ),
        )
        _oauth_ready = True


@bp.route("/login")
def login():
    redirect_uri = url_for(".authorized", _external=True)
    return oauth.passportd_oidc.authorize_redirect(redirect_uri)


@bp.route("/authorized")
def authorized():
    err = request.args.get("error")
    if err:
        return f"Error: {err}, description: {request.args.get('error_description')}"
    token = oauth.passportd_oidc.authorize_access_token()
    # set login state
    session["user"] = token["userinfo"]
    return redirect("/")


def register():
    """Flask-PluginKit 入口。

    OAuth 无法在此处初始化（无应用上下文），通过 hep before_request 延迟到首次请求。
    """
    return dict(
        bep=dict(blueprint=bp, prefix="/oauth2/passportd"),
        hep=dict(before_request=_ensure_oauth),
    )
