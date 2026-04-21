import streamlit as st
import pandas as pd
import plotly.express as px

from utils import detect_columns
from logic import process_data, get_top_users, get_product_profit, profit_over_time

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Profit Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------- LOAD CSS ----------------
def load_css():
    try:
        with open("styles.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

load_css()

# ---------------- HEADER ----------------
st.title("💼 Profit Dashboard")
st.markdown("### Analytics Overview")
st.caption("Only matched products are included in profit. Missing pricing is shown separately.")

# ---------------- SIDEBAR ----------------
st.sidebar.header("📂 Upload Data")

orders_file = st.sidebar.file_uploader("Orders CSV", type=["csv"])
pricing_file = st.sidebar.file_uploader("Pricing CSV", type=["csv"])

st.sidebar.markdown("---")
st.sidebar.subheader("Filters")

search = st.sidebar.text_input("🔍 Search Pack")
start_date = st.sidebar.date_input("📅 Start Date")
end_date = st.sidebar.date_input("📅 End Date")
show_raw = st.sidebar.checkbox("Show Raw Data", value=False)

# ---------------- HELPERS FOR INTERACTIVE TABLES ----------------
def show_interactive_table(df, key, label, height=280):
    st.markdown(f"#### {label}")
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key=key,
        height=height,
    )
    selected_rows = []
    try:
        selected_rows = list(event.selection.rows)
    except Exception:
        selected_rows = []
    return selected_rows


# ---------------- MAIN ----------------
if orders_file and pricing_file:
    try:
        orders = pd.read_csv(orders_file)
        pricing = pd.read_csv(pricing_file)

        cols = detect_columns(orders)
        merged = process_data(
            orders=orders,
            pricing=pricing,
            cols=cols,
            start_date=start_date,
            end_date=end_date,
            search=search,
        )

        valid_df = merged[merged["Match Status"] == "Matched"].copy()
        missing_df = merged[merged["Match Status"] == "Missing"].copy()

        total_profit = valid_df["Profit"].sum()
        total_orders = len(valid_df)

        # ---------------- METRICS ----------------
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 Profit", f"₹ {total_profit:,.0f}")
        col2.metric("📦 Orders", total_orders)
        col3.metric("⚠️ Missing", len(missing_df))
        col4.metric("📄 Total Rows", len(merged))

        st.markdown("---")

        # ---------------- TOP CUSTOMERS ----------------
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.subheader("🏆 Top Customers")

        if cols.get("user") and cols["user"] in valid_df.columns:
            top_users = get_top_users(valid_df, cols["user"]).reset_index()
            top_users.columns = ["Customer", "Profit"]

            selected_customer_rows = show_interactive_table(
                top_users,
                key="top_customers_table",
                label="Top Customers Table",
                height=280,
            )

            if selected_customer_rows:
                selected_customers = top_users.iloc[selected_customer_rows]["Customer"].tolist()
                detail_df = valid_df[valid_df[cols["user"]].isin(selected_customers)]
                st.markdown("**Selected customer orders**")
                st.dataframe(
                    detail_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Selling Price": st.column_config.NumberColumn(format="₹ %.2f"),
                        "Actual Price": st.column_config.NumberColumn(format="₹ %.2f"),
                        "Profit": st.column_config.NumberColumn(format="₹ %.2f"),
                    },
                )
        else:
            st.info("No customer column found")

        st.markdown('</div>', unsafe_allow_html=True)

        # ---------------- PRODUCT PROFIT ----------------
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.subheader("📦 Profit by Product")

        product_profit = get_product_profit(valid_df).reset_index()
        product_profit.columns = ["Pack", "Profit"]

        if not product_profit.empty:
            selected_product_rows = show_interactive_table(
                product_profit,
                key="product_table",
                label="Product Profit Table",
                height=320,
            )

            fig = px.bar(
                product_profit.head(15),
                x="Pack",
                y="Profit",
                title="Top Performing Packs",
            )
            st.plotly_chart(fig, use_container_width=True)

            if selected_product_rows:
                selected_packs = product_profit.iloc[selected_product_rows]["Pack"].tolist()
                detail_df = valid_df[valid_df["Pack"].isin(selected_packs)]
                st.markdown("**Selected product orders**")
                st.dataframe(
                    detail_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Selling Price": st.column_config.NumberColumn(format="₹ %.2f"),
                        "Actual Price": st.column_config.NumberColumn(format="₹ %.2f"),
                        "Profit": st.column_config.NumberColumn(format="₹ %.2f"),
                    },
                )
        else:
            st.info("No product data")

        st.markdown('</div>', unsafe_allow_html=True)

        # ---------------- PROFIT OVER TIME ----------------
        if cols.get("date") and cols["date"] in valid_df.columns:
            st.markdown('<div class="section-box">', unsafe_allow_html=True)
            st.subheader("📈 Profit Over Time")

            chart_df = profit_over_time(valid_df, cols["date"])
            if not chart_df.empty:
                fig = px.line(chart_df, x="Date", y="Profit", markers=True)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No date data")

            st.markdown('</div>', unsafe_allow_html=True)

        # ---------------- MISSING PRICING ----------------
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.subheader("⚠️ Missing Pricing")

        if not missing_df.empty:
            missing_view_cols = [c for c in ["Pack", "Selling Price", cols.get("user"), cols.get("date"), cols.get("status")] if c and c in missing_df.columns]
            missing_view = missing_df[missing_view_cols].copy()

            selected_missing_rows = show_interactive_table(
                missing_view,
                key="missing_table",
                label="Missing Pricing Table",
                height=280,
            )

            if selected_missing_rows:
                st.markdown("**Selected missing rows**")
                st.dataframe(
                    missing_df.iloc[selected_missing_rows],
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.success("No missing pricing 🎉")

        st.markdown('</div>', unsafe_allow_html=True)

        # ---------------- RAW DATA ----------------
        if show_raw:
            st.markdown('<div class="section-box">', unsafe_allow_html=True)
            st.subheader("📋 Raw Data")

            st.dataframe(
                valid_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Selling Price": st.column_config.NumberColumn(format="₹ %.2f"),
                    "Actual Price": st.column_config.NumberColumn(format="₹ %.2f"),
                    "Profit": st.column_config.NumberColumn(format="₹ %.2f"),
                },
            )

            st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Upload both CSV files to begin")