# Data Pipeline

Scripts thu thập và seed dữ liệu việc làm từ VietnamWorks.

> **Lưu ý:** Thông thường không cần chạy lại các scripts này. Dữ liệu đã có sẵn trong `data/jobs_full_all.csv` và được backend tự động seed vào DB khi khởi động lần đầu.

## Files

| File | Mô tả |
|---|---|
| `crawl_jobs.py` | Crawl VietnamWorks → xuất CSV |
| `seed_db.py` | Import CSV vào PostgreSQL + tạo embeddings |
| `skills_config.py` | Danh sách kỹ năng để trích xuất khi crawl |

## Cài đặt

```bash
pip install requests beautifulsoup4 pandas lxml psycopg2-binary sentence-transformers python-dotenv
```

## Sử dụng

### 1. Crawl dữ liệu mới

```bash
# Chạy từ thư mục gốc project
python data/pipeline/crawl_jobs.py --limit 100   # Test 100 jobs
python data/pipeline/crawl_jobs.py               # Crawl toàn bộ
```

CLI options:

| Flag | Mặc định | Mô tả |
|---|---|---|
| `--limit` | tất cả | Giới hạn số job |
| `--workers` | 3 | Số luồng song song |
| `--output` | `data/jobs_full_all.csv` | File output |

### 2. Seed vào Database

```bash
# Dry-run kiểm tra trước
python data/pipeline/seed_db.py --dry-run --limit 20

# Seed đầy đủ
python data/pipeline/seed_db.py
```

> **Thay thế:** Dùng admin API endpoint để tạo embeddings cho jobs đã có trong DB:
> ```
> POST /api/v1/jobs/admin/regenerate-embeddings
> ```

## Cách VietnamWorks parsing hoạt động

VietnamWorks dùng Next.js RSC streaming — dữ liệu không nằm trong HTML thông thường mà embedded trong JavaScript:

```html
<script>self.__next_f.push([1, "{\"jobTitle\":\"...\"}"])</script>
```

Parser sẽ:
1. Tìm tất cả `self.__next_f.push(...)` bằng regex
2. Decode JSON payload
3. Deep-merge toàn bộ key-value
4. Trích xuất `jobTitle`, `jobDescription`, `jobRequirement`, `skills`...
5. Fallback sang CSS selector nếu RSC thất bại
