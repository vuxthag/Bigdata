# Data Directory

Đặt file dataset tại đây với tên: `training_data.csv`

## Định dạng file CSV bắt buộc

File phải có **ít nhất 2 cột** sau:

| Cột | Kiểu dữ liệu | Mô tả |
|-----|-------------|-------|
| `position_title` | string | Tên/chức danh vị trí công việc |
| `job_description` | string | Mô tả chi tiết công việc, yêu cầu kỹ năng |

## Ví dụ

```csv
position_title,job_description
Data Scientist,"We are looking for a Data Scientist with 3+ years experience in Python, ML..."
Software Engineer,"Backend developer with Node.js and PostgreSQL experience..."
```

## Nguồn dataset gợi ý

- [Kaggle: Job Recommendation Dataset](https://www.kaggle.com/datasets)
- [Kaggle: Indeed Job Postings](https://www.kaggle.com/datasets/promptcloud/jobs-on-naukricom)
