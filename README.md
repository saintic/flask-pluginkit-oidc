# flask-pluginkit-oidc

基于 [Authlib](https://docs.authlib.org/) 的 OIDC Client，作为 [Flask-PluginKit](https://github.com/staugur/flask-pluginkit) 插件使用，对接 [staugur/passportd](https://github.com/staugur/passportd) OIDC Provider。

## 依赖

- Python >= 3.9
- flask-pluginkit >= 3.11.0
- authlib >= 1.7.0

## 快速开始

### 1. 安装

```bash
pip install flask-pluginkit-oidc
# 或从 Git 安装
pip install git+https://github.com/saintic/flask-pluginkit-oidc@master
```

### 2. 配置

通过环境变量或 `app.config` 设置以下配置：

| 配置项                               | 环境变量                             | 必填 | 说明                                                                                      |
| ------------------------------------ | ------------------------------------ | ---- | ----------------------------------------------------------------------------------------- |
| `PASSPORTD_OIDC_CLIENT_ID`           | `PASSPORTD_OIDC_CLIENT_ID`           | 是   | OIDC Provider 分配的 client_id                                                            |
| `PASSPORTD_OIDC_CLIENT_SECRET`       | `PASSPORTD_OIDC_CLIENT_SECRET`       | 是   | OIDC Provider 分配的 client_secret                                                        |
| `PASSPORTD_OIDC_SERVER_METADATA_URL` | `PASSPORTD_OIDC_SERVER_METADATA_URL` | 否   | OIDC Discovery 端点，默认 `https://passport.saintic.com/.well-known/openid-configuration` |
| `PASSPORTD_OIDC_CLIENT_KWARGS`       | —                                    | 否   | 传递给 OAuth client 的额外参数，默认 `{"scope": "openid profile"}`                        |
| `PASSPORTD_OIDC_STATE`               | `PASSPORTD_OIDC_STATE`               | 否   | 插件启用状态，默认是enabled，禁用是disabled                                               |
| `PASSPORTD_OIDC_STATE_STORE`         | —                                    | 否   | OAuth state 存储方式：`session`（默认，存客户端 session cookie）或 `redis`（存服务端 Redis） |
| `PASSPORTD_OIDC_REDIS_URL`           | `PASSPORTD_OIDC_REDIS_URL`           | 否   | Redis 连接串，仅 `STATE_STORE=redis` 时使用              |
| `PASSPORTD_OIDC_REDIS`               | —                                    | 否   | 直接传入 Redis 客户端实例（优先级高于 `REDIS_URL`），仅 `STATE_STORE=redis` 时使用        |
| `PASSPORTD_OIDC_STATE_EXPIRES`       | —                                    | 否   | state 过期时间（秒），仅 `STATE_STORE=redis` 时使用，默认 `3600`                           |

> Authlib 约定：`oauth.register(name="passportd_oidc")` 会自动从 `app.config` 查找 `PASSPORTD_OIDC_CLIENT_ID` 和 `PASSPORTD_OIDC_CLIENT_SECRET`，无需手动传入。

### 3. 使用

```python
from os import getenv
from flask import Flask, session, g, make_response, redirect
from flask_pluginkit import PluginManager

app = Flask(__name__)
app.secret_key = getenv("SECRET_KEY", "change-me")

app.config.update(
    PASSPORTD_OIDC_CLIENT_ID=getenv("PASSPORTD_OIDC_CLIENT_ID", ""),
    PASSPORTD_OIDC_CLIENT_SECRET=getenv("PASSPORTD_OIDC_CLIENT_SECRET", ""),
)

plugin = PluginManager(app, plugin_packages=["flask_pluginkit_oidc"])

def set_login_state(userinfo:dict):
    # 假设用session管理会话
    session["user"] = userinfo
    return make_response(redirect("/"))

@app.before_request
def before_request():
    # 强烈建议, 设置登录状态，如果返回 Flask.Response 对象, 扩展会直接 return 对象。
    g.set_login_state = set_login_state
    # 可选，登录后跳转地址
    g.login_redirect_url = "/"

if __name__ == "__main__":
    app.run(debug=True)
```

### 4. 测试

```bash
export PASSPORTD_OIDC_CLIENT_ID=your_client_id
export PASSPORTD_OIDC_CLIENT_SECRET=your_client_secret
python test_client.py
```

访问 `http://localhost:5000/oauth2/passportd/login` 发起 OIDC 登录。

### 5. userinfo

```json
{
  "bio": "签名",
  "gender": 1,
  "location": "地点",
  "nickname": "昵称",
  "picture": "头像地址",
  "status": 1,
  "sub": "用户唯一标识"
}
```

### 6. 解决 OIDC state 丢失问题（可选）

Authlib 默认把 OAuth state（含 nonce、code_verifier）写入 Flask 客户端 session cookie。
部分浏览器（如 Brave）会阻止跨站 Cookie：用户从 Provider 授权页回调 `/authorized` 时，
session cookie 丢失，Authlib 会抛出 `MismatchingStateError`（500）。

插件已内置兜底：即使 state 丢失也不会 500，而是重定向回登录页重新发起授权。

若要彻底规避该问题，可将 state 改为存到服务端 Redis：

```python
app.config.update(
    PASSPORTD_OIDC_STATE_STORE="redis",
    PASSPORTD_OIDC_REDIS_URL=getenv("PASSPORTD_OIDC_REDIS_URL", "redis://localhost:6379/0"),
)
# 或者直接传入 Redis 客户端实例（需先 pip install redis）
# PASSPORTD_OIDC_REDIS=redis_client,
```

## 路由

| 路由                           | 说明                                     |
| ------------------------------ | ---------------------------------------- |
| `/oauth2/passportd/login`      | 发起 OIDC 授权，重定向至 Provider 登录页 |
| `/oauth2/passportd/authorized` | OIDC 回调地址，Provider 需配置为此 URL   |

## 工作原理

1. 插件通过 Flask-PluginKit 的 `register()` 入口加载，注册 Blueprint
2. `on_app_ready(app)` 在应用完全就绪后调用（Flask-PluginKit >= 3.11.0），此时有应用上下文，安全地初始化 `oauth.init_app(app)` 并注册 OIDC 客户端；若配置 `PASSPORTD_OIDC_STATE_STORE=redis`，同时将 OAuth state 存储切换到 Redis
3. 用户访问 `/login` → 重定向到 OIDC Provider 授权页
4. Provider 认证后回调 `/authorized` → Authlib 完成 token 交换 + userinfo 获取；若 state 校验失败（如跨站 Cookie 被阻止），自动重定向回登录页而非 500
5. userinfo 默认写入 `session["user"] = userinfo` 或通过 `g.set_login_state(userinfo)` 设置登录状态
6. 重定向到 `g.login_redirect_url` 或 `/`
