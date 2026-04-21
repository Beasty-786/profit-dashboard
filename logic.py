import pandas as pd
from utils import normalize_pack, extract_value


def resolve_pricing_cost_column(pricing_df):
    preferred = [
        "Raw Cost",
        "Actual Price",
        "Cost",
        "Cost(SOC)",
        "Cost SOC",
    ]

    for col in preferred:
        if col in pricing_df.columns:
            return col

    for col in pricing_df.columns:
        if "cost" in col.lower():
            return col

    raise ValueError("Could not find a cost column in the pricing sheet.")


def resolve_pricing_pack_column(pricing_df):
    if "Pack" in pricing_df.columns:
        return "Pack"

    candidates = [
        c for c in pricing_df.columns
        if "pack" in c.lower() or "product" in c.lower() or "item" in c.lower()
    ]
    if candidates:
        return candidates[0]

    raise ValueError("Could not find a Pack column in the pricing sheet.")


def build_lookups(pricing_df, pack_col, cost_col):
    pricing = pricing_df.copy()

    pricing["Pack_norm"] = pricing[pack_col].apply(normalize_pack)
    pricing["Actual Price"] = pd.to_numeric(pricing[cost_col], errors="coerce")

    if "Value" in pricing.columns:
        pricing["Value_num"] = pd.to_numeric(pricing["Value"], errors="coerce")
    else:
        pricing["Value_num"] = pd.NA

    pricing = pricing.dropna(subset=["Actual Price"])

    exact_lookup = (
        pricing.drop_duplicates(subset="Pack_norm", keep="first")
        .set_index("Pack_norm")["Actual Price"]
        .to_dict()
    )

    value_lookup = (
        pricing.dropna(subset=["Value_num"])
        .drop_duplicates(subset="Value_num", keep="first")
        .set_index("Value_num")["Actual Price"]
        .to_dict()
    )

    return exact_lookup, value_lookup


def process_data(orders, pricing, cols, start_date, end_date, search):
    if not cols.get("pack"):
        raise ValueError("Pack column not detected in orders file.")
    if not cols.get("price"):
        raise ValueError("Price column not detected in orders file.")

    df = orders.copy()
    pricing_df = pricing.copy()

    # Filter completed only
    if cols.get("status") and cols["status"] in df.columns:
        df = df[df[cols["status"]].astype(str).str.lower() == "completed"]

    # Filter date range
    if cols.get("date") and cols["date"] in df.columns:
        df[cols["date"]] = pd.to_datetime(df[cols["date"]], errors="coerce")
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        df = df[
            (df[cols["date"]] >= start_dt) &
            (df[cols["date"]] <= end_dt)
        ]

    # Search filter
    if search and cols.get("pack") and cols["pack"] in df.columns:
        df = df[df[cols["pack"]].astype(str).str.contains(search, case=False, na=False)]

    # Standardize order columns
    df = df.rename(columns={
        cols["pack"]: "Pack",
        cols["price"]: "Selling Price",
    })

    # Standardize pricing columns
    pricing_pack_col = resolve_pricing_pack_column(pricing_df)
    pricing_cost_col = resolve_pricing_cost_column(pricing_df)

    if pricing_pack_col != "Pack":
        pricing_df = pricing_df.rename(columns={pricing_pack_col: "Pack"})

    # Build lookups from pricing
    exact_lookup, value_lookup = build_lookups(pricing_df, "Pack", pricing_cost_col)

    # Normalize order packs
    df["Pack_norm"] = df["Pack"].apply(normalize_pack)

    # Fix the one naming mismatch you already showed
    alias_map = {
        normalize_pack("3x Weekly Passes"): normalize_pack("3× Weekly Pass"),
    }
    df["Pack_norm"] = df["Pack_norm"].replace(alias_map)

    # Extract numeric value from the order pack
    df["Value_num"] = df["Pack"].apply(extract_value)

    # Selling price
    df["Selling Price"] = pd.to_numeric(df["Selling Price"], errors="coerce")

    # Match in two steps
    df["Actual Price"] = df["Pack_norm"].map(exact_lookup)

    missing_mask = df["Actual Price"].isna() & df["Value_num"].notna()
    if missing_mask.any():
        df.loc[missing_mask, "Actual Price"] = df.loc[missing_mask, "Value_num"].map(value_lookup)

    # Mark match status
    df["Match Status"] = "Matched"
    df.loc[df["Actual Price"].isna(), "Match Status"] = "Missing"

    # Profit
    df["Profit"] = df["Selling Price"] - df["Actual Price"]

    # Cleanup
    df = df.drop(columns=["Pack_norm", "Value_num"], errors="ignore")

    return df


def get_top_users(df, user_col):
    if not user_col or user_col not in df.columns:
        return pd.Series(dtype="float64")

    return (
        df.groupby(user_col, dropna=False)["Profit"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )


def get_product_profit(df):
    if "Pack" not in df.columns:
        return pd.Series(dtype="float64")

    return (
        df.groupby("Pack", dropna=False)["Profit"]
        .sum()
        .sort_values(ascending=False)
    )


def profit_over_time(df, date_col):
    if not date_col or date_col not in df.columns:
        return pd.DataFrame(columns=["Date", "Profit"])

    temp = df.copy()
    temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
    temp = temp.dropna(subset=[date_col])

    chart = temp.groupby(temp[date_col].dt.date, as_index=False)["Profit"].sum()
    chart.columns = ["Date", "Profit"]
    return chart