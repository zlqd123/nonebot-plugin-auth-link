"""AI 群服务授权链接生成插件(QQ 官方 Bot·指令面板版)。

交互已从"卡片按钮 + token 预填"全面迁移到指令面板:
- 在 q.qq.com 管理端配置指令「授权」, 用户点击后输入框预填, 补全群号发送即可
- 「授权」: 返回当前会话 openid 与使用说明
- 「授权 群号」: 直接生成授权链接

机器人 QQ 号从 .env 的 QBOT_QQ 读取。
"""

from __future__ import annotations

from nonebot import get_driver, on_command
from nonebot.adapters import Event
from nonebot.adapters.qq import Message, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.adapters import Message as BaseMessage

__plugin_meta__ = PluginMetadata(
    name="nonebot_plugin_auth_link",
    description="发送「授权 群号」生成 AI 群服务协议授权跳转链接(配合指令面板使用)",
    usage="授权 —— 查看当前会话 openid 与说明\n授权 群号 —— 生成授权链接",
    type="application",
)

# AI 群服务协议授权页跳转模板（open_kuikly_info 为 URL 编码的 JSON）
_URL_TEMPLATE = (
    "https://club.vip.qq.com/transfer?open_kuikly_info="
    "%7b%22page_name%22%3a+%22ai_group_service_agreement_pop_page%22%2c"
    "%22groupCode%22%3a{group_code}"
    "%2c%22botUin%22%3a+{bot_uin}"
    "%2c%22botUid%22%3a%22%22%2c%22screen%22%3a1%7d"
)


def _get_bot_uin() -> str:
    """读取 .env 中的 QBOT_QQ（机器人 QQ 号）。"""
    return str(getattr(get_driver().config, "qbot_qq", "") or "").strip()


def _openid_info(event: Event) -> str:
    """当前会话 openid: 群聊展示 group_openid, C2C 展示用户 openid。"""
    group_openid = getattr(event, "group_openid", None)
    return (
        f"群 openid: {group_openid}"
        if group_openid
        else f"用户 openid: {event.get_user_id()}"
    )


def _build_result(group_code: str, url: str) -> Message:
    """授权链接结果卡片(纯 markdown 文本, 无按钮)。"""
    return Message(
        MessageSegment.markdown(
            f"## ✅ 授权链接已生成\n"
            f"**群号：** {group_code}\n"
            f"[👉 点击前往授权页面]({url})"
        )
    )


auth_link = on_command("授权", priority=10, block=True)


@auth_link.handle()
async def handle_auth(
    matcher: Matcher, event: Event, args: BaseMessage = CommandArg()
) -> None:
    bot_uin = _get_bot_uin()
    if not bot_uin:
        await matcher.finish("未配置 QBOT_QQ，请联系管理员在 .env 中添加后重启")

    group_code = args.extract_plain_text().strip()

    # 无参数：返回 openid 与使用说明
    if not group_code:
        await matcher.finish(
            "🔐 AI 群服务授权\n"
            f"当前会话 {_openid_info(event)}\n"
            "发送「授权 群号」生成授权链接（指令面板点击「授权」后补全群号即可）\n"
            "---\n"
            "🔒 授权仅群主可用\n"
            "如群内收不到机器人消息或无法发言：右上角三条线 → 群机器人 → 管理 → "
            "在「机器人可获取的群聊消息范围」和「机器人主动在群聊内发言」中调整"
        )

    if not group_code.isdigit() or not 5 <= len(group_code) <= 15:
        await matcher.reject("群号应为纯数字（5~15 位），请重新发送「授权 群号」")

    url = _URL_TEMPLATE.format(group_code=group_code, bot_uin=bot_uin)
    await matcher.finish(_build_result(group_code, url))
