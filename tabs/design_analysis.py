import streamlit as st
import pandas as pd
import plotly.express as px
from config import (
    CUSTOM_YEAR_COL, WEEK_AS_INT_COL, SALES_VALUE_GBP_COL, SALES_CHANNEL_COL, PRODUCT_COL, DESIGN_COL, DATE_COL
)

def display_tab(df, available_years):
    st.markdown("""
    # 🎨 Design Analysis
    Analyze how different product designs perform over time. Use the filters below to explore trends, compare designs, and spot opportunities.
    """)

    if DESIGN_COL not in df.columns:
        st.error(f"The required column '{DESIGN_COL}' is missing from your data.")
        return

    # --- Filters ---
    with st.expander("🎨 Design Analysis Filters", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            selected_years = st.multiselect("Year(s)", options=available_years, default=available_years[-2:], help="Select year(s) to analyze.")
        with col2:
            channel_options = sorted(df[SALES_CHANNEL_COL].dropna().unique()) if SALES_CHANNEL_COL in df.columns else []
            selected_channels = st.multiselect("Channel(s)", options=channel_options, default=[], help="Filter by sales channel.")
        with col3:
            product_options = sorted(df[PRODUCT_COL].dropna().unique()) if PRODUCT_COL in df.columns else []
            selected_products = st.multiselect("Product(s)", options=product_options, default=[], help="Filter by product.")
        with col4:
            design_options = sorted(df[DESIGN_COL].dropna().unique())
            selected_designs = st.multiselect("Design(s)", options=design_options, default=[], help="Filter by design.")

    # --- Filter Data ---
    filtered = df.copy()
    if selected_years:
        filtered = filtered[filtered[CUSTOM_YEAR_COL].isin(selected_years)]
    if selected_channels:
        filtered = filtered[filtered[SALES_CHANNEL_COL].isin(selected_channels)]
    if selected_products:
        filtered = filtered[filtered[PRODUCT_COL].isin(selected_products)]
    if selected_designs:
        filtered = filtered[filtered[DESIGN_COL].isin(selected_designs)]

    # --- Time Series Chart: Sales by Design ---
    st.markdown("## 📈 Sales by Design Over Time")
    if not filtered.empty:
        filtered[DATE_COL] = pd.to_datetime(filtered[DATE_COL], errors='coerce')
        filtered['Month'] = filtered[DATE_COL].dt.to_period('M').astype(str)
        sales_by_month = filtered.groupby(['Month', DESIGN_COL])[SALES_VALUE_GBP_COL].sum().reset_index()
        fig = px.line(
            sales_by_month,
            x='Month', y=SALES_VALUE_GBP_COL, color=DESIGN_COL,
            markers=True,
            title="Monthly Sales by Design",
            labels={SALES_VALUE_GBP_COL: "Sales (£)", 'Month': "Month", DESIGN_COL: "Design"},
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_layout(
            plot_bgcolor='#222',
            paper_bgcolor='#222',
            font_color='#EEE',
            legend_title_text='Design',
            hovermode='x unified',
            title_font_size=22
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")

    # --- Table: Total Sales by Design ---
    st.markdown("## 🏆 Top Designs by Total Sales")
    if not filtered.empty:
        design_table = filtered.groupby(DESIGN_COL)[SALES_VALUE_GBP_COL].sum().reset_index()
        design_table = design_table.sort_values(SALES_VALUE_GBP_COL, ascending=False)
        design_table[SALES_VALUE_GBP_COL] = design_table[SALES_VALUE_GBP_COL].map('£{:,.0f}'.format)
        st.dataframe(
            design_table,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No data to display in the table for the selected filters.")

    st.markdown("---")
    st.caption("Pro tip: Use the filters above to focus on new launches, seasonal trends, or compare design families!") 