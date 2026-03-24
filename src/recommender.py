"""
recommender.py
==============
Module lõi của hệ thống gợi ý việc làm.

Chức năng:
- Tính toán Cosine Similarity giữa tất cả các job descriptions
- Gợi ý các công việc tương tự dựa trên job title được chọn
"""

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import spmatrix


def compute_similarity(matrix: spmatrix) -> np.ndarray:
    """
    Tính toán Cosine Similarity matrix giữa tất cả các documents.

    Cosine Similarity đo lường góc giữa hai vector TF-IDF,
    cho giá trị từ 0 (hoàn toàn khác nhau) đến 1 (giống hệt nhau).

    Parameters
    ----------
    matrix : spmatrix
        TF-IDF matrix đầu vào (sparse matrix) với shape (n_docs, n_features).

    Returns
    -------
    np.ndarray
        Ma trận Cosine Similarity có shape (n_docs, n_docs).
        cosine_sim[i][j] = độ tương đồng giữa document i và document j.

    Example
    -------
    >>> cosine_sim = compute_similarity(tfidf_matrix)
    >>> print(cosine_sim.shape)  # (n_jobs, n_jobs)
    """
    cosine_sim = cosine_similarity(matrix, matrix)
    print(f"[Recommender] Cosine similarity matrix shape: {cosine_sim.shape}")
    return cosine_sim


def recommend_jobs(
    job_title: str,
    df: pd.DataFrame,
    cosine_sim: np.ndarray,
    top_n: int = 5
) -> pd.DataFrame:
    """
    Gợi ý các công việc tương tự dựa trên một job title được chọn.

    Logic:
    1. Tìm index của job_title trong DataFrame
    2. Lấy hàng similarity scores tương ứng
    3. Sắp xếp theo độ tương đồng giảm dần
    4. Loại bỏ chính nó (similarity = 1.0)
    5. Trả về top_n jobs tương đồng nhất

    Parameters
    ----------
    job_title : str
        Tên công việc cần tìm gợi ý tương đồng.
    df : pd.DataFrame
        DataFrame chứa cột 'position_title' và 'job_description'.
    cosine_sim : np.ndarray
        Ma trận Cosine Similarity từ hàm compute_similarity().
    top_n : int, optional
        Số lượng gợi ý muốn trả về (mặc định: 5).

    Returns
    -------
    pd.DataFrame
        DataFrame chứa top_n công việc tương tự nhất với các cột:
        - 'position_title': Tên công việc
        - 'job_description': Mô tả công việc
        - 'similarity_score': Điểm tương đồng (0.0 - 1.0)
        Trả về DataFrame rỗng nếu không tìm thấy job_title.

    Example
    -------
    >>> recommendations = recommend_jobs("Data Scientist", df, cosine_sim, top_n=5)
    >>> print(recommendations[['position_title', 'similarity_score']])
    """
    # Lấy danh sách tất cả các job titles (lowercase để so sánh dễ dàng)
    job_titles = df['position_title'].str.lower().tolist()
    query_lower = job_title.strip().lower()

    # Tìm index của job title được chọn
    if query_lower not in job_titles:
        # Thử tìm kiếm gần đúng (partial match)
        matches = [i for i, t in enumerate(job_titles) if query_lower in t]
        if not matches:
            print(f"[Recommender] Không tìm thấy job title: '{job_title}'")
            return pd.DataFrame()
        idx = matches[0]
    else:
        idx = job_titles.index(query_lower)

    # Lấy vector similarity scores của job này với tất cả các job khác
    sim_scores = list(enumerate(cosine_sim[idx]))

    # Sắp xếp theo similarity score giảm dần, bỏ qua chính nó (idx)
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = [(i, score) for i, score in sim_scores if i != idx]

    # Lấy top_n kết quả
    top_results = sim_scores[:top_n]
    top_indices = [i for i, _ in top_results]
    top_scores = [score for _, score in top_results]

    # Xây dựng DataFrame kết quả
    result_df = df.iloc[top_indices][['position_title', 'job_description']].copy()
    result_df['similarity_score'] = [round(s, 4) for s in top_scores]
    result_df.reset_index(drop=True, inplace=True)

    return result_df
