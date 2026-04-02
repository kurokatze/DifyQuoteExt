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
    
    server = MemeWebServer(str(memes_dir), host="0.0.0.0", port=6186)
    
    print("=" * 50)
    print("🎭 Meme Web Server 启动中...")
    print(f"📍 访问地址: http://localhost:6186")
    print(f"📁 图片存储目录: {memes_dir.absolute()}")
    print("=" * 50)
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
