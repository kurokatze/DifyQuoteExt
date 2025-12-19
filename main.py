from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.message.components import Image, Reply

@register("DifyQuoteExt", "MadCat", "DifyQuoteExt for AstrBot", "1.0.0")
class DifyQuoteExt(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    @filter.on_llm_request()
    async def on_request(self, event: AstrMessageEvent, req: ProviderRequest): # 请注意有三个参数
        quote = None
        for comp in event.message_obj.message:
            if isinstance(comp, Reply):
                quote = comp
                break
        if quote:
            sender_info = quote.sender_nickname or "[null]"
            message_str = quote.message_str or "[Empty Text]"
            req.system_prompt += (
                f"\n[quote]\n"
                "{\n"
                f"  \"sender\": \"{sender_info}\"\n"
                f"  \"message\": \"{message_str}\"\n"
                # f"[quote_end]\n"
            )
            
            # 处理引用图片
            image_seg = None
            if quote.chain:
                for comp in quote.chain:
                    if isinstance(comp, Image):
                        image_seg = comp
                        break
            if image_seg:
                try:
                    req.image_urls.append(await image_seg.convert_to_file_path())
                    req.system_prompt += (
                        f"  \"image\": true\n"
                    )
                except BaseException as e:
                    logger.error(f"处理引用图片失败: {e}")
            req.system_prompt += (
                "}\n"
                f"[quote_end]\n"
            )

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
