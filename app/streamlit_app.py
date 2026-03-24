"""
streamlit_app.py
================
Web demo cho hệ thống gợi ý việc làm dựa trên TF-IDF & Cosine Similarity.

Cách chạy:
    streamlit run app/streamlit_app.py

Yêu cầu:
    - File dataset tại: data/training_data.csv
    - Các module src/ đã được cài đặt
"""

import streamlit as st
import sys
import os

# ─── Đảm bảo Python có thể tìm thấy thư mục src/ ──────────────────────────────
# Thêm thư mục gốc của project vào sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from src.data_loader import load_data
from src.preprocessing import clean_text
from src.vectorizer import build_vectorizer
from src.recommender import compute_similarity, recommend_jobs

# ─── Cấu hình trang ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hệ thống gợi ý việc làm",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CSS tùy chỉnh (giao diện đẹp hơn) ────────────────────────────────────────
st.markdown("""
<style>
    /* Header gradient */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    .main-header h1 { font-size: 2.4rem; margin-bottom: 0.3rem; }
    .main-header p  { font-size: 1.1rem; opacity: 0.9; }

    /* Card cho kết quả */
    .job-card {
        background: #f8f9ff;
        border-left: 5px solid #667eea;
        border-radius: 8px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(102,126,234,0.1);
    }
    .job-card h4 { color: #4a4a8a; margin-bottom: 0.3rem; }
    .similarity-badge {
        display: inline-block;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        margin-bottom: 0.5rem;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] > div {
        background: #1e1e2e;
        color: white;
    }
    .stSelectbox label, .stSlider label, .stTextArea label {
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ─── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>💼 Hệ thống gợi ý việc làm</h1>
    <p>Khám phá việc làm phù hợp dựa trên TF-IDF và Cosine Similarity</p>
</div>
""", unsafe_allow_html=True)


# ─── Sidebar: Cài đặt & thông tin ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Cài đặt")

    # Đường dẫn dataset
    data_path = st.text_input(
        "📂 Đường dẫn dữ liệu (CSV)",
        value="data/training_data.csv",
        help="Nhập đường dẫn tới file CSV chứa dữ liệu việc làm"
    )

    # Số lượng gợi ý
    top_n = st.slider(
        "🎯 Số lượng gợi ý",
        min_value=3, max_value=15, value=5, step=1,
        help="Số lượng công việc tương tự muốn hiển thị"
    )

    st.markdown("---")
    st.markdown("""
    ### 📌 Về hệ thống
    Hệ thống sử dụng:
    - **TF-IDF** để vector hóa mô tả công việc
    - **Cosine Similarity** để đo độ tương đồng
    - **Tiền xử lý văn bản** để làm sạch dữ liệu
    """)

    st.markdown("---")
    st.markdown("👨‍💻 Xây dựng bằng Streamlit và scikit-learn")


# ─── Cache: Load & xử lý dữ liệu (chỉ chạy một lần) ──────────────────────────
@st.cache_data(show_spinner=False)
def load_and_process(path: str):
    """Pipeline: Load → Làm sạch → TF-IDF → Cosine similarity."""
    # 1. Load data
    df = load_data(path)

    # 2. Preprocess text
    df = df.copy()
    df["cleaned_description"] = df["job_description"].apply(clean_text)

    # 3. Tạo TF-IDF matrix
    vectorizer = build_vectorizer()
    tfidf_matrix = vectorizer.fit_transform(df["cleaned_description"])

    # 4. Tính cosine similarity
    cosine_sim = compute_similarity(tfidf_matrix)

    return df, vectorizer, tfidf_matrix, cosine_sim


# ─── Load dữ liệu ──────────────────────────────────────────────────────────────
try:
    with st.spinner("⏳ Đang tải và xử lý dữ liệu..."):
        df, vectorizer, tfidf_matrix, cosine_sim = load_and_process(data_path)

    # Thông báo thành công
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📋 Tổng số việc làm", f"{len(df):,}")
    with col2:
        unique_titles = df['position_title'].nunique()
        st.metric("🏷️ Số chức danh độc lập", f"{unique_titles:,}")
    with col3:
        st.metric("📊 Số đặc trưng TF-IDF", f"{tfidf_matrix.shape[1]:,}")

    st.markdown("---")

    # ─── Tabs: 2 chế độ gợi ý ─────────────────────────────────────────────────
    tab1, tab3 = st.tabs([
        "🔍 Gợi ý theo chức danh",
        "📊 Khám phá dữ liệu"
    ])

    # ── Tab 1: Gợi ý theo Job Title ───────────────────────────────────────────
    with tab1:
        st.markdown("### 🎯 Chọn chức danh để tìm việc tương tự")

        # Dropdown chọn job title
        job_titles_list = sorted(df['position_title'].unique().tolist())
        selected_job = st.selectbox(
            "💼 Chọn một chức danh",
            options=job_titles_list,
            index=0,
            help="Chọn một chức danh công việc để hệ thống gợi ý các việc làm tương tự"
        )

        # Hiển thị thông tin job được chọn
        if selected_job:
            with st.expander("📄 Xem mô tả công việc đã chọn"):
                job_info = df[df['position_title'] == selected_job].iloc[0]
                st.markdown(f"**Chức danh:** {job_info['position_title']}")
                st.markdown(f"**Mô tả:**\n\n{job_info['job_description'][:500]}...")

        st.markdown("")

        # Button gợi ý
        if st.button("🚀 Tìm việc tương tự", type="primary", key="btn_title"):
            with st.spinner("🔄 Đang tính toán độ tương đồng..."):
                recommendations = recommend_jobs(
                    job_title=selected_job,
                    df=df,
                    cosine_sim=cosine_sim,
                    top_n=top_n
                )

            if recommendations.empty:
                st.warning("⚠️ Không tìm thấy gợi ý phù hợp.")
            else:
                st.success(f"✅ Tìm thấy **{len(recommendations)}** công việc tương tự!")
                st.markdown("---")

                # Hiển thị kết quả dạng cards
                for rank, (_, row) in enumerate(recommendations.iterrows(), start=1):
                    similarity_pct = f"{row['similarity_score'] * 100:.1f}%"
                    description_preview = row['job_description'][:200].strip()

                    st.markdown(f"""
                    <div class="job-card">
                        <h4>#{rank} &nbsp; {row['position_title']}</h4>
                        <span class="similarity-badge">🎯 Độ tương đồng: {similarity_pct}</span>
                        <p style="color: #555; margin-top: 0.5rem;">
                            {description_preview}...
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                # Tải kết quả dưới dạng CSV
                st.download_button(
                    label="⬇️ Tải kết quả (CSV)",
                    data=recommendations.to_csv(index=False).encode('utf-8'),
                    file_name=f"recommendations_{selected_job.replace(' ', '_')}.csv",
                    mime="text/csv"
                )

    # ── Tab 3: EDA – Khám phá dữ liệu ────────────────────────────────────────
    with tab3:
        st.markdown("### 📊 Khám phá dữ liệu (EDA)")

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("#### 📋 Mẫu dữ liệu (10 dòng đầu)")
            st.dataframe(df.head(10), use_container_width=True)

        with col_right:
            st.markdown("#### 🏆 Top 20 chức danh phổ biến nhất")
            top_titles = (
                df['position_title']
                .value_counts()
                .head(20)
                .reset_index()
                .rename(columns={'position_title': 'Chức danh', 'count': 'Số lượng'})
            )
            st.dataframe(top_titles, use_container_width=True)

        st.markdown("#### 📝 Thống kê độ dài mô tả công việc")
        df_stats = df.copy()
        df_stats['desc_length'] = df_stats['job_description'].str.len()
        st.write(df_stats['desc_length'].describe().rename("Thống kê số ký tự"))

except FileNotFoundError as e:
    st.error(f"❌ Không tìm thấy file dữ liệu!")
    st.markdown(f"**Chi tiết lỗi:** `{e}`")
    st.info("""
    💡 **Hướng dẫn:**
    1. Đặt file `training_data.csv` vào thư mục `data/`
    2. Hoặc thay đổi đường dẫn trong sidebar bên trái
    3. File CSV phải có hai cột: `position_title` và `job_description`
    """)

except ValueError as e:
    st.error(f"❌ Lỗi định dạng dữ liệu!")
    st.markdown(f"**Chi tiết lỗi:** `{e}`")

except Exception as e:
    st.error(f"❌ Đã xảy ra lỗi không mong đợi: `{e}`")
    st.exception(e)
