import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from web import MemeWebServer


if __name__ == "__main__":
    memes_dir = Path(__file__).parent / "memes"
    memes_dir.mkdir(exist_ok=True)
    
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
