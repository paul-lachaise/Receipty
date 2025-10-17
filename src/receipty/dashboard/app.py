import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import time

from receipty.config import settings

supabase: Client = create_client(settings.supabase_url, settings.supabase_api_key)


# Authentication
def authenticate():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "role" not in st.session_state:
        st.session_state.role = None

    if not st.session_state.authenticated:
        st.subheader("Login")
        password = st.text_input("Enter password:", type="password")
        if st.button("Login"):
            if password == settings.streamlit_guest_password:
                st.session_state.authenticated = True
                st.session_state.role = "guest"
                st.rerun()
            elif password == settings.streamlit_dev_password:
                st.session_state.authenticated = True
                st.session_state.role = "developer"
                st.rerun()
            else:
                st.error("Incorrect password")
        return False
    return True


# Main App
def main():
    st.title("OCR Dashboard")

    # Add logout and refresh buttons in a row
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()
    with col2:
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.role = None
            st.success("Successfully logged out!")
            time.sleep(1)
            st.rerun()

    @st.cache_data(ttl=3600)
    def load_data():
        response = supabase.table("items").select("*").execute()
        return pd.DataFrame(response.data)

    df = load_data()

    # Developer-only features
    if st.session_state.role == "developer":
        st.success("Developer Mode: Full access")
        st.write("Raw data preview:")
        st.dataframe(df)

    # Guest features (limited access)
    elif st.session_state.role == "guest":
        st.info("Guest Mode: Limited access")
        st.dataframe(df[["name", "price", "quantity", "category"]])

    # Total expenses
    total_expenses = df["price"].sum()
    st.divider()
    st.subheader("Total Expenses")
    st.metric(label="Total Spending", value=f"{total_expenses:.2f} €")

    # Expenses by category
    st.subheader("Expenses by Category")

    unique_categories = df["category"].nunique()
    total_items = len(df)
    st.caption(f"Displaying {total_items} items across {unique_categories} categories")

    fig = px.bar(df, x="category", y="price", title="Spending by Category")
    st.plotly_chart(fig, use_container_width=True)

    # Category ranking by total spending
    st.subheader("Category Ranking by Total Spending")
    category_sum = df.groupby("category")["price"].sum().reset_index()
    category_sum = category_sum.sort_values(by="price", ascending=False)
    category_sum.columns = ["Category", "Total Spending"]
    # Add total row
    total_expenses = category_sum["Total Spending"].sum()
    total_row = pd.DataFrame(
        {"Category": ["TOTAL"], "Total Spending": [total_expenses]}
    )
    category_sum = pd.concat([category_sum, total_row], ignore_index=True)

    st.table(
        category_sum.style.format({"Total Spending": "{:.2f} €"}).hide(axis="index")
    )

    # Developer-only tools
    if st.session_state.role == "developer":
        st.divider()
        st.subheader("Developer Tools")
        st.code(
            f"""
        Supabase URL: {settings.supabase_url}
        Table: items
        Total rows: {len(df)}
        """
        )


# Run the app
if authenticate():
    main()
