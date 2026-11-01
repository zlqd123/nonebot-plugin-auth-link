# nonebot-plugin-auth-link

QQ 官方 Bot「AI 群服务授权」链接生成插件。发送 `授权` 签发授权卡片，点击按钮后在输入框补全群号，生成群机器人服务协议授权跳转链接。

## 特性

- **指令面板友好**：指令静态无参（`授权`/`授权 群号`），在 q.qq.com 管理端配置指令面板后，用户点击即预填，补全群号发送即可
- **openid 直显**：发送「授权」即返回当前会话的 `group_openid` / `user_openid`，方便配置迁移与机器人管理
- **无会话、无状态**：不依赖被动回复窗口与交互会话，永不过时
- **纯适配器交互**：仅依赖 nonebot2 + nonebot-adapter-qq

## 使用

```
用户: @bot 授权            → 返回当前会话 openid 与使用说明
用户: @bot 授权 965148132  → 返回授权链接卡片
```

> 历史 v0.1.0 采用「卡片按钮 + token 预填」方案（利用群聊按钮点击=指令预填的实测行为），
> 现已全面迁移到指令面板，卡片按钮代码已移除。

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
