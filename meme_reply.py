import re
import base64
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class MemeReplyResult:
    has_image: bool
    image_base64: Optional[str] = None
    image_filename: Optional[str] = None
    text: str = ""


class MemeReplyParser:
    IMG_PATTERN = re.compile(r'\[img\]\[([^\]]+)\]')
    
    @classmethod
    def extract_filename(cls, text: str) -> Optional[str]:
        match = cls.IMG_PATTERN.search(text)
        if match:
            return match.group(1)
        return None
    
    @classmethod
    def remove_img_tag(cls, text: str) -> str:
        return cls.IMG_PATTERN.sub('', text).strip()
    
    @classmethod
    def parse(cls, text: str) -> tuple[str, Optional[str]]:
        filename = cls.extract_filename(text)
        clean_text = cls.remove_img_tag(text)
        return clean_text, filename


class MemeReplyProcessor:
    def __init__(self, memes_dir: str, enabled: bool = True):
        self.memes_dir = Path(memes_dir)
        self.enabled = enabled
    
    def process(self, text: str) -> MemeReplyResult:
        if not self.enabled:
            return MemeReplyResult(has_image=False, text=text)
        
        filename = MemeReplyParser.extract_filename(text)
        clean_text = MemeReplyParser.remove_img_tag(text)
        
        if not filename:
            return MemeReplyResult(has_image=False, text=text)
        
        file_path = self.memes_dir / filename
        if not file_path.exists():
            return MemeReplyResult(
                has_image=False, 
                text=clean_text,
                image_filename=filename
            )
        
        try:
            with open(file_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            return MemeReplyResult(
                has_image=True,
                image_base64=image_data,
                image_filename=filename,
                text=clean_text
            )
        except Exception:
            return MemeReplyResult(
                has_image=False,
                text=clean_text,
                image_filename=filename
            )
    
    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
    
    @property
    def is_enabled(self) -> bool:
        return self.enabled
