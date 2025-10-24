# excel_parser.py
import io
import pandas as pd

REQUIRED_COLUMNS = ["MSE ID", "Title"]
OPTIONAL_CLIENT_COLUMNS = ["Client", "Client Name", "CLIENT", "CLIENT NAME"]

def parse_excel(file_bytes: bytes) -> pd.DataFrame:
    """
    Reads an Excel file (as bytes) and returns a cleaned DataFrame with required
    columns: 'MSE ID' and 'Title'. If a client column exists (any of OPTIONAL_CLIENT_COLUMNS),
    a unified 'Client' column is created.
    """
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    except Exception:
        df = pd.read_excel(io.BytesIO(file_bytes))

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in Excel: {missing}")

    # Keep at least the required columns, and pull the first matching client column if present
    client_col = None
    for c in OPTIONAL_CLIENT_COLUMNS:
        if c in df.columns:
            client_col = c
            break

    cols = REQUIRED_COLUMNS.copy()
    if client_col:
        cols.append(client_col)

    df = df[cols].copy()
    df = df.dropna(subset=["MSE ID", "Title"])

    # Normalize
    df["MSE ID"] = df["MSE ID"].astype(str).str.strip()
    df["Title"] = df["Title"].astype(str).str.strip()
    if client_col:
        df["Client"] = df[client_col].astype(str).fillna("").str.strip()
    else:
        df["Client"] = ""

    # Remove duplicates by MSE ID
    df = df.drop_duplicates(subset=["MSE ID"], keep="first").reset_index(drop=True)
    return df

def build_maps(df: pd.DataFrame) -> tuple[dict, dict]:
    """
    Returns:
      title_map: { MSE ID -> Title }
      client_map: { MSE ID -> Client }
    """
    title_map = dict(zip(df["MSE ID"].tolist(), df["Title"].tolist()))
    client_map = dict(zip(df["MSE ID"].tolist(), df["Client"].tolist()))
    return title_map, client_map
