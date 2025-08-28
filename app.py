import streamlit as st
import pandas as pd
import datetime
import time
import os
import traceback


from config import LOGO_PATH, CUSTOM_YEAR_COL, SALES_VALUE_GBP_COL, LISTING_COL, WEEK_AS_INT_COL, DATE_COL 
from utils import format_currency, format_currency_int, get_daily_target_actual, get_weekly_target_actual, calculate_variance #
from data_loader import load_data_from_gsheet, load_targets_from_gsheet
from processing import preprocess_data # Assuming this file exists and is correct


from tabs import kpi, yoy_trends, daily_prices, sku_trends, pivot_table, unrecognised_sales
from tabs import seasonality_load
from tabs import category_summary 
from tabs import price_range_analysis
from tabs import ppc_analytics 

# --- Page Config ---
st.set_page_config(
    page_title="YOY Sales Analytics Dashboard", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Session State Initialization for Stable UI ---
# Initialize session state to prevent tab jumping and preserve scroll position
if 'ui_initialized' not in st.session_state:
    st.session_state.ui_initialized = True
    st.session_state.prevent_tab_jump = True


st.markdown("""
<style>
    /* Force pure black theme */
    .stApp {
        background-color: #0d1117 !important;
        color: #f0f6fc !important;
    }
    
    /* Dark theme for all containers */
    .stApp > div, .stApp > div > div, .stApp > div > div > div {
        background-color: #0d1117 !important;
        color: #f0f6fc !important;
    }
    
    /* Sidebar dark theme */
    .css-1d391kg {
        background-color: #21262d !important;
    }
    
    /* Main content area */
    .main .block-container {
        background-color: #0d1117 !important;
        color: #f0f6fc !important;
    }
    
    /* Prevent unwanted scrolling behavior */
    html, body {
        scroll-behavior: auto !important;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0d1117 !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #0d1117 !important;
        color: #f0f6fc !important;
    }
    
    /* Force white text for readability */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        color: #f0f6fc !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Simple Styling (Similar to Old Dashboard) ---
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Main app styling - minimal */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }
    
    .header-title {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    
    .header-subtitle {
        color: rgba(255, 255, 255, 0.9);
        font-size: 1.1rem;
        font-weight: 400;
        margin: 0.5rem 0 0 0;
    }
</style>
""", unsafe_allow_html=True)

# --- Header Section ---
st.markdown("""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 class="header-title">Sales Analytics Dashboard</h1>
            <p class="header-subtitle">Year-over-Year Performance & Insights</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Performance Tracker ---
performance_start = time.time()
st.sidebar.markdown("### ⚡ Performance Tracker")
performance_placeholder = st.sidebar.empty()

try:
    # =============================================================================
    # Data Loading and Processing Orchestration
    # =============================================================================
    
    # Load Data
    with st.spinner("Loading data from Google Sheets..."):
        df_raw = load_data_from_gsheet() # Function handles caching and errors
    
    if df_raw is None or df_raw.empty:
        st.warning("Failed to load data from Google Sheet or the sheet is empty. Dashboard cannot proceed.")  
        st.stop() # Stop execution if data loading fails
    
    # Load Targets Data
    with st.spinner("Loading targets data..."):
        df_targets = load_targets_from_gsheet()  # Load targets (can be None if not available)
    
    load_time = time.time() - performance_start
    
    # Preprocess Data  
    with st.spinner("Processing and transforming data..."):
        try:
            # Pass a copy to prevent modifying the cached raw data if preprocess_data alters it
            df = preprocess_data(df_raw.copy()) # Function handles caching and errors
        except Exception as e:
            st.error(f"An error occurred during data preprocessing: {e}")
            st.error(traceback.format_exc())
            st.stop() # Stop execution if preprocessing fails
    
    # Check if preprocessing returned valid data
    if df is None or df.empty:
        st.error("Data is empty after preprocessing. Please check the 'processing.py' function logic and the source data.")
        st.stop()
    
    process_time = time.time() - performance_start - load_time
    
    # =============================================================================
    # Prepare Common Filter Variables (Derived from Processed Data 'df')
    # =============================================================================
    
    # These are calculated once and passed to the relevant tabs
    if CUSTOM_YEAR_COL not in df.columns:
        st.error(f"Critical Error: '{CUSTOM_YEAR_COL}' column not found after preprocessing.")
        st.stop()
    
    available_custom_years = sorted(pd.to_numeric(df[CUSTOM_YEAR_COL], errors='coerce').dropna().unique().astype(int))
    
    if not available_custom_years:
        st.error(f"No valid '{CUSTOM_YEAR_COL}' data found after preprocessing. Check calculations and sheet content.")
        st.stop()
    
    # Determine current, previous, and default years for filters
    current_custom_year = available_custom_years[-1]
    prev_custom_year = available_custom_years[-2] if len(available_custom_years) >= 2 else None
    
    # Default for YOY charts/comparisons: current and previous year if available
    yoy_default_years = [prev_custom_year, current_custom_year] if prev_custom_year is not None else [current_custom_year]
    
    # Default for single-year views (like Pivot table initially): current year
    default_current_year = [current_custom_year]
    
    # Calculate data metrics for performance display
    total_records = len(df)
    date_range = f"{df[DATE_COL].min().strftime('%Y-%m-%d')} to {df[DATE_COL].max().strftime('%Y-%m-%d')}" if DATE_COL in df.columns else "Unknown"
    latest_data_date = df[DATE_COL].max().strftime('%d %b %Y') if DATE_COL in df.columns else "Unknown"
    total_sales = df[SALES_VALUE_GBP_COL].sum() if SALES_VALUE_GBP_COL in df.columns else 0
    
    # Update performance tracker
    performance_placeholder.markdown(f"""
    **📊 Data Overview**
    - **Records:** {total_records:,}
    - **Date Range:** {date_range}
    - **Total Sales:** £{total_sales:,.0f}
    
    **⏱️ Load Times**
    - **Data Load:** {load_time:.1f}s
    - **Processing:** {process_time:.1f}s
    - **Total:** {time.time() - performance_start:.1f}s
    """)
    
    # =============================================================================
    # Define and Display Dashboard Tabs with Scroll Control
    # =============================================================================
    
    # Add container to control scroll behavior
    with st.container():
        tab_names = [
            "📊 KPIs",
            "📈 YOY Trends", 
            "💰 Daily Prices",
            "🔍 SKU Trends",
            "🎯 PPC Analytics",
            "📂 Category Summary",
            "💰 Price Range Analysis",
            "🌊 Seasonality Load", 
            "📋 Pivot Table",
            "❓ Unrecognised Sales"
        ]
        
        # Create tab objects
        tab_kpi, tab_yoy, tab_daily, tab_sku, tab_ppc, tab_category, tab_price_range, tab_seasonality, tab_pivot, tab_unrec = st.tabs(tab_names)
    
    # Render content for each tab by calling its display function
    with tab_kpi:
        kpi.display_tab(df, available_custom_years, current_custom_year, df_targets)
    
    with tab_yoy:
        yoy_trends.display_tab(df, available_custom_years, yoy_default_years)
    
    with tab_daily:
        daily_prices.display_tab(df, available_custom_years, default_current_year)
    
    with tab_sku:
        sku_trends.display_tab(df, available_custom_years, yoy_default_years)
    
    with tab_ppc:
        ppc_analytics.display_tab()
    
    with tab_category:
        category_summary.display_tab(df, available_custom_years, yoy_default_years)
    
    with tab_price_range:
        price_range_analysis.display_tab(df, available_custom_years, yoy_default_years)
    
    with tab_seasonality:
        seasonality_load.display_tab(df, available_custom_years)
    
    with tab_pivot:
        pivot_table.display_tab(df, available_custom_years, default_current_year)
    
    with tab_unrec:
        unrecognised_sales.display_tab(df)

    # --- Footer ---
    st.markdown("""
    <hr style="margin: 3rem 0 1rem 0; border: none; height: 1px; background: linear-gradient(90deg, transparent, #ccc, transparent);">
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align: center; color: #64748b; padding: 2rem;">
        <p style="margin: 0; font-size: 0.9rem;">
            🚀 Putting the 'Awesome' in Sales Analytics | 
            <span style="color: #3b82f6;">Dashboard is up to date</span> | 
            <span style="color: #64748b;">Data as of: {latest_data_date}</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

except Exception as e:
    st.error("An unexpected error occurred:")
    st.error(traceback.format_exc())
    st.warning("Please refresh the page or contact support if the issue persists.")
