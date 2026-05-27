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
{{{{
  "index": <số thứ tự của tiêu đề được chọn>, 
  "reason": "<lý do ngắn gọn bằng {channel_cfg.get('language', 'Vietnamesisch')}>"
}}}}
"""

CONTENT_GENERATION_PROMPT = f"""Bạn là một nhà sáng tạo nội dung chuyên nghiệp cho TikTok/YouTube Shorts về chủ đề {channel_cfg.get('topic', 'gia đình')}.
Nhiệm vụ của bạn là tìm ra GIÁ TRỊ CỐT LÕI và LỜI KHUYÊN THIẾT THỰC nhất từ văn bản dưới đây để giúp ích cho cha mẹ trong việc nuôi dạy con cái.

TIÊU ĐỀ ĐÃ CHỌN:
{{title}}

NỘI DUNG BÀI VIẾT GỐC:
{{article_text}}

NHIỆM VỤ:
Dựa trên tiêu đề và nội dung bài viết, hãy tạo nội dung cho video ngắn. Tập trung tối đa vào giá trị giáo dục và tính ứng dụng thực tế.

QUAN TRỌNG: Tất cả nội dung output PHẢI bằng {channel_cfg.get('language', 'Vietnamesisch')}, kể cả khi bài viết gốc bằng ngôn ngữ khác.

TUYỆT ĐỐI KHÔNG SỬ DỤNG TÊN RIÊNG: Không sử dụng bất kỳ tên riêng nào cho nhân vật. Hãy thay thế bằng các vai trò chung như "cha mẹ", "người mẹ", "người cha", "đứa trẻ", "con cái"...

1. **title**: Tiêu đề cực kỳ thu hút, đánh đúng vào nỗi đau hoặc mong muốn của cha mẹ (tối đa 100 ký tự).
2. **description**: Mô tả VẤN ĐỀ hoặc TÌNH HUỐNG thực tế mà cha mẹ hay gặp phải (2-3 câu). Phải làm nổi bật TẠI SAO vấn đề này lại quan trọng.
3. **solution**: GIẢI PHÁP hoặc BÀI HỌC then chốt. Phải là những bước hành động cụ thể, dễ hiểu và có giá trị giáo dục cao. Đừng viết chung chung, hãy viết sao cho cha mẹ có thể áp dụng được ngay (3-5 câu).

Giọng văn: Chân thành, chuyên gia nhưng gần gũi, mang tính xây dựng và tích cực.

Trả lời CHỈ bằng JSON với format sau, KHÔNG thêm text nào khác:
{{{{
  "title": "...", 
  "description": "...", 
  "solution": "..."
}}}}
"""

# ---------------------------------------------------------------------------
# Output Configuration
# ---------------------------------------------------------------------------
OUTPUT_DIR = "output"
OUTPUT_FILENAME = "thema.json"
HISTORY_SHORTS_FILENAME = "historie_shorts.json"
HISTORY_LONG_FILENAME = "historie_long.json"
HISTORY_LONG_NATUR_FILENAME = "historie_long_natur.json"
# Legacy alias (used by existing shorts pipeline)
HISTORY_FILENAME = HISTORY_SHORTS_FILENAME
