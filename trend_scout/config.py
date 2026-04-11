"""
Configuration for the Trend Scout service.
Defines target URLs, CSS selectors, and LLM prompts.
"""

# ---------------------------------------------------------------------------
# API Configuration
# ---------------------------------------------------------------------------
GEMINI_MODEL = "gemini-2.5-flash-lite"

# ---------------------------------------------------------------------------
# Scraper Configuration
# ---------------------------------------------------------------------------
# Timeout per page in milliseconds
PAGE_TIMEOUT_MS = 30_000

# Maximum headlines to collect per source
MAX_HEADLINES_PER_SOURCE = 5

# Target websites with their CSS selectors for headline extraction.
# Each entry: name, url, headline_selector, link_selector (optional, defaults to 'a' inside headline),
# article_body_selector (for Phase 2 content extraction)
SCRAPE_TARGETS = [
    {
        "name": "VnExpress Sức Khỏe",
        "url": "https://vnexpress.net/suc-khoe",
        "headline_selector": "h3.title-news a, h2.title-news a",
        "article_body_selector": "article.fck_detail p.Normal",
    },
    {
        "name": "Dân Trí Góc Phụ Huynh",
        "url": "https://dantri.com.vn/giao-duc/goc-phu-huynh.htm",
        "headline_selector": "h3.article-title a, h2.article-title a",
        "article_body_selector": "div.singular-content p",
    },
    {
        "name": "Làm Cha Mẹ",
        "url": "https://lamchame.com",
        "headline_selector": "h2 a, h3 a",
        "article_body_selector": "div.entry-content p, div.content-detail p, article p",
    },
    {
        "name": "WebTrẻThơ Sức Khỏe",
        "url": "https://www.webtretho.vn/thinh-hanh/suc-khoe-doi-song",
        "headline_selector": "h3 a, a.thread-title, div.thread-item a",
        "article_body_selector": "div.post-content p, div.message-body p, article p",
    },
    {
        "name": "WebTrẻThơ Làm Mẹ",
        "url": "https://www.webtretho.vn/thinh-hanh/lam-me",
        "headline_selector": "h3 a, a.thread-title, div.thread-item a",
        "article_body_selector": "div.post-content p, div.message-body p, article p",
    },
    {
        "name": "ZEIT Online Kindererziehung",
        "url": "https://www.zeit.de/thema/kindererziehung",
        "headline_selector": "article a[href*='/familie/'], article a[href*='/zeit-magazin/'], h3 a, span.zon-teaser-standard__title",
        "article_body_selector": "div.article__item p.paragraph, div.article-page p",
        "consent_selector": None,
    },
    {
        "name": "Spiegel Erziehung",
        "url": "https://www.spiegel.de/thema/erziehung/",
        "headline_selector": "article a[title], a[data-sara-click-el='title'] span, section a span.align-middle",
        "article_body_selector": "article section div[data-word-count] p, div.RichText p",
        "consent_selector": "button[title='Einwilligen'], button.sp_choice_type_11",
    }
]

# ---------------------------------------------------------------------------
# Blocked resource types for faster scraping (no images, css, fonts)
# ---------------------------------------------------------------------------
BLOCKED_RESOURCE_TYPES = ["image", "stylesheet", "font", "media"]

# ---------------------------------------------------------------------------
# LLM Prompts
# ---------------------------------------------------------------------------

TOPIC_SELECTION_PROMPT = """Bạn là một chuyên gia về nội dung viral trên TikTok và YouTube Shorts, chuyên về chủ đề gia đình, nuôi dạy con cái, tâm lý tuổi teen và sức khỏe đời sống tại Việt Nam.

Dưới đây là danh sách các tiêu đề bài viết mới nhất từ nhiều trang web (cả tiếng Việt và tiếng Đức). Mỗi tiêu đề có một số thứ tự.

LƯU Ý: Một số tiêu đề có thể bằng tiếng Đức (từ trang zeit.de hoặc spiegel.de). Hãy hiểu nội dung và đánh giá chúng bình đẳng với các tiêu đề tiếng Việt.

DANH SÁCH TIÊU ĐỀ:
{headlines}

NHIỆM VỤ:
Hãy chọn MỘT tiêu đề TỐT NHẤT để làm video ngắn (TikTok/YouTube Shorts). Tiêu đề phải:
1. Có tính viral cao - khiến người xem muốn chia sẻ
2. Tích cực và cảm động (touching) - mang lại cảm xúc ấm áp
3. Liên quan đến: nuôi dạy con, gia đình, tâm lý tuổi teen, hoặc sức khỏe và đời sống
4. KHÔNG chọn quảng cáo, bài PR, hoặc tin tức chính trị tiêu cực

Trả lời CHỈ bằng JSON với format sau, KHÔNG thêm text nào khác:
{{"index": <số thứ tự của tiêu đề được chọn>, "reason": "<lý do ngắn gọn bằng tiếng Việt>"}}
"""

CONTENT_GENERATION_PROMPT = """Bạn là một nhà sáng tạo nội dung chuyên nghiệp cho TikTok/YouTube Shorts về chủ đề gia đình, tâm lý tuổi teen, và sức khỏe tại Việt Nam.

TIÊU ĐỀ ĐÃ CHỌN:
{title}

NỘI DUNG BÀI VIẾT GỐC (có thể bằng tiếng Đức hoặc tiếng Việt):
{article_text}

NHIỆM VỤ:
Dựa trên tiêu đề và nội dung bài viết (hoặc kiến thức của bạn nếu bài viết quá ngắn), hãy tạo nội dung cho video ngắn.

QUAN TRỌNG: Tất cả nội dung output PHẢI bằng TIẾNG VIỆT, kể cả khi bài viết gốc bằng tiếng Đức. Hãy chuyển ý tưởng sang bối cảnh Việt Nam.

1. **title**: Tiêu đề hấp dẫn, viral cho video (tiếng Việt, tối đa 100 ký tự)
2. **description**: Mô tả VẤN ĐỀ/TÌNH HUỐNG - câu chuyện hoặc thử thách mà các bậc cha mẹ gặp phải (tiếng Việt, 2-4 câu)
3. **solution**: GIẢI PHÁP/LỜI KHUYÊN cụ thể - có thể lấy trực tiếp từ bài viết hoặc bạn tự đề xuất dựa trên kiến thức chuyên môn (tiếng Việt, 3-5 câu, thiết thực và cảm động)

Giọng văn: ấm áp, gần gũi, như một người bạn chia sẻ kinh nghiệm.

Trả lời CHỈ bằng JSON với format sau, KHÔNG thêm text nào khác:
{{"title": "...", "description": "...", "solution": "..."}}
"""

# ---------------------------------------------------------------------------
# Output Configuration
# ---------------------------------------------------------------------------
OUTPUT_DIR = "output"
OUTPUT_FILENAME = "thema.json"
HISTORY_FILENAME = "historie.json"
