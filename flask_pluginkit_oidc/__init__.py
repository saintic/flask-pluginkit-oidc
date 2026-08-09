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

from flask import (
    Blueprint,
    url_for,
    request,
    session,
    redirect,
    g,
    Response,
)
from authlib.integrations.flask_client import OAuth

__plugin_name__ = "oidc"
__description__ = "OIDC Client for staugur/passportd"
__version__ = "0.3.0"
__author__ = "Hiroshi.tao <me@tcw.im>"
__url__ = "https://github.com/saintic/flask-pluginkit-oidc"
__license__ = "BSD 3-Clause"
__license_file__ = "LICENSE"
__readme_file__ = "README.md"
__state__ = getenv("PASSPORTD_OIDC_STATE", "enabled")
__appversion__ = ">=3.11.0"

# 模块级只创建 OAuth 空实例，由 on_app_ready 完成初始化
oauth = OAuth()
bp = Blueprint(__plugin_name__, __plugin_name__)


def on_app_ready(app):
    """应用就绪状态点（Flask-PluginKit >= 3.11.0）。

    register() 不在应用上下文，但 on_app_ready 在应用完全就绪后调用，
    此时可以安全地初始化 OAuth 并注册 OIDC 客户端。
    Authlib 自动从 app.config 读取 {NAME}_CLIENT_ID 等键，无需显式传入。
    """
    with app.app_context():
        oauth.init_app(app)
        oauth.register(
            name="passportd_oidc",
            server_metadata_url=app.config.get(
                "PASSPORTD_OIDC_SERVER_METADATA_URL",
                "https://passport.saintic.com/.well-known/openid-configuration",
            ),
            client_kwargs=app.config.get(
                "PASSPORTD_OIDC_CLIENT_KWARGS",
                {"scope": "openid profile"},
            ),
        )


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
    set_login_state = getattr(g, "set_login_state", None)
    if set_login_state and callable(set_login_state):
        ret = set_login_state(token["userinfo"])
        if isinstance(ret, Response):
            return ret
    else:
        session["user"] = token["userinfo"]
    return redirect(request.args.get("next") or getattr(g, "login_redirect_url", "/"))


def register():
    return dict(
        bep=dict(blueprint=bp, prefix="/oauth2/passportd"),
    )
