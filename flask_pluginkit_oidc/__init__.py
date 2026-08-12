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

import json
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
from authlib.integrations.base_client.errors import MismatchingStateError
from authlib.integrations.flask_client import OAuth
from authlib.integrations.flask_client.integration import FlaskIntegration

__plugin_name__ = "oidc"
__description__ = "OIDC Client for staugur/passportd"
__version__ = "0.4.0"
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


class RedisStateIntegration(FlaskIntegration):
    """将 OAuth state 数据存储到 Redis（服务端），避免客户端 session cookie
    在跨站跳转（Provider -> 回调）时被浏览器（如 Brave）阻止导致丢失，
    从而规避 authorize_access_token() 抛出 MismatchingStateError 的问题。

    兼容 authlib 的 FlaskIntegration：update_token / load_config 行为不变，
    仅重写 state 的存取三个方法。
    """

    def __init__(self, name, redis_client, expires_in=3600, cache=None):
        super().__init__(name, cache)
        self.redis_client = redis_client
        self.expires_in = expires_in

    def _key(self, state):
        return f"_state_{self.name}_{state}"

    def get_state_data(self, session, state):
        key = self._key(state)
        value = self.redis_client.get(key)
        if not value:
            return None
        try:
            return json.loads(value).get("data")
        except (TypeError, ValueError):
            return None

    def set_state_data(self, session, state, data):
        key = self._key(state)
        self.redis_client.set(key, json.dumps({"data": data}), ex=self.expires_in)

    def clear_state_data(self, session, state):
        key = self._key(state)
        self.redis_client.delete(key)


def _get_redis_client(app):
    """按配置获取 Redis 客户端。

    优先级：PASSPORTD_OIDC_REDIS（实例） > PASSPORTD_OIDC_REDIS_URL（连接串）。
    """
    rc = app.config.get("PASSPORTD_OIDC_REDIS")
    if rc is None:
        from redis import Redis

        redis_url = app.config.get("PASSPORTD_OIDC_REDIS_URL")
        rc = Redis.from_url(redis_url, decode_responses=True)
    return rc


def on_app_ready(app):
    """应用就绪状态点（Flask-PluginKit >= 3.11.0）。

    register() 不在应用上下文，但 on_app_ready 在应用完全就绪后调用，
    此时可以安全地初始化 OAuth 并注册 OIDC 客户端。
    Authlib 自动从 app.config 读取 {NAME}_CLIENT_ID 等键，无需显式传入。

    可通过 PASSPORTD_OIDC_STATE_STORE 配置 state 存储方式：
    - session（默认）：沿用 authlib 默认，state 存于客户端 session cookie；
    - redis：state 存于 Redis 服务端，规避跨站 Cookie 被浏览器阻止导致的
      MismatchingStateError，配合 PASSPORTD_OIDC_REDIS_URL 或
      PASSPORTD_OIDC_REDIS 使用。
    """
    name = "passportd_oidc"
    with app.app_context():
        oauth.init_app(app)
        client = oauth.register(
            name=name,
            server_metadata_url=app.config.get(
                "PASSPORTD_OIDC_SERVER_METADATA_URL",
                "https://passport.saintic.com/.well-known/openid-configuration",
            ),
            client_kwargs=app.config.get(
                "PASSPORTD_OIDC_CLIENT_KWARGS",
                {"scope": "openid profile"},
            ),
        )
        if app.config.get("PASSPORTD_OIDC_STATE_STORE", "session") == "redis":
            client.framework = RedisStateIntegration(
                name,
                redis_client=_get_redis_client(app),
                expires_in=app.config.get("PASSPORTD_OIDC_STATE_EXPIRES", 3600),
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
    try:
        token = oauth.passportd_oidc.authorize_access_token()
    except MismatchingStateError:
        # state 校验失败，常见于跨站 Cookie 被浏览器（如 Brave）阻止导致
        # session 中 state 丢失，重定向回登录页，避免直接返回 500。
        return redirect(url_for(".login"))
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
