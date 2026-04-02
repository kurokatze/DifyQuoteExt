import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from web import MemeWebServer

PLUGIN_NAME = "DifyQuoteExt"

try:
    from astrbot.core.utils.astrbot_path import get_astrbot_data_path
    def get_memes_dir() -> Path:
        return Path(get_astrbot_data_path()) / "plugin_data" / PLUGIN_NAME
except ImportError:
    def get_memes_dir() -> Path:
        return Path(__file__).parent / "memes"


if __name__ == "__main__":
    memes_dir = get_memes_dir()
    memes_dir.mkdir(parents=True, exist_ok=True)
    
    plugin_dir = Path(__file__).parent
    emotions_file = plugin_dir / "memes" / "config.json"
    
    server = MemeWebServer(str(memes_dir), emotions_file=str(emotions_file))
    
    print("=" * 50)
    print("🎭 Meme Web Server 启动中...")
    print(f"📍 访问地址: http://localhost:6186")
    print(f"📁 图片存储目录: {memes_dir.absolute()}")
    print(f"📄 表情配置: {emotions_file}")
    print("=" * 50)
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
