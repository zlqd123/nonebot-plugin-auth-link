# nonebot-plugin-auth-link

QQ 官方 Bot「AI 群服务授权」链接生成插件。发送 `授权` 签发授权卡片，点击按钮后在输入框补全群号，生成群机器人服务协议授权跳转链接。

## 特性

- **卡片交互**：Markdown 卡片 + 指令预填按钮（适配官方 Bot 群聊"按钮点击=指令预填"的实测行为），无会话、**不会超时**
- **卡片外无效**：每张卡签发随机 token（24h 有效、校验归属者），直接发送群号无法生成链接
- **openid 直显**：卡片自带当前会话的 `group_openid` / `user_openid`，方便配置迁移与机器人管理
- **快捷重发**：自动记忆最近授权过的群号，下次卡片一键预填
- **纯适配器无关交互**：仅依赖 nonebot2 + nonebot-adapter-qq

## 使用

```
用户: @bot 授权
bot:  [卡片] 🔐 AI 群服务授权（含当前群 openid）
      [✏️ 填写群号]  [群 965148132]
用户: (点击按钮 → 输入框预填 "/授权 <token> "，补全群号发送)
bot:  [卡片] ✅ 授权链接已生成 → [👉 点击前往授权页面]
```

## 配置

`.env` 中添加：

```
# 机器人 QQ 号（拼进授权链接的 botUin 参数）
QBOT_QQ=123456789
```

## 安装

把 `nonebot_plugin_auth_link` 目录放入 bot 的插件目录（如 `extra_plugins/`），或 `nb plugin install`。

## License

MIT
