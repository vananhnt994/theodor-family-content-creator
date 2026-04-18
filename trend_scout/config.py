"""
Configuration for the Trend Scout service.
Defines target URLs, CSS selectors, and LLM prompts.
"""

# ---------------------------------------------------------------------------
# API Configuration
# ---------------------------------------------------------------------------
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from channel_config import load_channel_config

channel_cfg = load_channel_config()

GEMINI_MODEL = "gemini-2.5-flash-lite"

# ---------------------------------------------------------------------------
# Scraper Configuration
# ---------------------------------------------------------------------------
# Timeout per page in milliseconds
PAGE_TIMEOUT_MS = 30_000

# Maximum headlines to collect per source
MAX_HEADLINES_PER_SOURCE = 5

SCRAPE_TARGETS = channel_cfg.get("scraping_sources", [])

# ---------------------------------------------------------------------------
# Blocked resource types for faster scraping (no images, css, fonts)
# ---------------------------------------------------------------------------
BLOCKED_RESOURCE_TYPES = ["image", "stylesheet", "font", "media"]

# ---------------------------------------------------------------------------
# LLM Prompts
# ---------------------------------------------------------------------------

TOPIC_SELECTION_PROMPT = f"""Bạn là một chuyên gia về nội dung viral trên TikTok và YouTube Shorts, chuyên về chủ đề {channel_cfg.get('topic', 'gia đình')}. Bạn hãy làm theo ngôn ngữ {channel_cfg.get('language', 'Vietnamesisch')}.

Dưới đây là danh sách các tiêu đề bài viết mới nhất từ nhiều trang web. Mỗi tiêu đề có một số thứ tự.

LƯU Ý: Một số tiêu đề có thể viết bằng ngôn ngữ khác. Hãy hiểu nội dung và đánh giá chúng bình đẳng.

DANH SÁCH TIÊU ĐỀ:
{{headlines}}

NHIỆM VỤ:
Hãy chọn MỘT tiêu đề TỐT NHẤT để làm video ngắn (TikTok/YouTube Shorts). Tiêu đề phải:
1. Có tính viral cao - khiến người xem muốn chia sẻ
2. Tích cực và cảm động (touching)
3. Liên quan đến: {channel_cfg.get('topic', 'gia đình, nuôi dạy con')}
4. KHÔNG chọn quảng cáo, bài PR, hoặc tin tức chính trị tiêu cực

Trả lời CHỈ bằng JSON với format sau, KHÔNG thêm text nào khác:
{{
  "index": <số thứ tự của tiêu đề được chọn>, 
  "reason": "<lý do ngắn gọn bằng {channel_cfg.get('language', 'Vietnamesisch')}>"
}}
"""

CONTENT_GENERATION_PROMPT = f"""Bạn là một nhà sáng tạo nội dung chuyên nghiệp cho TikTok/YouTube Shorts về chủ đề {channel_cfg.get('topic', 'gia đình')}.

TIÊU ĐỀ ĐÃ CHỌN:
{{title}}

NỘI DUNG BÀI VIẾT GỐC:
{{article_text}}

NHIỆM VỤ:
Dựa trên tiêu đề và nội dung bài viết, hãy tạo nội dung cho video ngắn.

QUAN TRỌNG: Tất cả nội dung output PHẢI bằng {channel_cfg.get('language', 'Vietnamesisch')}, kể cả khi bài viết gốc bằng ngôn ngữ khác.

1. **title**: Tiêu đề hấp dẫn, viral cho video (tối đa 100 ký tự)
2. **description**: Mô tả VẤN ĐỀ/TÌNH HUỐNG (2-4 câu)
3. **solution**: GIẢI PHÁP/LỜI KHUYÊN cụ thể (3-5 câu thiết thực và cảm động)

Giọng văn: ấm áp, gần gũi, như một người bạn chia sẻ kinh nghiệm.

Trả lời CHỈ bằng JSON với format sau, KHÔNG thêm text nào khác:
{{
  "title": "...", 
  "description": "...", 
  "solution": "..."
}}
"""

# ---------------------------------------------------------------------------
# Output Configuration
# ---------------------------------------------------------------------------
OUTPUT_DIR = "output"
OUTPUT_FILENAME = "thema.json"
HISTORY_FILENAME = "historie.json"
