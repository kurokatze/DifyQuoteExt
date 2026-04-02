import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from quart import Quart, request, jsonify, send_from_directory
from hypercorn.asyncio import serve
from hypercorn.config import Config as HyperConfig

from .meme_config import MemeConfig

logger = logging.getLogger("MemeWebServer")

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"RIFF": "webp",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
}


def allowed_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def verify_image_content(file_path: str) -> bool:
    try:
        with open(file_path, "rb") as f:
            header = f.read(16)
            for signature in IMAGE_SIGNATURES:
                if header.startswith(signature):
                    return True
            return False
    except Exception:
        return False


def is_safe_filename(filename: str) -> bool:
    if not filename:
        return False
    dangerous_patterns = ["..", "/", "\\", "\x00", "\n", "\r"]
    for pattern in dangerous_patterns:
        if pattern in filename:
            return False
    return True


class MemeWebServer:
    def __init__(self, memes_dir: str, emotions_file: str | None = None, host: str = "0.0.0.0", port: int = 6186):
        self.memes_dir = Path(memes_dir)
        self.memes_dir.mkdir(parents=True, exist_ok=True)
        
        self.host = host
        self.port = port
        self.server_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        web_dir = Path(__file__).parent
        self.static_folder = web_dir / "static"
        self.meme_config = MemeConfig(str(self.memes_dir), emotions_file)
        self.app = self._create_app(web_dir)

    def _create_app(self, web_dir: Path) -> Quart:
        app = Quart(
            "meme_server",
            static_folder=str(web_dir / "static"),
            static_url_path="/static"
        )
        app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
        
        app.before_serving(self._startup)
        app.after_serving(self._shutdown)
        
        self._register_routes(app)
        return app

    async def _startup(self) -> None:
        logger.info(f"Meme Web Server starting on {self.host}:{self.port}")

    async def _shutdown(self) -> None:
        logger.info("Meme Web Server shutting down")

    def _register_routes(self, app: Quart) -> None:
        
        @app.route("/")
        async def index():
            return await send_from_directory(str(self.static_folder), "index.html")

        @app.route("/api/memes", methods=["GET"])
        async def get_memes():
            memes = self.meme_config.get_all_memes()
            return jsonify([
                {
                    "filename": m.filename,
                    "name": m.name,
                    "tags": m.tags,
                    "created_at": m.created_at,
                    "url": f"/memes/{m.filename}"
                }
                for m in memes
            ])

        @app.route("/api/memes", methods=["POST"])
        async def add_meme():
            form = await request.form
            files = await request.files
            name = form.get("name", "").strip()
            tags_str = form.get("tags", "").strip()
            
            file = files.get("file")
            
            if not file:
                return jsonify({"error": "没有上传文件"}), 400
            
            if not allowed_file(file.filename):
                return jsonify({"error": "不支持的文件格式，仅支持: jpg, jpeg, png, webp, gif"}), 400
            
            if not name:
                return jsonify({"error": "请输入表情名称"}), 400
            
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            
            ext = file.filename.rsplit(".", 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{ext}"
            
            file_path = self.memes_dir / unique_filename
            await file.save(str(file_path))
            
            if not verify_image_content(str(file_path)):
                file_path.unlink(missing_ok=True)
                return jsonify({"error": "文件内容不是有效的图片"}), 400
            
            created_at = datetime.now().isoformat()
            meme = self.meme_config.add_meme(unique_filename, name, tags, created_at)
            
            return jsonify({
                "filename": meme.filename,
                "name": meme.name,
                "tags": meme.tags,
                "created_at": meme.created_at,
                "url": f"/memes/{meme.filename}"
            }), 201

        @app.route("/api/memes/<filename>", methods=["PUT"])
        async def update_meme(filename: str):
            if not is_safe_filename(filename):
                return jsonify({"error": "无效的文件名"}), 400
            data = await request.get_json()
            
            name = data.get("name")
            tags = data.get("tags")
            
            if name is None and tags is None:
                return jsonify({"error": "请提供要更新的字段"}), 400
            
            meme = self.meme_config.update_meme(filename, name=name, tags=tags)
            if not meme:
                return jsonify({"error": "表情不存在"}), 404
            
            return jsonify({
                "filename": meme.filename,
                "name": meme.name,
                "tags": meme.tags,
                "created_at": meme.created_at,
                "url": f"/memes/{meme.filename}"
            })

        @app.route("/api/memes/<filename>", methods=["DELETE"])
        async def delete_meme(filename: str):
            if not is_safe_filename(filename):
                return jsonify({"error": "无效的文件名"}), 400
            if self.meme_config.delete_meme(filename):
                return jsonify({"message": "删除成功"})
            return jsonify({"error": "表情不存在"}), 404

        @app.route("/api/memes/<filename>", methods=["GET"])
        async def get_meme(filename: str):
            if not is_safe_filename(filename):
                return jsonify({"error": "无效的文件名"}), 400
            meme = self.meme_config.get_meme(filename)
            if not meme:
                return jsonify({"error": "表情不存在"}), 404
            
            return jsonify({
                "filename": meme.filename,
                "name": meme.name,
                "tags": meme.tags,
                "created_at": meme.created_at,
                "url": f"/memes/{meme.filename}"
            })

        @app.route("/api/tags", methods=["GET"])
        async def get_tags():
            tags = list(self.meme_config.get_all_tags())
            return jsonify(sorted(tags))

        @app.route("/api/emotions", methods=["GET"])
        async def get_emotions():
            emotions = self.meme_config.get_emotions()
            return jsonify(emotions)

        @app.route("/api/memelist", methods=["GET"])
        async def get_meme_list():
            memes = self.meme_config.get_all_memes()
            return jsonify([
                {
                    "filename": m.filename,
                    "name": m.name,
                    "tags": m.tags
                }
                for m in memes
            ])

        @app.route("/api/memes/search", methods=["GET"])
        async def search_memes():
            keyword = request.args.get("q", "").strip()
            if not keyword:
                return jsonify([])
            
            memes = self.meme_config.search(keyword)
            return jsonify([
                {
                    "filename": m.filename,
                    "name": m.name,
                    "tags": m.tags,
                    "created_at": m.created_at,
                    "url": f"/memes/{m.filename}"
                }
                for m in memes
            ])

        @app.route("/memes/<filename>")
        async def serve_meme(filename: str):
            if not is_safe_filename(filename):
                return jsonify({"error": "无效的文件名"}), 400
            
            if not self.meme_config.get_meme(filename):
                return jsonify({"error": "表情不存在"}), 404
            
            return await send_from_directory(str(self.memes_dir), filename)

    async def start(self) -> None:
        config = HyperConfig()
        config.bind = [f"{self.host}:{self.port}"]
        config.accesslog = None
        config.errorlog = None
        
        await serve(self.app, config)

    def run(self) -> None:
        asyncio.run(self.start())
