# flask-pluginkit-oidc

基于 [Authlib](https://docs.authlib.org/) 的 OIDC Client，作为 [Flask-PluginKit](https://github.com/staugur/flask-pluginkit) 插件使用，对接 [staugur/passportd](https://github.com/staugur/passportd) OIDC Provider。

## 依赖

- Python >= 3.9
- flask-pluginkit >= 3.8.0
- authlib >= 1.7.0

## 快速开始

### 1. 安装

```bash
pip install .
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
| `PASSPORTD_OIDC_STATE`               | `PASSPORTD_OIDC_STATE`                | 否   | 插件启用状态，默认是enabled，禁用是disabled                                               |

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
    # 强烈建议, 设置登录状态，如果返回 Flask.Response 对象, 插件会直接 return 对象。
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

## 路由

| 路由                           | 说明                                     |
| ------------------------------ | ---------------------------------------- |
| `/oauth2/passportd/login`      | 发起 OIDC 授权，重定向至 Provider 登录页 |
| `/oauth2/passportd/authorized` | OIDC 回调地址，Provider 需配置为此 URL   |

## 工作原理

1. 插件通过 Flask-PluginKit 的 `register()` 入口加载，注册 Blueprint 和 `before_first_request` 钩子
2. `before_first_request` 钩子在首次请求时延迟初始化 Authlib OAuth（延迟初始化是因为 `register()` 不在 Flask 应用上下文中）
3. 用户访问 `/login` → 重定向到 OIDC Provider 授权页
4. Provider 认证后回调 `/authorized` → Authlib 完成 token 交换 + userinfo 获取
5. userinfo 默认写入 `session["user"] = userinfo` 或通过 `g.set_login_state(userinfo)` 设置登录状态
6. 重定向到 `g.login_redirect_url` 或 `/`
