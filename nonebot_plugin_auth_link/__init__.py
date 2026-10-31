"""AI 群服务授权卡片插件：发送「授权」签发授权卡片。

流程（基于 QQ 官方 Bot 群聊实测）：
- 群聊中按钮点击均为「指令预填」，无 INTERACTION_CREATE，故采用指令按钮方案
- 卡片按钮预填「/授权 <token>」，用户在输入框补全群号后发送（卡内填写的近似实现）
- 插件只接受带有效 token 的消息（token 校验使用者、24h 有效），卡片外直接发群号无效
- 无 got 会话、无被动窗口依赖，不存在超时

机器人 QQ 号从 .env 的 QBOT_QQ 读取。
"""

from __future__ import annotations

import secrets
import time

from nonebot import get_driver, on_command
from nonebot.adapters import Event
from nonebot.adapters.qq import Message, MessageSegment
from nonebot.adapters.qq.models import (
    Action,
    InlineKeyboard,
    InlineKeyboardRow,
    MessageKeyboard,
    Permission,
    Button,
    RenderData,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.adapters import Message as BaseMessage

__plugin_meta__ = PluginMetadata(
    name="nonebot_plugin_auth_link",
    description="发送「授权」签发授权卡片，卡片按钮预填口令，在输入框补全群号生成 AI 群服务协议授权链接",
    usage="发送「授权」获取卡片 → 点击按钮 → 补全群号后发送；卡片外发送群号无效。",
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

# token 有效期（秒）：无会话超时，仅防口令被无限期冒用
_TOKEN_TTL = 24 * 3600
# 每个用户/会话最多记忆的常用群号
_RECENT_LIMIT = 6

# 已签发的 token: token -> (user_openid, 签发时间)
_tokens: dict[str, tuple[str, float]] = {}
# 常用群号记忆: user_openid -> [群号, ...]
_recent_groups: dict[str, list[str]] = {}


def _get_bot_uin() -> str:
    """读取 .env 中的 QBOT_QQ（机器人 QQ 号）。"""
    return str(getattr(get_driver().config, "qbot_qq", "") or "").strip()


def _issue_token(user_id: str) -> str:
    """签发新 token 并清理过期项。"""
    now = time.time()
    expired = [t for t, (_, ts) in _tokens.items() if now - ts > _TOKEN_TTL]
    for t in expired:
        del _tokens[t]
    token = secrets.token_hex(4)
    _tokens[token] = (user_id, now)
    return token


def _remember_group(user_id: str, group_code: str) -> None:
    """记录该用户最近授权过的群号，供卡片生成快捷按钮。"""
    groups = _recent_groups.setdefault(user_id, [])
    if group_code in groups:
        groups.remove(group_code)
    groups.insert(0, group_code)
    del groups[_RECENT_LIMIT:]


def _button(label: str, data: str) -> Button:
    """构造指令预填按钮（群聊中点击即为预填，发送需用户确认）。"""
    return Button(
        id=f"auth_{secrets.token_hex(4)}",
        render_data=RenderData(label=label, visited_label=label, style=0),
        action=Action(
            type=2,
            data=data,
            enter=False,  # 预填不自动发送，用户补全/确认后发送
            permission=Permission(type=2),  # 所有人可点（按实测 permission.type=2 全员有效）
        ),
    )


def _build_card(token: str, user_id: str, openid_info: str = "") -> Message:
    """签发授权卡片：markdown 说明 + 指令按钮（预填 token）。"""
    openid_line = f"**当前会话 {openid_info}**\n" if openid_info else ""
    md = MessageSegment.markdown(
        "## 🔐 AI 群服务授权\n"
        f"{openid_line}"
        "点击下方按钮，在输入框**补全群号**后发送，即可生成授权链接\n"
        "---\n"
        "⚠️ 出于安全考虑，仅限通过本卡片按钮发起，**直接发送群号无效**\n"
        "🔒 授权仅群主可用\n"
        "如群内收不到机器人消息或无法发言：右上角三条线 → 群机器人 → 管理 → "
        "在「机器人可获取的群聊消息范围」和「机器人主动在群聊内发言」中调整"
    )
    rows = [InlineKeyboardRow(buttons=[_button("✏️ 填写群号", f"/授权 {token} ")])]
    recent = _recent_groups.get(user_id, [])
    if recent:
        rows.append(
            InlineKeyboardRow(
                buttons=[_button(f"群 {g}", f"/授权 {token} {g}") for g in recent]
            )
        )
    keyboard = MessageSegment.keyboard(MessageKeyboard(content=InlineKeyboard(rows=rows)))
    return Message([md, keyboard])


def _build_result(group_code: str, url: str) -> Message:
    """授权链接结果卡片。"""
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

    parts = args.extract_plain_text().split()
    user_id = event.get_user_id()

    # 当前会话的 openid: 群聊展示 group_openid, C2C 展示用户 openid
    group_openid = getattr(event, "group_openid", None)
    openid_info = (
        f"群 openid: {group_openid}" if group_openid else f"用户 openid: {user_id}"
    )

    # 无参数：签发新卡片
    if not parts:
        token = _issue_token(user_id)
        await matcher.finish(_build_card(token, user_id, openid_info))

    # 带参数：token(+群号) 回填路径
    token = parts[0]
    info = _tokens.get(token)
    if info is None:
        await matcher.finish("口令无效或已过期，请发送「授权」重新获取卡片")
    if info[0] != user_id:
        await matcher.finish("该口令不属于当前用户，请自行发送「授权」获取卡片")

    # 仅 token：视为点按钮后未补全群号
    if len(parts) == 1:
        await matcher.reject("请在口令后补全群号，例如「/授权 口令 123456789」")

    group_code = parts[1]
    if not group_code.isdigit() or not 5 <= len(group_code) <= 15:
        await matcher.reject("群号应为纯数字（5~15 位），请重新补全后发送")

    # token 剩余参数忽略；校验通过后生成链接
    if time.time() - info[1] > _TOKEN_TTL:
        del _tokens[token]
        await matcher.finish("口令已过期，请发送「授权」重新获取卡片")

    _remember_group(user_id, group_code)
    url = _URL_TEMPLATE.format(group_code=group_code, bot_uin=bot_uin)
    await matcher.finish(_build_result(group_code, url))
