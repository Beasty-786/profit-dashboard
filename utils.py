import re
import pandas as pd


def detect_columns(df: pd.DataFrame):
    cols = {c.lower(): c for c in df.columns}

    def find(keys):
        for k in keys:
            for low_name, original in cols.items():
                if k in low_name:
                    return original
        return None

    return {
        "pack": find(["product", "item", "pack"]),
        "price": find(["amount", "price", "total"]),
        "status": find(["status"]),
        "date": find(["date", "created"]),
        "user": find(["email", "phone", "customer"]),
    }


def normalize_pack(text):
    if pd.isna(text):
        return ""
    text = str(text).lower().replace("×", "x")
    return re.sub(r"[^a-z0-9+]", "", text)


def extract_value(text):
    nums = re.findall(r"\d+", str(text))
    return int(nums[0]) if nums else None