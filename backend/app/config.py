"""Cấu hình tập trung (tương đương appsettings.json + IOptions<T> bên .NET)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Hạ tầng ---
    # agent-db (docker-compose.override.yml của librechat) map ra cổng 5433 trên máy host.
    # Tách hẳn khỏi vectordb của LibreChat: kho tri thức doanh nghiệp có ACL riêng.
    database_url: str = "postgresql+psycopg://agent:agent@localhost:5433/agent"
    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 480

    # --- LLM ---
    # claude: gọi Claude API qua Anthropic SDK | fake: chạy offline không cần API key (demo/test)
    # local: model cục bộ qua API tương thích OpenAI (LocalAI), hiện chỉ dùng cho bước sinh câu trả lời RAG
    llm_provider: str = "claude"
    local_llm_base_url: str = "http://localhost:8080/v1"  # LocalAI publish cổng 8080 ra máy host
    local_llm_model: str = "qwen3-4b"
    local_llm_max_tokens: int = 700  # câu trả lời RAG ngắn -> giới hạn thấp để phản hồi nhanh
    local_llm_timeout: float = 120.0
    anthropic_api_key: str = ""  # để trong backend/.env; rỗng -> SDK tự đọc biến môi trường ANTHROPIC_API_KEY
    anthropic_model: str = "claude-opus-5-5"
    # Model rẻ hơn cho các tác vụ phụ (reflection, trích xuất) -> kiểm soát chi phí
    anthropic_small_model: str = "claude-haiku-5-5"
    llm_effort: str = "medium"  # low | medium | high | xhigh | max
    # Server-side fallback khi model chính từ chối (refusal). Để rỗng để tắt.
    llm_fallbacks: str = "default"

    # --- RAG ---
    embedding_provider: str = "fastembed"  # fastembed | hash (hash: offline, chỉ để test)
    # e5 cần tiền tố "query: " / "passage: " -> xem embeddings.py. Đổi model = phải nạp lại toàn bộ.
    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_dim: int = 1024
    chunk_size: int = 1200
    chunk_overlap: int = 150
    ocr_lang: str = "vie+eng"

    # --- Dịch vụ OCR (ADR-005) ---
    ocr_engine: str = "tesseract"  # engine mặc định: tesseract | (sau này) unlimited
    # Đường dẫn tesseract.exe. Để rỗng = tự tìm trong PATH, rồi thư mục cài mặc định trên Windows.
    tesseract_cmd: str = ""
    # Khử nhiễu + nhị phân + xóa đường kẻ bảng trước khi đưa vào Tesseract (app/ocr/preprocess.py).
    ocr_preprocess: bool = True
    ocr_max_mb: float = 20.0  # dung lượng file upload tối đa
    ocr_max_pages: int = 10  # số trang xử lý tối đa mỗi request đồng bộ (job bất đồng bộ sẽ nới)
    ocr_max_pixels: int = 60_000_000  # chặn ảnh/trang khổng lồ (tránh hết RAM)
    ocr_render_dpi: int = 250  # độ phân giải render trang PDF scan (khớp ingest.py)
    ocr_max_concurrency: int = 1  # số lượt OCR chạy song song cho mỗi engine
    # Job bất đồng bộ (/api/ocr/jobs): giới hạn nới hơn request đồng bộ
    ocr_job_max_mb: float = 50.0
    ocr_job_max_pages: int = 100
    ocr_job_ttl_days: int = 7  # tự xóa job và kết quả sau số ngày này
    ocr_job_workers: int = 2  # số job xử lý cùng lúc (mỗi engine vẫn bị ocr_max_concurrency chặn)
    ocr_job_max_active_per_user: int = 3  # tối đa job đang chờ/đang chạy của một người
    ocr_job_queue_max: int = 20  # tối đa job đang chờ/đang chạy toàn hệ thống (file nằm trong RAM khi chờ)
    # Trích xuất (/api/ocr/extract): LLM theo LLM_PROVIDER (local = qwen3-4b, dữ liệu không rời máy)
    ocr_extract_max_tokens: int = 1500  # JSON một phiếu dài hơn câu trả lời RAG (700)
    ocr_extract_max_chars: int = 8000  # cắt văn bản OCR gửi cho LLM

    # --- Knowledge base (knowledge-mcp) ---
    kb_dir: str = "../data/knowledge"
    # /api/kb: bản gốc tài liệu upload (<sha256>.<đuôi>), cần cho reindex. Tương đối theo thư mục chạy.
    upload_dir: str = "../data/uploads"
    max_upload_mb: float = 25.0  # khớp MAX_FILE_BYTES của portal (files.ts)
    rag_candidates: int = 30  # số ứng viên mỗi nhánh (vector, keyword) trước khi gộp RRF
    rag_top_k: int = 8  # số chunk đưa vào context
    rag_llm_model: str = "claude-sonnet-5-5"  # model sinh câu trả lời RAG (cân bằng chất lượng/chi phí)
    rag_judge_model: str = "claude-haiku-5-5"  # LLM-judge trong eval
    kb_mcp_host: str = "0.0.0.0"
    kb_mcp_port: int = 8100
    # Bí mật dùng chung giữa LibreChat và knowledge-mcp. Header X-User-Email chỉ được tin
    # khi request mang đúng token này (chứng minh request đến từ LibreChat, không phải ai đó tự gọi).
    kb_mcp_token: str = ""

    # --- Agent ---
    agent_max_steps: int = 8
    tool_output_max_chars: int = 8000
    history_max_messages: int = 10
    enable_reflection: bool = True
    skills_dir: str = "skills"

    # --- Governance ---
    monthly_budget_usd_per_user: float = 20.0

    # --- MCP: JSON list các server để agent kết nối (MCP client) ---
    # Ví dụ: [{"name":"fs","command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","./data"]}]
    mcp_servers: str = ""
    mcp_service_role: str = "staff"  # quyền của MCP server nội bộ khi chạy độc lập

    # --- Tích hợp kênh ---
    teams_webhook_secret: str = ""  # base64 secret của Teams Outgoing Webhook
    teams_incoming_webhook_url: str = ""  # để đẩy kết quả chậm (>5s) về kênh
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
