import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
from datetime import date


st.set_page_config(layout="wide", page_title="Receipty Dashboard")


supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_API_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)

GUEST_PASSWORD = st.secrets["STREAMLIT_GUEST_PASSWORD"]
DEV_PASSWORD = st.secrets["STREAMLIT_DEV_PASSWORD"]


def authenticate():
    """Handles user authentication and role management with an improved UI."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.markdown(
            """
            <style>
                .main {
                    background-color: #f5f5f5;
                }
                .st-form {
                    background-color: white;
                    border-radius: 10px;
                    padding: 2rem;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                }
            </style>
            """,
            unsafe_allow_html=True,
        )

        _, center_col, _ = st.columns([1, 1.5, 1])
        with center_col:
            with st.form("login_form"):
                st.markdown(
                    "<h1 style='text-align: center;'>Welcome to Receipty</h1>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<p style='text-align: center;'>Log in to access your expense analysis dashboard.</p>",
                    unsafe_allow_html=True,
                )

                password = st.text_input(
                    "Password",
                    type="password",
                    key="password_input",
                    placeholder="Enter your password",
                )
                submitted = st.form_submit_button("Login", use_container_width=True)

                if submitted:
                    if password == GUEST_PASSWORD:
                        st.session_state.authenticated = True
                        st.session_state.role = "guest"
                        st.rerun()
                    elif password == DEV_PASSWORD:
                        st.session_state.authenticated = True
                        st.session_state.role = "developer"
                        st.rerun()
                    else:
                        st.error("Incorrect password.")

                st.markdown(
                    "<p style='text-align: center; font-size: small; color: grey;'>Created by Paul Lachaise</p>",
                    unsafe_allow_html=True,
                )
        return False
    return True


# DATA LOADING AND CACHING
@st.cache_data(ttl=600)
def load_data():
    """
    Loads data from Supabase, merges receipts and items, and prepares it for analysis.
    """
    receipts_response = (
        supabase.table("receipts")
        .select("id, receipt_date, merchant, status")
        .execute()
    )
    items_response = (
        supabase.table("items")
        .select("receipt_id, name, price, quantity, category")
        .execute()
    )

    receipts_df = pd.DataFrame(receipts_response.data)
    items_df = pd.DataFrame(items_response.data)

    if receipts_df.empty or items_df.empty:
        return pd.DataFrame()

    receipts_df["receipt_date"] = pd.to_datetime(receipts_df["receipt_date"])

    df = pd.merge(
        items_df, receipts_df, left_on="receipt_id", right_on="id", how="left"
    )

    df["total_price"] = df["price"] * df["quantity"]

    return df


# MAIN APP
def main():
    """
    The main function that runs the Streamlit dashboard.
    """
    st.title("Receipty Dashboard")
    st.caption(
        f"Welcome, {st.session_state.role} | Today is {date.today().strftime('%B %d, %Y')}"
    )

    df_full = load_data()
    if df_full.empty:
        st.warning("No data found in the database. Please generate some data first.")
        return

    # SIDEBAR FILTERS
    st.sidebar.header("Filters & Controls")

    # Date Range Filter
    min_date = df_full["receipt_date"].min().date()
    max_date = df_full["receipt_date"].max().date()

    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="date_range_filter",
    )

    if date_range and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    all_categories = sorted(df_full["category"].unique())
    selected_categories = st.sidebar.multiselect(
        "Select Categories",
        all_categories,
        default=all_categories,
        key="category_filter",
    )

    all_merchants = sorted(df_full["merchant"].unique())
    selected_merchants = st.sidebar.multiselect(
        "Select Merchants", all_merchants, default=all_merchants, key="merchant_filter"
    )

    # FILTERING LOGIC
    df_filtered = df_full[
        (df_full["receipt_date"].dt.date >= start_date)
        & (df_full["receipt_date"].dt.date <= end_date)
        & (df_full["category"].isin(selected_categories))
        & (df_full["merchant"].isin(selected_merchants))
    ].copy()

    # SIDEBAR BUTTONS
    st.sidebar.divider()

    def reset_filters_callback():
        st.session_state.date_range_filter = (min_date, max_date)
        st.session_state.category_filter = all_categories
        st.session_state.merchant_filter = all_merchants

    st.sidebar.button(
        "Reset Filters", on_click=reset_filters_callback, use_container_width=True
    )

    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col2:
        if st.button("Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.role = None
            st.rerun()

    # MAIN PAGE LAYOUT
    if df_filtered.empty:
        st.warning("No data matches the current filter settings.")
        return

    # KPIs SECTION
    st.header("Key Performance Indicators")
    total_expenses = df_filtered["total_price"].sum()
    num_receipts = df_filtered["receipt_id"].nunique()
    avg_per_receipt = total_expenses / num_receipts if num_receipts > 0 else 0
    top_category = (
        df_filtered.groupby("category")["total_price"].sum().idxmax()
        if not df_filtered.empty
        else "N/A"
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Spend", f"{total_expenses:.2f} €")
    col2.metric("Receipts Analyzed", num_receipts)
    col3.metric("Average per Receipt", f"{avg_per_receipt:.2f} €")
    col4.metric("Top Category", top_category)

    st.divider()

    # CHARTS SECTION
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Expenses by Category")
        category_spending = (
            df_filtered.groupby("category")["total_price"].sum().reset_index()
        )
        fig_cat = px.bar(
            category_spending,
            x="category",
            y="total_price",
            title="Total Spending per Category",
            labels={"total_price": "Total (€)"},
        )
        st.plotly_chart(fig_cat, use_container_width=True)

    with col2:
        st.subheader("Expenses Over Time")
        daily_spending = (
            df_filtered.groupby(df_filtered["receipt_date"].dt.date)["total_price"]
            .sum()
            .reset_index()
        )
        fig_time = px.line(
            daily_spending,
            x="receipt_date",
            y="total_price",
            title="Daily Spending",
            markers=True,
            labels={"receipt_date": "Date", "total_price": "Total (€)"},
        )
        st.plotly_chart(fig_time, use_container_width=True)

    # ADVANCED STATS BY MERCHANT (DEPENDS ON FILTERS)
    st.divider()
    st.header("Analysis by Merchant")

    if not df_filtered.empty:
        receipt_totals = (
            df_filtered.groupby(["receipt_id", "merchant"])["total_price"]
            .sum()
            .reset_index()
        )
        avg_receipt_by_merchant = (
            receipt_totals.groupby("merchant")["total_price"].mean().reset_index()
        )
        avg_receipt_by_merchant.rename(
            columns={"total_price": "Average Receipt (€)"}, inplace=True
        )

        category_spending_per_merchant = (
            df_filtered.groupby(["merchant", "category"])["total_price"]
            .sum()
            .reset_index()
        )
        dominant_category_idx = category_spending_per_merchant.groupby("merchant")[
            "total_price"
        ].idxmax()
        dominant_category_by_merchant = category_spending_per_merchant.loc[
            dominant_category_idx
        ][["merchant", "category"]]
        dominant_category_by_merchant.rename(
            columns={"category": "Dominant Category"}, inplace=True
        )

        merchant_stats_df = pd.merge(
            avg_receipt_by_merchant, dominant_category_by_merchant, on="merchant"
        )
        merchant_stats_df = merchant_stats_df.sort_values(
            by="Average Receipt (€)", ascending=False
        )

        st.subheader("Merchant Statistics")
        st.dataframe(
            merchant_stats_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Average Receipt (€)": st.column_config.NumberColumn(format="%.2f €")
            },
        )

    # MONTHLY ANALYSIS SECTION (INDEPENDENT OF FILTERS)
    st.divider()
    st.header("Monthly Analysis")

    if not df_full.empty:
        df_monthly_full = df_full.copy()
        df_monthly_full["month_period"] = df_monthly_full["receipt_date"].dt.to_period(
            "M"
        )
        monthly_summary = (
            df_monthly_full.groupby("month_period")["total_price"].sum().reset_index()
        )

        today = date.today()
        current_month_period = pd.Period(today, "M")
        previous_month_period = current_month_period - 1

        current_month_spend_series = monthly_summary[
            monthly_summary["month_period"] == current_month_period
        ]["total_price"]
        current_month_spend = current_month_spend_series.sum()

        previous_month_spend_series = monthly_summary[
            monthly_summary["month_period"] == previous_month_period
        ]["total_price"]
        previous_month_spend = previous_month_spend_series.sum()

        historical_monthly_summary = monthly_summary[
            monthly_summary["month_period"] < current_month_period
        ]
        average_monthly_spend = (
            historical_monthly_summary["total_price"].mean()
            if not historical_monthly_summary.empty
            else 0
        )

        delta_vs_previous_abs = current_month_spend - previous_month_spend
        delta_vs_previous_pct = (
            (delta_vs_previous_abs / previous_month_spend) * 100
            if previous_month_spend > 0
            else None
        )

        delta_vs_average_abs = current_month_spend - average_monthly_spend
        delta_vs_average_pct = (
            (delta_vs_average_abs / average_monthly_spend) * 100
            if average_monthly_spend > 0
            else None
        )

        col1, col2, col3 = st.columns(3)
        col1.metric(
            f"Spend for {current_month_period.strftime('%B %Y')}",
            f"{current_month_spend:.2f} €",
        )
        col2.metric(
            f"vs Previous Month ({previous_month_period.strftime('%B')}: {previous_month_spend:.2f}€)",
            (
                f"{delta_vs_previous_pct:.1f}%"
                if delta_vs_previous_pct is not None
                else "N/A"
            ),
            (
                f"{delta_vs_previous_abs:+.2f} €"
                if delta_vs_previous_abs is not None
                else None
            ),
            delta_color="inverse",
        )
        col3.metric(
            f"vs Monthly Average ({average_monthly_spend:.2f}€)",
            (
                f"{delta_vs_average_pct:.1f}%"
                if delta_vs_average_pct is not None
                else "N/A"
            ),
            (
                f"{delta_vs_average_abs:+.2f} €"
                if delta_vs_average_abs is not None
                else None
            ),
            delta_color="inverse",
        )

        monthly_summary["Month"] = monthly_summary["month_period"].dt.strftime("%Y-%m")

        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Historical Spending")
            st.dataframe(
                monthly_summary[["Month", "total_price"]].sort_values(
                    by="Month", ascending=False
                ),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Month": "Month",
                    "total_price": st.column_config.NumberColumn(
                        "Total Spent", format="%.2f €"
                    ),
                },
            )
        with col2:
            st.subheader("Monthly Trend")
            fig_monthly_bar = px.bar(
                monthly_summary,
                x="Month",
                y="total_price",
                title="Total Spending per Month",
                labels={"Month": "Month", "total_price": "Total Spend (€)"},
            )
            st.plotly_chart(fig_monthly_bar, use_container_width=True)

    # DETAILED DATA SECTION
    with st.expander("View Detailed Item Data", expanded=True):
        if not df_filtered.empty:
            receipt_summary = (
                df_filtered.groupby(["receipt_id", "receipt_date", "merchant"])[
                    "total_price"
                ]
                .sum()
                .reset_index()
            )

            receipt_summary = receipt_summary.sort_values(
                by="receipt_date", ascending=False
            )

            receipt_summary["display_label"] = receipt_summary.apply(
                lambda row: f"{row['receipt_date'].strftime('%Y-%m-%d')} - {row['merchant']} ({row['total_price']:.2f}€)",
                axis=1,
            )

            receipt_options = receipt_summary["display_label"].tolist()
            selected_receipt_label = st.selectbox(
                "Select a specific receipt to view its items:", receipt_options
            )

            if selected_receipt_label:
                selected_receipt_id = receipt_summary[
                    receipt_summary["display_label"] == selected_receipt_label
                ]["receipt_id"].iloc[0]

                items_of_selected_receipt = df_filtered[
                    df_filtered["receipt_id"] == selected_receipt_id
                ]

                st.dataframe(
                    items_of_selected_receipt[
                        ["name", "quantity", "price", "total_price", "category"]
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
        else:
            st.info("No receipts match the current filters.")

    # DEVELOPER SECTION
    if st.session_state.role == "developer":
        with st.expander("Developer Tools"):
            st.subheader("Raw Data Inspector")
            st.dataframe(df_full)

            st.divider()
            st.subheader("Failed Receipts Queue")

            df_failed = df_full[df_full["status"] == "failed"]

            if df_failed.empty:
                st.success("No failed receipts found. All clear!")
            else:
                st.warning(f"Found {len(df_failed)} failed receipts.")
                st.dataframe(df_failed[["receipt_date", "merchant", "status"]])

                if st.button("Retry All Failed Receipts", use_container_width=True):
                    try:
                        supabase.table("receipts").update({"status": "pending"}).eq(
                            "status", "failed"
                        ).execute()

                        st.success("All failed receipts have been reset to 'pending'.")

                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"An error occurred: {e}")


# RUN THE APP
if authenticate():
    main()
