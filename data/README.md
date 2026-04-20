# Data

Thư mục chứa dữ liệu seed cho hệ thống.

## Nội dung

| File/Thư mục | Mô tả |
|---|---|
| `jobs_full_all.csv` | ~9000 tin tuyển dụng từ VietnamWorks (seed tự động khi khởi động) |
| `pipeline/` | Scripts crawl và seed dữ liệu ban đầu |

## CSV Schema (`jobs_full_all.csv`)

Hệ thống backend tự động đọc file này khi khởi động lần đầu (nếu DB trống).

| Cột | Mô tả |
|---|---|
| `jobTitle` | Tên vị trí công việc |
| `jobDescription` | Mô tả công việc |
| `jobRequirement` | Yêu cầu công việc |
| `companyName` | Tên công ty |
| `jobUrl` | Link tin tuyển dụng |
| `prettySalary` | Mức lương hiển thị |
| `salaryMin` / `salaryMax` | Khoảng lương (số) |
| `yearsOfExperience` | Số năm kinh nghiệm yêu cầu |
| `jobLevel` | Cấp bậc (Fresher / Junior / Senior...) |
| `skills` | Kỹ năng yêu cầu (dấu phẩy) |

## Thêm dữ liệu mới

Để crawl thêm dữ liệu mới, xem hướng dẫn trong `pipeline/README.md`.
