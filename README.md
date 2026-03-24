# 💼 Job Recommendation System

> **Hệ thống gợi ý việc làm dựa trên độ tương đồng nội dung công việc sử dụng TF-IDF và Cosine Similarity.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-FF4B4B?logo=streamlit)](https://streamlit.io)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3%2B-orange?logo=scikit-learn)](https://scikit-learn.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📌 Project Overview

Dự án này xây dựng một **Content-Based Job Recommendation System** sử dụng kỹ thuật **Natural Language Processing (NLP)**. Hệ thống phân tích mô tả công việc (job descriptions), học được các biểu diễn vector thông qua **TF-IDF**, và tính toán **Cosine Similarity** để gợi ý những vị trí công việc có nội dung tương đồng nhất.

**Web demo** được xây dựng bằng **Streamlit** với giao diện thân thiện, hỗ trợ cả tìm kiếm theo job title lẫn theo mô tả kỹ năng tùy ý.

---

## ❓ Problem Statement

Trong thị trường việc làm hiện đại, người tìm việc phải duyệt qua hàng nghìn vị trí tuyển dụng để tìm ra cơ hội phù hợp. Vấn đề cần giải quyết:

- **Thông tin quá tải**: Quá nhiều job listings, khó lọc thủ công
- **Mô tả công việc không chuẩn**: Các vị trí giống nhau có thể được diễn đạt rất khác nhau
- **Thiếu gợi ý cá nhân hóa**: Cần hệ thống hiểu được nội dung và đưa ra gợi ý thông minh

**Giải pháp**: Sử dụng NLP để tự động phân tích nội dung mô tả công việc và gợi ý những vị trí tương đồng nhất.

---

## 📂 Dataset Description

| Cột | Mô tả |
|-----|-------|
| `position_title` | Chức danh công việc (e.g., "Data Scientist", "Software Engineer") |
| `job_description` | Mô tả chi tiết yêu cầu, trách nhiệm, kỹ năng của vị trí |

**Nguồn gợi ý**: Dataset có thể thu thập từ:
- [Kaggle — Job Postings Dataset](https://www.kaggle.com)
- LinkedIn API / Indeed scraping
- Sample data từ các nguồn tuyển dụng công khai

---

## 🧠 Methodology

```
Raw Text
    │
    ▼
┌─────────────────────────────┐
│   Text Preprocessing        │  lowercase → remove URLs → remove special chars
│   (preprocessing.py)        │  → normalize whitespace
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   TF-IDF Vectorization      │  max_features=5000, stop_words='english'
│   (vectorizer.py)           │  ngram_range=(1,2), sublinear_tf=True
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   Cosine Similarity Matrix  │  (n_jobs × n_jobs) similarity scores
│   (recommender.py)          │  score ∈ [0, 1]
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   Top-N Recommendations     │  Sắp xếp giảm dần theo similarity score
│                             │  Trả về top N jobs tương đồng nhất
└─────────────────────────────┘
```

---

## 🔬 NLP Pipeline

### 1. Text Preprocessing (`src/preprocessing.py`)

```python
from src.preprocessing import clean_text

raw = "Apply at https://jobs.com! Python & ML skills required. Salary: $80k"
cleaned = clean_text(raw)
# Output: "apply at  python  ml skills required salary k"
```

**Các bước xử lý:**
| Bước | Phép biến đổi | Ví dụ |
|------|--------------|-------|
| Lowercase | `text.lower()` | `"Python"` → `"python"` |
| Remove URLs | `re.sub(r'https?://...')` | `"https://jobs.com"` → `""` |
| Remove emails | `re.sub(r'\S+@\S+')` | `"hr@company.com"` → `""` |
| Remove special chars | `re.sub(r'[^a-z\s]')` | `"C++ & Java!"` → `"c  java"` |
| Normalize spaces | `re.sub(r'\s+', ' ')` | `"  data   science "` → `"data science"` |

### 2. TF-IDF Vectorization (`src/vectorizer.py`)

$$TF\text{-}IDF(t, d) = TF(t, d) \times \log\frac{N}{DF(t)}$$

Tham số cấu hình:
```python
TfidfVectorizer(
    max_features=5000,    # Top 5000 terms phổ biến nhất
    stop_words='english', # Loại bỏ common words (the, is, at...)
    ngram_range=(1, 2),   # Sử dụng unigrams và bigrams
    sublinear_tf=True,    # Log normalization: 1 + log(tf)
    min_df=2              # Bỏ từ xuất hiện < 2 lần
)
```

### 3. Cosine Similarity (`src/recommender.py`)

$$\text{Cosine Similarity}(A, B) = \frac{A \cdot B}{\|A\| \|B\|}$$

- Giá trị từ **0** (hoàn toàn khác nhau) đến **1** (giống hệt nhau)
- Độc lập với độ dài văn bản → phù hợp cho job descriptions có độ dài khác nhau

---

## 📸 Example Results

**Demo:** Tìm công việc tương tự "Data Scientist"

| Rank | Job Title | Similarity Score |
|------|-----------|-----------------|
| #1 | Senior Data Scientist | 0.8923 (89.2%) |
| #2 | Machine Learning Engineer | 0.8147 (81.5%) |
| #3 | Data Analyst | 0.7634 (76.3%) |
| #4 | AI Research Scientist | 0.7421 (74.2%) |
| #5 | Business Intelligence Analyst | 0.6893 (68.9%) |

---

## 🛠 Technologies Used

| Category | Technology | Version |
|----------|-----------|---------|
| **Language** | Python | 3.10+ |
| **Data Processing** | pandas, numpy | 2.0+, 1.24+ |
| **NLP / ML** | scikit-learn | 1.3+ |
| **Visualization** | matplotlib, seaborn, wordcloud | Latest |
| **Web Framework** | Streamlit | 1.28+ |
| **Notebook** | JupyterLab | 4.0+ |

---

## 🚀 Cài Đặt & Chạy

### Yêu cầu
- Python 3.10 trở lên
- pip hoặc conda

### Cài đặt

```bash
# Clone repository
git clone https://github.com/your-username/cv-job-recommendation-system.git
cd cv-job-recommendation-system

# Tạo virtual environment (khuyến nghị)
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/Mac

# Cài đặt dependencies
pip install -r requirements.txt
```

### Chuẩn bị dữ liệu

Đặt file CSV vào thư mục `data/`:
```
data/
└── training_data.csv   ← File gồm 2 cột: position_title, job_description
```

### Chạy Web Demo

```bash
streamlit run app/streamlit_app.py
```

Truy cập: `http://localhost:8501`

### Chạy Notebook (EDA)

```bash
cd notebooks
jupyter lab
```

---

## 📁 Cấu Trúc Project

```
cv-job-recommendation-system/
│
├── data/
│   └── training_data.csv          # Dataset việc làm
│
├── notebooks/
│   └── job_recommendation_exploration.ipynb   # EDA & thử nghiệm
│
├── src/                           # Business logic modules
│   ├── __init__.py
│   ├── data_loader.py             # Load và validate dataset
│   ├── preprocessing.py           # Text cleaning pipeline
│   ├── vectorizer.py              # TF-IDF vectorization
│   └── recommender.py             # Cosine similarity & recommendations
│
├── app/
│   └── streamlit_app.py           # Web demo interface
│
├── requirements.txt               # Python dependencies
├── .gitignore
└── README.md
```

---

## 🔮 Future Improvements

### 1. 📄 Upload CV để gợi ý việc làm
```python
# Tích hợp PyPDF2 / python-docx để parse CV
# Trích xuất kỹ năng và kinh nghiệm tự động
# Recommend jobs based on CV content
```

### 2. 🤖 Semantic Similarity với BERT / Sentence-Transformers
```python
# Sử dụng sentence-transformers thay thế TF-IDF
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(job_descriptions)
# → Hiểu ngữ nghĩa sâu hơn, không chỉ từ vựng
```

### 3. 🎨 Cải thiện giao diện Streamlit
- Thêm filter theo ngành nghề, địa điểm, mức lương
- Pagination cho kết quả tìm kiếm
- Dark mode / Light mode toggle
- Export PDF report

### 4. ⚡ Xây dựng API với FastAPI
```python
# app/api.py
from fastapi import FastAPI
app = FastAPI()

@app.post("/recommend")
def recommend(job_title: str, top_n: int = 5):
    return recommend_jobs(job_title, df, cosine_sim, top_n)
```

### 5. 📊 Advanced Analytics
- Clustering các vị trí công việc với K-Means / DBSCAN
- Topic modeling với LDA để phân tích chủ đề
- Interactive visualizations với Plotly

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 👨‍💻 Author

**Your Name**
- GitHub: [@your-username](https://github.com/your-username)
- LinkedIn: [Your LinkedIn](https://linkedin.com)
- Portfolio: [your-portfolio.com](https://your-portfolio.com)

---

*⭐ Nếu project này hữu ích, đừng quên star repository!*
