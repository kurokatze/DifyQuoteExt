import datetime
import json
import zoneinfo
from collections import defaultdict

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.provider import LLMResponse, ProviderRequest
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.message.components import Image, Reply, Plain, At

@register("DifyQuoteExt", "MadCat", "DifyQuoteExt for AstrBot", "1.0.0")
class DifyQuoteExt(Star):
    def __init__(self, context: Context):
        super().__init__(context)

        """记录群成员的群聊记录"""
        self.session_chats = defaultdict(list)

        cfg = context.get_config()
        self.timezone = cfg.get("timezone")
        
    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    @filter.on_llm_request()
    async def on_request(self, event: AstrMessageEvent, req: ProviderRequest): # 请注意有三个参数
        sys_prompt_json = {}

        """基本信息"""
        info_json = {}
        if event.message_obj.group_id:
            info_json["isGroup"] = True
            if event.message_obj.group:
                info_json["groupName"] = event.message_obj.group.group_name or "[null]"
            else:
                info_json["groupName"] = "[null]"
        else:
            info_json["isGroup"] = False

        current_time = None
        if self.timezone:
            # 启用时区
            try:
                now = datetime.datetime.now(zoneinfo.ZoneInfo(self.timezone))
                current_time = now.strftime("%Y-%m-%d %H:%M (%Z)")
            except Exception as e:
                logger.error(f"时区设置错误: {e}, 使用本地时区")
        if not current_time:
            current_time = (
                datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M (%Z)")
            )
        info_json["dateTime"] = current_time
        sys_prompt_json["info"] = info_json

        """引用"""
        quote = None
        for comp in event.message_obj.message:
            if isinstance(comp, Reply):
                quote = comp
                break
        if quote:
            quote_json = {}
            quote_json["sender"] = quote.sender_nickname or "[null]"
            quote_json["message"] = quote.message_str or "[Empty Text]"
            
            # 处理引用图片
            image_seg = None
            if quote.chain:
                for comp in quote.chain:
                    if isinstance(comp, Image):
                        image_seg = comp
                        break
            if image_seg:
                try:
                    req.image_urls.append(await image_seg.convert_to_base64())
                    quote_json["containImage"] = True
                except BaseException as e:
                    logger.error(f"处理引用图片失败: {e}")
                    quote_json["containImage"] = False
            else:
                quote_json["containImage"] = False
            sys_prompt_json["quote"] = quote_json

        """聊天记录"""
        history_json = []
        for chat_log in self.session_chats[event.unified_msg_origin]:
            history_json.append(chat_log)

        sys_prompt_json["history"] = history_json
        req.system_prompt += f"\n[json]\n{json.dumps(sys_prompt_json, ensure_ascii=False)}\n[json_end]\n"

    """记录群聊消息"""
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent):
        datetime_str = datetime.datetime.now().strftime("%H:%M:%S")

        parts = [f"[{datetime_str}][{event.message_obj.sender.nickname}]: "]

        for comp in event.get_messages():
            if isinstance(comp, Plain):
                parts.append(f" {comp.text}")
            elif isinstance(comp, Image):
                parts.append(" [图片]")
            elif isinstance(comp, At):
                parts.append(f" [At: {comp.name}]")

        final_message = "".join(parts)
        logger.debug(f"ltm | {event.unified_msg_origin} | {final_message}")
        self.session_chats[event.unified_msg_origin].append(final_message)

        """获取群聊最大消息数量"""
        cfg = self.context.get_config(umo=event.unified_msg_origin)
        try:
            max_cnt = int(cfg["provider_ltm_settings"]["group_message_max_cnt"])
        except BaseException as e:
            logger.error(e)
            max_cnt = 100

        while len(self.session_chats[event.unified_msg_origin]) > max_cnt:
            self.session_chats[event.unified_msg_origin].pop(0)

    @filter.on_llm_response()
    async def on_llm_resp(self, event: AstrMessageEvent, resp: LLMResponse): # 请注意有三个参数
        """并非群聊消息，忽略"""
        if not event.message_obj.group_id:
            return

        if event.unified_msg_origin not in self.session_chats:
            return

        datetime_str = datetime.datetime.now().strftime("%H:%M:%S")

        if resp.completion_text:
            parts = [f"[{datetime_str}][你]: "]
            parts.append(f" {resp.completion_text}")                
            final_message = "".join(parts)
            logger.debug(
                    f"Recorded AI response: {event.unified_msg_origin} | {final_message}"
                )
            self.session_chats[event.unified_msg_origin].append(final_message)
            """获取群聊最大消息数量"""
            cfg = self.context.get_config(umo=event.unified_msg_origin)
            try:
                max_cnt = int(cfg["provider_ltm_settings"]["group_message_max_cnt"])
            except BaseException as e:
                logger.error(e)
                max_cnt = 100

            while len(self.session_chats[event.unified_msg_origin]) > max_cnt:
                self.session_chats[event.unified_msg_origin].pop(0)

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
