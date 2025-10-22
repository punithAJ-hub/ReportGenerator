# excel_parser.py
import io
import pandas as pd

REQUIRED_COLUMNS = ["MSE ID", "Title"]

def parse_excel(file_bytes: bytes) -> pd.DataFrame:
    """Read Excel bytes and return cleaned DataFrame with required columns."""
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    except Exception:
        df = pd.read_excel(io.BytesIO(file_bytes))

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in Excel: {missing}")

    df = df[REQUIRED_COLUMNS].copy().dropna(subset=REQUIRED_COLUMNS)
    df["MSE ID"] = df["MSE ID"].astype(str).str.strip()
    df["Title"]  = df["Title"].astype(str).str.strip()
    df = df.drop_duplicates(subset=["MSE ID"]).reset_index(drop=True)
    return df

def build_id_title_map(df: pd.DataFrame) -> dict:
    """Return {MSE ID: Title} mapping."""
    return dict(zip(df["MSE ID"].tolist(), df["Title"].tolist()))
