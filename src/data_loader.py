"""
data_loader.py
==============
Module responsible for loading and validating the job dataset.

Chức năng:
- Load dataset từ file CSV
- Kiểm tra và lọc các cột cần thiết
- Trả về DataFrame đã được làm sạch sơ bộ
"""

from __future__ import annotations

import pandas as pd


def load_data(path: str) -> pd.DataFrame:
    """
    Load job dataset từ file CSV và chỉ giữ lại các cột quan trọng.

    Parameters
    ----------
    path : str
        Đường dẫn tới file CSV chứa dữ liệu việc làm.

    Returns
    -------
    pd.DataFrame
        DataFrame chứa các cột: 'position_title', 'job_description'.
        Các hàng có giá trị null đã được loại bỏ.

    Raises
    ------
    FileNotFoundError
        Nếu file CSV không tồn tại tại đường dẫn đã cho.
    ValueError
        Nếu DataFrame không có đủ các cột bắt buộc.

    Example
    -------
    >>> df = load_data('data/training_data.csv')
    >>> print(df.head())
    """
    # Đọc file CSV
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        raise FileNotFoundError(f"[DataLoader] File not found: '{path}'")

    # Các cột bắt buộc cần có trong dataset
    required_columns = ['position_title', 'job_description']

    # Kiểm tra xem dataset có đủ các cột cần thiết không
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(
            f"[DataLoader] Dataset thiếu các cột: {missing}. "
            f"Các cột hiện có: {list(df.columns)}"
        )

    # Chỉ giữ lại hai cột cần thiết
    df = df[required_columns].copy()

    # Loại bỏ các hàng có giá trị null
    before = len(df)
    df.dropna(subset=required_columns, inplace=True)
    after = len(df)

    if before != after:
        print(f"[DataLoader] Dropped {before - after} rows with nulls.")

    # Reset lại index sau khi lọc
    df.reset_index(drop=True, inplace=True)

    print(f"[DataLoader] Loaded {len(df)} records from '{path}'.")
    return df
