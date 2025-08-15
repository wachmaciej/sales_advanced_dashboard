# tabs/price_range_analysis.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from utils import format_currency, format_currency_int
from config import (
    SALES_CHANNEL_COL, SALES_VALUE_GBP_COL, DATE_COL, CUSTOM_YEAR_COL, WEEK_AS_INT_COL,
    PRICE_RANGE_UK_COL, PRICE_RANGE_US_COL, UK_CHANNELS, US_CHANNELS, 
    PRICE_RANGES, LISTING_COL, ORDER_QTY_COL_RAW, PRODUCT_COL,
    CUSTOM_WEEK_START_COL
)

@st.cache_data
def get_applicable_price_range_cached(channel_list, df_subset):
    """Cached version of price range calculation for better performance."""
    result = []
    for i, channel in enumerate(channel_list):
        if pd.isna(channel):
            result.append('0')
            continue
            
        channel_str = str(channel).strip()
        channel_lower = channel_str.lower()
        
        # Get the row data
        row_data = df_subset.iloc[i]
        
        # Check for UK channels (exact match first, then flexible)
        if channel_str in UK_CHANNELS or any(keyword in channel_lower for keyword in ['ra website uk', 'website uk', 'amazon uk']):
            result.append(row_data.get(PRICE_RANGE_UK_COL, '0'))
        # Check for US channels (exact match first, then flexible) 
        elif channel_str in US_CHANNELS or any(keyword in channel_lower for keyword in ['ra website us', 'website us', 'amazon us']):
            result.append(row_data.get(PRICE_RANGE_US_COL, '0'))
        else:
            result.append('0')  # Default for other channels
    
    return result

@st.cache_data
def filter_and_prepare_data(df, selected_channels, selected_years, selected_weeks=None, selected_ranges=None):
    """Cache the main data filtering and preparation step."""
    # Filter data
    base_filter = (
        (df[SALES_CHANNEL_COL].isin(selected_channels)) &
        (df[CUSTOM_YEAR_COL].isin(selected_years))
    )
    
    # Add week filter if specific weeks are selected
    if selected_weeks and WEEK_AS_INT_COL in df.columns:
        week_filter = df[WEEK_AS_INT_COL].isin(selected_weeks)
        filtered_df = df[base_filter & week_filter].copy()
    else:
        filtered_df = df[base_filter].copy()
    
    if filtered_df.empty:
        return pd.DataFrame()
    
    # Add applicable price range column using cached function
    channel_list = filtered_df[SALES_CHANNEL_COL].tolist()
    price_ranges = get_applicable_price_range_cached(
        channel_list, 
        filtered_df[[PRICE_RANGE_UK_COL, PRICE_RANGE_US_COL]]
    )
    filtered_df['Applicable_Price_Range'] = price_ranges
    
    # Filter by selected price ranges
    if selected_ranges:
        filtered_df = filtered_df[filtered_df['Applicable_Price_Range'].isin(selected_ranges)]
    
    return filtered_df

@st.cache_data
def calculate_range_summary(filtered_df):
    """Cache the range summary calculations."""
    range_summary = filtered_df.groupby('Applicable_Price_Range').agg({
        SALES_VALUE_GBP_COL: 'sum',
        ORDER_QTY_COL_RAW: 'sum' if ORDER_QTY_COL_RAW in filtered_df.columns else 'count'
    }).reset_index()
    
    range_summary['Sales_Pct'] = (range_summary[SALES_VALUE_GBP_COL] / range_summary[SALES_VALUE_GBP_COL].sum() * 100)
    range_summary['AOV'] = range_summary[SALES_VALUE_GBP_COL] / range_summary[ORDER_QTY_COL_RAW]
    range_summary['AOV'] = range_summary['AOV'].fillna(0)
    
    return range_summary

@st.cache_data
def calculate_weekly_trends(filtered_df):
    """Cache weekly trends calculation using custom Saturday-Friday weeks (aligned with YOY trends)."""
    if CUSTOM_WEEK_START_COL not in filtered_df.columns or CUSTOM_YEAR_COL not in filtered_df.columns:
        return pd.DataFrame()
    
    # Group by custom week start date and year (same as YOY trends for consistency)
    weekly_trends = filtered_df.groupby([CUSTOM_YEAR_COL, CUSTOM_WEEK_START_COL, 'Applicable_Price_Range'])[SALES_VALUE_GBP_COL].sum().reset_index()
    
    # Convert custom week start to week number for display (matching company Saturday-Friday weeks)
    if not weekly_trends.empty and WEEK_AS_INT_COL in filtered_df.columns:
        # Get the week number mapping from the original data
        week_mapping = filtered_df[[CUSTOM_WEEK_START_COL, WEEK_AS_INT_COL]].drop_duplicates()
        weekly_trends = weekly_trends.merge(week_mapping, on=CUSTOM_WEEK_START_COL, how='left')
        
        # Create week display labels with actual Saturday dates (company week start dates)
        weekly_trends['Week_Display'] = weekly_trends.apply(lambda row: 
            f"W{int(row[WEEK_AS_INT_COL]):02d} ({row[CUSTOM_WEEK_START_COL].strftime('%Y-%m-%d')})" 
            if pd.notna(row[WEEK_AS_INT_COL]) and pd.notna(row[CUSTOM_WEEK_START_COL]) 
            else "W??", axis=1)
    else:
        # Fallback if week mapping not available
        weekly_trends['Week_Display'] = "Week"
        weekly_trends[WEEK_AS_INT_COL] = 1
    
    # Sort by year and custom week start date for proper chronological order (Saturday-Friday)
    weekly_trends = weekly_trends.sort_values([CUSTOM_YEAR_COL, CUSTOM_WEEK_START_COL])
    
    return weekly_trends

@st.cache_data
def calculate_channel_breakdown(filtered_df):
    """Cache channel breakdown calculations."""
    return filtered_df.groupby([SALES_CHANNEL_COL, 'Applicable_Price_Range']).agg({
        SALES_VALUE_GBP_COL: 'sum',
        ORDER_QTY_COL_RAW: 'sum' if ORDER_QTY_COL_RAW in filtered_df.columns else 'count'
    }).reset_index()

@st.cache_data
def calculate_listing_performance(filtered_df):
    """Cache listing performance calculations."""
    if LISTING_COL not in filtered_df.columns:
        return pd.DataFrame()
    
    # Group listings by price range and calculate performance metrics
    listing_performance = filtered_df.groupby(['Applicable_Price_Range', LISTING_COL]).agg({
        SALES_VALUE_GBP_COL: 'sum',
        ORDER_QTY_COL_RAW: 'sum' if ORDER_QTY_COL_RAW in filtered_df.columns else 'count'
    }).reset_index()
    
    # Calculate AOV per listing
    listing_performance['Listing_AOV'] = listing_performance[SALES_VALUE_GBP_COL] / listing_performance[ORDER_QTY_COL_RAW]
    listing_performance['Listing_AOV'] = listing_performance['Listing_AOV'].fillna(0)
    
    return listing_performance

@st.cache_data
def calculate_product_performance(filtered_df):
    """Cache product performance calculations."""
    if PRODUCT_COL not in filtered_df.columns:
        return pd.DataFrame()
    
    # Group products by price range and calculate performance metrics
    product_performance = filtered_df.groupby(['Applicable_Price_Range', PRODUCT_COL]).agg({
        SALES_VALUE_GBP_COL: 'sum',
        ORDER_QTY_COL_RAW: 'sum' if ORDER_QTY_COL_RAW in filtered_df.columns else 'count'
    }).reset_index()
    
    # Calculate AOV per product
    product_performance['Product_AOV'] = product_performance[SALES_VALUE_GBP_COL] / product_performance[ORDER_QTY_COL_RAW]
    product_performance['Product_AOV'] = product_performance['Product_AOV'].fillna(0)
    
    return product_performance

@st.cache_data
def calculate_weekly_trends_by_listing(filtered_df):
    """Cache weekly trends calculation by listing with Saturday-Friday weeks."""
    if (CUSTOM_WEEK_START_COL not in filtered_df.columns or 
        CUSTOM_YEAR_COL not in filtered_df.columns or 
        LISTING_COL not in filtered_df.columns):
        return pd.DataFrame()
    
    # Group by custom week start date, year, listing, and price range
    weekly_trends = filtered_df.groupby([
        CUSTOM_YEAR_COL, CUSTOM_WEEK_START_COL, LISTING_COL, 'Applicable_Price_Range'
    ])[SALES_VALUE_GBP_COL].sum().reset_index()
    
    # Convert custom week start to week number for display
    if not weekly_trends.empty and WEEK_AS_INT_COL in filtered_df.columns:
        # Get the week number mapping from the original data
        week_mapping = filtered_df[[CUSTOM_WEEK_START_COL, WEEK_AS_INT_COL]].drop_duplicates()
        weekly_trends = weekly_trends.merge(week_mapping, on=CUSTOM_WEEK_START_COL, how='left')
        
        # Create week display labels with actual Saturday dates
        weekly_trends['Week_Display'] = weekly_trends.apply(lambda row: 
            f"W{int(row[WEEK_AS_INT_COL]):02d} ({row[CUSTOM_WEEK_START_COL].strftime('%Y-%m-%d')})" 
            if pd.notna(row[WEEK_AS_INT_COL]) and pd.notna(row[CUSTOM_WEEK_START_COL]) 
            else "W??", axis=1)
        
        # Create combined legend label for listing + price range
        weekly_trends['Listing_PriceRange'] = weekly_trends[LISTING_COL] + " - " + weekly_trends['Applicable_Price_Range']
    else:
        # Fallback if week mapping not available
        weekly_trends['Week_Display'] = "Week"
        weekly_trends[WEEK_AS_INT_COL] = 1
        weekly_trends['Listing_PriceRange'] = "Unknown"
    
    # Sort by year and custom week start date for proper chronological order
    weekly_trends = weekly_trends.sort_values([CUSTOM_YEAR_COL, CUSTOM_WEEK_START_COL])
    
    return weekly_trends

def week_to_month(week_num):
    """Helper function to convert week number to month abbreviation."""
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    # Weeks 1-4 = Jan, 5-9 = Feb, 10-13 = Mar, etc.
    # More accurate mapping: approximately 4.33 weeks per month
    if week_num <= 4:
        return month_names[0]  # Jan
    elif week_num <= 9:
        return month_names[1]  # Feb
    elif week_num <= 13:
        return month_names[2]  # Mar
    elif week_num <= 17:
        return month_names[3]  # Apr
    elif week_num <= 22:
        return month_names[4]  # May
    elif week_num <= 26:
        return month_names[5]  # Jun
    elif week_num <= 30:
        return month_names[6]  # Jul
    elif week_num <= 35:
        return month_names[7]  # Aug
    elif week_num <= 39:
        return month_names[8]  # Sep
    elif week_num <= 43:
        return month_names[9]  # Oct
    elif week_num <= 48:
        return month_names[10] # Nov
    else:
        return month_names[11] # Dec

def get_applicable_price_range(channel, df_row):
    """Get the applicable price range for a given channel with exact matching."""
    if pd.isna(channel):
        return '0'
    
    channel_str = str(channel).strip()
    channel_lower = channel_str.lower()
    
    # Check for UK channels (exact match first, then flexible)
    if channel_str in UK_CHANNELS or any(keyword in channel_lower for keyword in ['ra website uk', 'website uk', 'amazon uk']):
        return df_row.get(PRICE_RANGE_UK_COL, '0')
    # Check for US channels (exact match first, then flexible) 
    elif channel_str in US_CHANNELS or any(keyword in channel_lower for keyword in ['ra website us', 'website us', 'amazon us']):
        return df_row.get(PRICE_RANGE_US_COL, '0')
    else:
        return '0'  # Default for other channels

@st.cache_data(ttl=300, show_spinner=False)  # Cache for 5 minutes
def get_price_range_data(df, selected_sales_channels, selected_years, selected_listings):
    """Cache heavy computations for price range analysis to prevent reprocessing on filter changes"""
    # Create a unique key for this data combination
    cache_key = f"{hash(tuple(selected_sales_channels))}_{hash(tuple(selected_years))}_{hash(tuple(selected_listings))}"
    
    # Filter the dataframe based on selections
    filtered_df = df[
        (df[SALES_CHANNEL_COL].isin(selected_sales_channels)) & 
        (df[CUSTOM_YEAR_COL].isin(selected_years)) &
        (df[LISTING_COL].isin(selected_listings))
    ].copy()
    
    if filtered_df.empty:
        return None, cache_key
    
    # Perform the heavy price range computations once and cache them
    price_bins = [0, 5, 10, 15, 25, 50, 100, float('inf')]
    price_labels = ['£0-£5', '£5-£10', '£10-£15', '£15-£25', '£25-£50', '£50-£100', '£100+']
    
    filtered_df = filtered_df.copy()
    # Calculate unit price from sales value and quantity
    filtered_df['unit_price_gbp'] = filtered_df[SALES_VALUE_GBP_COL] / filtered_df[ORDER_QTY_COL_RAW]
    filtered_df['price_range'] = pd.cut(filtered_df['unit_price_gbp'], bins=price_bins, labels=price_labels, right=False)
    
    # Group by week and price range for trend analysis
    weekly_price_trend = filtered_df.groupby([CUSTOM_WEEK_START_COL, 'price_range']).agg({
        SALES_VALUE_GBP_COL: 'sum',
        ORDER_QTY_COL_RAW: 'sum'
    }).reset_index()
    
    return weekly_price_trend, cache_key


def display_tab(df, available_custom_years, yoy_default_years):
    """Displays the Price Range Analysis tab."""
    
    st.markdown("### 💰 Price Range Analysis")
    st.markdown("Analyze sales trends by price ranges across different channels and identify impact of price reductions.")
    
    # Check if required columns exist
    required_cols = [PRICE_RANGE_UK_COL, PRICE_RANGE_US_COL, SALES_CHANNEL_COL]
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        st.error(f"Missing required columns for Price Range Analysis: {missing_cols}")
        st.info("Please ensure your Google Sheet contains 'Price Range UK' and 'Price Range US' columns.")
        return
    
    # Enhanced filters section
    with st.expander("🔧 Price Range Filters", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Channel filter with improved matching for RA Website UK/US
            all_channels = sorted(df[SALES_CHANNEL_COL].unique())
            expected_channels = UK_CHANNELS + US_CHANNELS
            
            # First try exact matching
            target_channels = [ch for ch in all_channels if ch in expected_channels]
            
            # If missing channels, try flexible matching for RA Website variations
            if len(target_channels) < 4:  # We expect 4 channels total
                for ch in all_channels:
                    if ch not in target_channels:  # Don't add duplicates
                        ch_lower = ch.lower()
                        # Check for RA Website UK variations
                        if any(keyword in ch_lower for keyword in ['ra website uk', 'website uk']):
                            target_channels.append(ch)
                        # Check for RA Website US variations
                        elif any(keyword in ch_lower for keyword in ['ra website us', 'website us']):
                            target_channels.append(ch)
                        # Check for Amazon variations
                        elif any(keyword in ch_lower for keyword in ['amazon uk', 'ra amazon uk']):
                            target_channels.append(ch)
                        elif any(keyword in ch_lower for keyword in ['amazon us', 'ra amazon us']):
                            target_channels.append(ch)
            
            # Show debug information about channel matching
            st.markdown("📡 **Sales Channels**")
            if not target_channels:
                st.error("❌ No UK/US channels found in data!")
                st.info(f"**Expected channels:** {expected_channels}")
                st.info(f"**Available channels in your data:** {all_channels}")
                st.info("💡 **Tip:** Channel names must contain 'RA Amazon UK/US' or 'RA Website UK/US'")
                return
                
            # Default to only "RA Amazon US" if available, otherwise all target channels
            ra_amazon_us_default = [ch for ch in target_channels if 'ra amazon us' in ch.lower()]
            default_channels = ra_amazon_us_default if ra_amazon_us_default else target_channels
                
            selected_channels = st.multiselect(
                "Select channels to analyze", 
                options=target_channels,
                default=default_channels,
                help="Only UK/US channels with price ranges are shown. Default shows RA Amazon US.",
                key="price_range_channels"
            )
        
        with col2:
            # Year filter - default to 2025 only
            year_2025_default = [2025] if 2025 in available_custom_years else yoy_default_years
            selected_years = st.multiselect(
                "📅 Years", 
                options=available_custom_years,
                default=year_2025_default,
                help="Select years for analysis"
            )
        
        with col3:
            # Week filter with slider
            available_weeks = sorted(df[WEEK_AS_INT_COL].unique()) if WEEK_AS_INT_COL in df.columns else []
            
            if available_weeks:
                st.markdown("📆 **Week Selection**")
                week_range = st.select_slider(
                    "Select Week Range",
                    options=available_weeks,
                    value=(available_weeks[0], available_weeks[-1]),
                    help="Drag to select range of weeks to analyze"
                )
                selected_weeks = list(range(week_range[0], week_range[1] + 1))
                
                # Show selected week info
                if week_range[0] == week_range[1]:
                    st.caption(f"📍 Selected: Week {week_range[0]}")
                else:
                    st.caption(f"📍 Selected: Weeks {week_range[0]}-{week_range[1]} ({len(selected_weeks)} weeks)")
            else:
                selected_weeks = []
        
        with col4:
            # Price range filter
            selected_ranges = st.multiselect(
                "💰 Price Ranges",
                options=[r for r in PRICE_RANGES if r != '0'],
                default=[r for r in PRICE_RANGES if r != '0'],
                help="Select price ranges to include"
            )
    
    if not selected_channels or not selected_years:
        st.warning("Please select at least one channel and year.")
        return
    
    # Show loading spinner for better UX
    with st.spinner('🔄 Filtering and processing data...'):
        # Use cached data filtering function
        filtered_df = filter_and_prepare_data(
            df, 
            selected_channels, 
            selected_years, 
            selected_weeks if selected_weeks else None,
            selected_ranges if selected_ranges else None
        )
    
    if filtered_df.empty:
        st.warning("No data found for selected filters.")
        return
    
    # Cache key calculations
    with st.spinner('📊 Calculating metrics...'):
        range_summary = calculate_range_summary(filtered_df)
        weekly_trends = calculate_weekly_trends(filtered_df)
        channel_breakdown = calculate_channel_breakdown(filtered_df)
        listing_performance = calculate_listing_performance(filtered_df)
        product_performance = calculate_product_performance(filtered_df)
    
    # === ANALYSIS SECTIONS ===
    
    # 1. Overview Metrics
    st.markdown("#### 📊 Price Range Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_sales = filtered_df[SALES_VALUE_GBP_COL].sum()
    total_orders = filtered_df[ORDER_QTY_COL_RAW].sum() if ORDER_QTY_COL_RAW in filtered_df.columns else len(filtered_df)
    avg_aov = total_sales / total_orders if total_orders > 0 else 0
    
    range_counts = filtered_df['Applicable_Price_Range'].value_counts()
    top_range = range_counts.index[0] if not range_counts.empty else "N/A"
    
    with col1:
        st.metric("Total Sales", format_currency_int(total_sales))
    
    with col2:
        st.metric("Total Orders", f"{total_orders:,}")
    
    with col3:
        st.metric("Average AOV", format_currency(avg_aov))
    
    with col4:
        st.metric("Top Price Range", top_range)
    
    # 2. Sales by Price Range - Pie Chart
    st.markdown("#### 🥧 Sales Distribution by Price Range")
    
    col1, col2 = st.columns(2)
    
    # Define consistent color palette for both charts
    # Professional color scheme that works well with dark theme
    price_range_colors = [
        '#4FC3F7',  # Light Blue - Full Price Range
        '#66BB6A',  # Green - Reduced Range  
        '#FFB74D',  # Orange - Stragglers
        '#F06292',  # Pink - Zero Stock
        '#9575CD'   # Purple - Additional ranges if needed
    ]

    with col1:
        # Modern enhanced pie chart for sales value
        fig_pie = go.Figure(data=[go.Pie(
            labels=range_summary['Applicable_Price_Range'],
            values=range_summary[SALES_VALUE_GBP_COL],
            hole=0.4,  # Create donut chart for modern look
            marker=dict(
                colors=price_range_colors,
                line=dict(color='#21262d', width=2)  # Dark border to match dashboard
            ),
            textinfo='percent+label',
            textposition='outside',
            textfont=dict(size=13, color='#f0f6fc', family='Inter'),  # Light text for dark theme
            hovertemplate="<b>%{label}</b><br>" +
                          "Sales: £%{value:,.0f}<br>" +
                          "Percentage: %{percent}<br>" +
                          "<extra></extra>",
            pull=[0.1, 0.05, 0.05, 0.05, 0.05],  # Pull out slices for 3D effect
            rotation=-45  # Changed to match order count distribution orientation
        )])
        
        # Add center text for donut chart
        fig_pie.add_annotation(
            text=f"<b>Total Sales</b><br>{format_currency_int(range_summary[SALES_VALUE_GBP_COL].sum())}",
            x=0.5, y=0.5,
            font_size=16,
            font_color="#f0f6fc",  # Light color for dark theme
            font_family="Inter",
            showarrow=False,
            align="center"
        )
        
        fig_pie.update_layout(
            title=dict(
                text="<b>💰 Sales Value Distribution</b>",
                font=dict(size=18, color="#f0f6fc", family="Inter"),  # Light title color
                x=0.5,
                y=0.95,
                xanchor='center'
            ),
            font=dict(family="Inter", size=12, color="#f0f6fc"),  # Light font color
            showlegend=False,  # Remove legend since order count chart has the same legend
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=500,
            margin=dict(l=20, r=50, t=100, b=20),  # Reduced right margin since no legend
            annotations=[
                dict(
                    text=f"<b>Total Sales</b><br><span style='font-size:16px'>{format_currency_int(range_summary[SALES_VALUE_GBP_COL].sum())}</span>",
                    x=0.5, y=0.5,
                    font_size=14,
                    font_color="#f0f6fc",  # Light annotation color
                    font_family="Inter",
                    showarrow=False,
                    align="center"
                )
            ]
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Modern enhanced pie chart for order count
        order_values = range_summary[ORDER_QTY_COL_RAW] if ORDER_QTY_COL_RAW in range_summary.columns else range_summary.index
        
        fig_pie_orders = go.Figure(data=[go.Pie(
            labels=range_summary['Applicable_Price_Range'],
            values=order_values,
            hole=0.4,  # Create donut chart for modern look
            marker=dict(
                colors=price_range_colors,  # Same color scheme as sales chart
                line=dict(color='#21262d', width=2)  # Dark border to match dashboard
            ),
            textinfo='percent+label',
            textposition='outside',
            textfont=dict(size=13, color='#f0f6fc', family='Inter'),  # Light text for dark theme
            hovertemplate="<b>%{label}</b><br>" +
                          "Orders: %{value:,.0f}<br>" +
                          "Percentage: %{percent}<br>" +
                          "<extra></extra>",
            pull=[0.1, 0.05, 0.05, 0.05, 0.05],  # Pull out slices for 3D effect
            rotation=-45  # Rotate opposite direction for balance
        )])
        
        # Add center text for donut chart
        total_orders = order_values.sum() if hasattr(order_values, 'sum') else len(order_values)
        
        fig_pie_orders.update_layout(
            title=dict(
                text="<b>📦 Order Count Distribution</b>",
                font=dict(size=18, color="#f0f6fc", family="Inter"),  # Light title color
                x=0.5,
                y=0.95,
                xanchor='center'
            ),
            font=dict(family="Inter", size=12, color="#f0f6fc"),  # Light font color
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05,
                font=dict(size=12, color="#f0f6fc"),  # Light legend text
                bgcolor="rgba(13,17,23,0.8)",  # Dark background to match dashboard
                bordercolor="rgba(33,38,45,0.8)",  # Dark border
                borderwidth=1,
                itemsizing="constant",
                itemwidth=30
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=500,
            margin=dict(l=20, r=150, t=100, b=20),  # Increased top margin from 80 to 100
            annotations=[
                dict(
                    text=f"<b>Total Orders</b><br><span style='font-size:16px'>{total_orders:,.0f}</span>",
                    x=0.5, y=0.5,
                    font_size=14,
                    font_color="#f0f6fc",  # Light annotation color
                    font_family="Inter",
                    showarrow=False,
                    align="center"
                )
            ]
        )
        
        st.plotly_chart(fig_pie_orders, use_container_width=True)
    
    # 3. Trends Over Time
    st.markdown("#### 📈 Price Range Sales Trends")
    
    # Add toggle switches for view mode and breakdown
    col_toggle1, col_toggle2, col_spacer = st.columns([1, 1, 2])
    with col_toggle1:
            view_mode = st.toggle(
                "📊 Show Percentage View",
                value=True,
                help="Toggle between absolute sales values and percentage of total sales by week"
            )
    with col_toggle2:
            listing_breakdown = st.toggle(
                "📋 Breakdown by Listing",
                value=False,
                help="Show price range percentages broken down by individual listings"
            )
    
    # Add helpful note for listing breakdown mode
    if listing_breakdown:
        st.caption("💡 **Tip:** Listing breakdown shows each listing-price range combination as a separate line, perfect for identifying which specific listings drive sales in each price tier.")
    
    # Add view mode indicator
    if listing_breakdown:
        st.info("📋 **View Mode:** Breakdown by Listing & Price Range - Shows how each listing performs across different price ranges")
        
        # Add listing selector for breakdown mode
        if LISTING_COL in filtered_df.columns:
            available_listings = sorted(filtered_df[LISTING_COL].dropna().unique())
            
            # Default to "Pattern Pants" if available, otherwise first listing
            default_listing = ["Pattern Pants"] if "Pattern Pants" in available_listings else [available_listings[0]] if available_listings else []
            
            st.markdown("**📋 Select Listings to Display:**")
            selected_listings = st.multiselect(
                "Choose specific listings for breakdown analysis",
                options=available_listings,
                default=default_listing,
                key="listing_breakdown_selector",
                help="Select which listings to show in the breakdown chart. Default shows Pattern Pants."
            )
            
            # Buttons section removed
            
            if not selected_listings:
                st.warning("⚠️ Please select at least one listing for breakdown analysis.")
                selected_listings = default_listing
        else:
            selected_listings = []
            st.warning(f"⚠️ No '{LISTING_COL}' column found for listing breakdown.")
    else:
        selected_listings = []  # Not needed for regular mode
    
    # Use cached weekly trends data - choose between regular or listing breakdown
    if listing_breakdown:
        # Use listing-based weekly trends
        weekly_trends_listing = calculate_weekly_trends_by_listing(filtered_df)
        if not weekly_trends_listing.empty and selected_listings:
            # Filter trends to only include selected listings
            current_trends = weekly_trends_listing[weekly_trends_listing[LISTING_COL].isin(selected_listings)].copy()
            
            if current_trends.empty:
                st.warning(f"⚠️ No data found for selected listings: {', '.join(selected_listings)}")
                current_trends = weekly_trends.copy()
                color_col = 'Applicable_Price_Range'
                chart_title_suffix = ' by Price Range (Fallback)'
            else:
                color_col = 'Listing_PriceRange'
                chart_title_suffix = f' by Selected Listings & Price Range ({len(selected_listings)} listings)'
        else:
            st.warning("⚠️ No listing data available for breakdown analysis")
            current_trends = weekly_trends.copy()
            color_col = 'Applicable_Price_Range'
            chart_title_suffix = ' by Price Range'
    else:
        # Use regular price range trends
        current_trends = weekly_trends.copy()
        color_col = 'Applicable_Price_Range'
        chart_title_suffix = ' by Price Range'
    
    if not current_trends.empty:
        current_trends['Month_Approx'] = current_trends[WEEK_AS_INT_COL].apply(week_to_month)
        # Ensure Week_Display uses the correct Saturday start dates from CUSTOM_WEEK_START_COL
        # Check if we already have the correct Week_Display from calculate_weekly_trends
        if 'Week_Display' not in current_trends.columns or current_trends['Week_Display'].isna().any():
            # Recreate with actual Saturday dates (company week structure)
            current_trends['Week_Display'] = current_trends.apply(lambda row: 
                f"W{int(row[WEEK_AS_INT_COL]):02d} ({row[CUSTOM_WEEK_START_COL].strftime('%Y-%m-%d')})" 
                if pd.notna(row[WEEK_AS_INT_COL]) and pd.notna(row[CUSTOM_WEEK_START_COL]) 
                else "W??", axis=1)
        # Sort by year and week for proper chronological order
        current_trends = current_trends.sort_values([CUSTOM_YEAR_COL, WEEK_AS_INT_COL])
        
        # Calculate percentage values if needed
        if view_mode:
            # Calculate total sales per week across all entries
            if listing_breakdown:
                # For listing breakdown, calculate total per week across all listings and price ranges
                weekly_totals = current_trends.groupby([CUSTOM_YEAR_COL, WEEK_AS_INT_COL, 'Week_Display'])[SALES_VALUE_GBP_COL].sum().reset_index()
            else:
                # For regular breakdown, calculate total per week across all price ranges
                weekly_totals = current_trends.groupby([CUSTOM_YEAR_COL, WEEK_AS_INT_COL, 'Week_Display'])[SALES_VALUE_GBP_COL].sum().reset_index()
            
            weekly_totals.rename(columns={SALES_VALUE_GBP_COL: 'Total_Sales_Week'}, inplace=True)
            # Merge totals back to main dataframe
            current_trends = current_trends.merge(
                weekly_totals[['Week_Display', 'Total_Sales_Week']], 
                on='Week_Display', 
                how='left'
            )
            # Calculate percentage
            current_trends['Sales_Percentage'] = (current_trends[SALES_VALUE_GBP_COL] / current_trends['Total_Sales_Week'] * 100).fillna(0)
            # Create percentage chart
            fig_trends = px.line(
                current_trends,
                x='Week_Display',
                y='Sales_Percentage',
                color=color_col,
                title=f'Weekly Sales{chart_title_suffix} - Percentage View (Saturday-Friday weeks)',
                labels={
                    'Week_Display': 'Week (Saturday Start Date)', 
                    'Sales_Percentage': 'Sales Percentage (%)',
                    color_col: 'Legend'
                }
            )
            # Update hover template for percentage view - with correct Saturday-Friday week dates
            fig_trends.update_traces(
                hovertemplate="<b>%{fullData.name}</b><br>" +
                              "<b>Week (Sat-Fri):</b> %{x}<br>" +
                              "<b>Percentage:</b> %{y:.1f}%<br>" +
                              "<extra></extra>"
            )
            y_axis_title = "Sales Percentage (%)"
            y_axis_range = [0, 100]
            y_tick_format = ".1f"
        else:
            # Add formatted sales values for better tooltip display
            current_trends['Sales_Formatted'] = current_trends[SALES_VALUE_GBP_COL].apply(lambda x: f"£{x:,.0f}")
            fig_trends = px.line(
                current_trends,
                x='Week_Display',
                y=SALES_VALUE_GBP_COL,
                color=color_col,
                title=f'Weekly Sales{chart_title_suffix} - Absolute Values (Saturday-Friday weeks)',
                labels={
                    'Week_Display': 'Week (Saturday Start Date)', 
                    SALES_VALUE_GBP_COL: 'Sales (£)',
                    color_col: 'Legend'
                }
            )
            # Update hover template with correct Saturday-Friday week information
            fig_trends.update_traces(
                hovertemplate="<b>%{fullData.name}</b><br>" +
                              "<b>Week (Sat-Fri):</b> %{x}<br>" +
                              "<b>Sales:</b> £%{y:,.0f}<br>" +
                              "<extra></extra>"
            )
            y_axis_title = "Sales (£)"
            y_axis_range = None
            y_tick_format = ",.0f"
        
        # Enable unified hover mode (no month annotations or separator lines)
        fig_trends.update_layout(
            height=520,
            xaxis_tickangle=45,
            hovermode='x unified',
            xaxis_title="Week (Saturday-Friday)",
            yaxis_title=y_axis_title,
            xaxis=dict(
                tickmode='linear',
                dtick=2,
                showgrid=True,
                gridcolor='rgba(128,128,128,0.2)',
                domain=[0, 1]
            ),
            yaxis=dict(
                range=y_axis_range,
                tickformat=y_tick_format,
                showgrid=True,
                gridcolor='rgba(128,128,128,0.2)',
            ),
            margin=dict(t=60, b=60, l=60, r=60),
            font=dict(family="Inter", color="#f0f6fc"),
            # Optimize legend for listing breakdown mode
            legend=dict(
                orientation="h" if listing_breakdown else "v",  # Horizontal legend for listing breakdown
                yanchor="bottom" if listing_breakdown else "top",
                y=1.02 if listing_breakdown else 1,
                xanchor="left" if listing_breakdown else "right",
                x=0 if listing_breakdown else 1,
                font=dict(size=10 if listing_breakdown else 12)  # Smaller text for listing mode
            ) if listing_breakdown else dict()
        )
        
        st.plotly_chart(fig_trends, use_container_width=True)
    else:
        st.warning(f"Weekly trend chart requires '{WEEK_AS_INT_COL}' and '{CUSTOM_YEAR_COL}' columns.")
        # Fallback to monthly trends if weekly data is not available
        filtered_df['Month'] = pd.to_datetime(filtered_df[DATE_COL]).dt.to_period('M')
        monthly_trends = filtered_df.groupby(['Month', 'Applicable_Price_Range'])[SALES_VALUE_GBP_COL].sum().reset_index()
        monthly_trends['Month_Str'] = monthly_trends['Month'].astype(str)
        
        fig_trends_monthly = px.line(
            monthly_trends,
            x='Month_Str',
            y=SALES_VALUE_GBP_COL,
            color='Applicable_Price_Range',
            title='Monthly Sales by Price Range (Fallback)',
            labels={'Month_Str': 'Month', SALES_VALUE_GBP_COL: 'Sales (£)'}
        )
        fig_trends_monthly.update_layout(height=500, xaxis_tickangle=45, hovermode='x unified')
        st.plotly_chart(fig_trends_monthly, use_container_width=True)
    
    # 4. Channel Breakdown
    st.markdown("#### 🏪 Sales by Channel and Price Range")
    
    # Use cached channel breakdown data
    # channel_breakdown = calculate_channel_breakdown(filtered_df)
    
    # Create modern grouped bar chart using go.Figure for better control
    fig_channel = go.Figure()
    
    # Use the same color scheme as pie charts for consistency
    price_range_color_map = {
        'Full Price Range': '#4FC3F7',
        'Reduced Range': '#66BB6A',
        'Stragglers': '#FFB74D',
        'Zero Stock': '#F06292'
    }
    
    # Get unique channels and price ranges
    unique_channels = channel_breakdown[SALES_CHANNEL_COL].unique()
    unique_ranges = channel_breakdown['Applicable_Price_Range'].unique()
    
    # Add bars for each price range
    for price_range in unique_ranges:
        range_data = channel_breakdown[channel_breakdown['Applicable_Price_Range'] == price_range]
        
        fig_channel.add_trace(go.Bar(
            name=price_range,
            x=range_data[SALES_CHANNEL_COL],
            y=range_data[SALES_VALUE_GBP_COL],
            marker=dict(
                color=price_range_color_map.get(price_range, '#9575CD'),
                line=dict(color='#21262d', width=1),
                opacity=0.85
            ),
            hoverinfo='none',  # Remove tooltip completely
            text=[f"£{val/1000:.0f}K" if val >= 1000 else f"£{val:.0f}" for val in range_data[SALES_VALUE_GBP_COL]],
            textposition='outside',
            textfont=dict(size=11, color='#f0f6fc', family='Inter')
        ))
    
    fig_channel.update_layout(
        xaxis=dict(
            title="Channel",
            title_font=dict(size=14, color="#f0f6fc", family="Inter"),
            tickfont=dict(size=12, color="#f0f6fc", family="Inter"),
            tickangle=45,
            showgrid=False,
            linecolor='rgba(128,128,128,0.3)'
        ),
        yaxis=dict(
            title="Sales (£)",
            title_font=dict(size=14, color="#f0f6fc", family="Inter"),
            tickfont=dict(size=12, color="#f0f6fc", family="Inter"),
            showgrid=True,
            gridcolor='rgba(128,128,128,0.2)',
            linecolor='rgba(128,128,128,0.3)',
            tickformat=',.0f'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=12, color="#f0f6fc", family="Inter"),
            bgcolor="rgba(13,17,23,0.8)",
            bordercolor="rgba(33,38,45,0.8)",
            borderwidth=1
        ),
        barmode='group',
        bargap=0.15,
        bargroupgap=0.1,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=550,
        margin=dict(t=100, b=80, l=60, r=60),
        font=dict(family="Inter", color="#f0f6fc"),
        hovermode=False  # Completely disable hover interactions
    )
    
    st.plotly_chart(fig_channel, use_container_width=True)
    
    # 5. Detailed Table
    st.markdown("#### 📋 Price Range Summary Table")
    
    # Format the summary table using cached data
    display_summary = range_summary.copy()
    display_summary[SALES_VALUE_GBP_COL] = display_summary[SALES_VALUE_GBP_COL].apply(format_currency_int)
    display_summary['AOV'] = display_summary['AOV'].apply(format_currency)
    display_summary['Sales_Pct'] = display_summary['Sales_Pct'].apply(lambda x: f"{x:.1f}%")
    
    display_summary = display_summary.rename(columns={
        'Applicable_Price_Range': 'Price Range',
        SALES_VALUE_GBP_COL: 'Total Sales',
        ORDER_QTY_COL_RAW: 'Total Orders',
        'Sales_Pct': 'Sales %'
    })
    
    st.dataframe(display_summary, use_container_width=True, hide_index=True)
    
    # 6. Listing Performance Analysis by Price Range
    st.markdown("#### 🏆 Top & Bottom Performing Listings by Price Range")
    
    # Use cached listing performance data
    if not listing_performance.empty:
        # Create tabs for each price range
        price_range_tabs = st.tabs([f"📊 {pr}" for pr in listing_performance['Applicable_Price_Range'].unique()])
        
        for i, price_range in enumerate(listing_performance['Applicable_Price_Range'].unique()):
            with price_range_tabs[i]:
                range_listings = listing_performance[listing_performance['Applicable_Price_Range'] == price_range].copy()
                
                if len(range_listings) > 0:
                    # Sort by sales value for top/bottom analysis
                    range_listings_sorted = range_listings.sort_values(SALES_VALUE_GBP_COL, ascending=False)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**🔥 Top 3 Listings - {price_range}**")
                        top_3 = range_listings_sorted.head(3).copy()
                        
                        if not top_3.empty:
                            # Format the data for display
                            top_3_display = top_3.copy()
                            top_3_display[SALES_VALUE_GBP_COL] = top_3_display[SALES_VALUE_GBP_COL].apply(format_currency_int)
                            top_3_display['Listing_AOV'] = top_3_display['Listing_AOV'].apply(format_currency)
                            top_3_display[ORDER_QTY_COL_RAW] = top_3_display[ORDER_QTY_COL_RAW].apply(lambda x: f"{x:,}")
                            
                            top_3_display = top_3_display.rename(columns={
                                LISTING_COL: 'Listing',
                                SALES_VALUE_GBP_COL: 'Total Sales',
                                ORDER_QTY_COL_RAW: 'Orders',
                                'Listing_AOV': 'AOV'
                            })
                            
                            # Add rank column
                            top_3_display.insert(0, 'Rank', [f"#{i+1}" for i in range(len(top_3_display))])
                            
                            st.dataframe(
                                top_3_display[['Rank', 'Listing', 'Total Sales', 'Orders', 'AOV']], 
                                use_container_width=True, 
                                hide_index=True
                            )
                            
                            # Show performance metrics
                            top_total_sales = top_3[SALES_VALUE_GBP_COL].sum()
                            range_total_sales = range_listings[SALES_VALUE_GBP_COL].sum()
                            top_3_contribution = (top_total_sales / range_total_sales * 100) if range_total_sales > 0 else 0
                            
                            st.success(f"""
                            **Top 3 Performance:**
                            - Combined Sales: {format_currency_int(top_total_sales)}
                            - Contribution to {price_range}: {top_3_contribution:.1f}%
                            - Listings Analyzed: {len(range_listings)} total
                            """)
                        else:
                            st.info("No listings found in this price range.")
                    
                    with col2:
                        st.markdown(f"**📉 Bottom 3 Listings - {price_range}**")
                        
                        # Only show bottom listings if we have more than 6 total (to avoid overlap with top 3)
                        if len(range_listings_sorted) > 6:
                            bottom_3 = range_listings_sorted.tail(3).copy()
                            # Reverse order to show worst first
                            bottom_3 = bottom_3.iloc[::-1]
                            
                            if not bottom_3.empty:
                                # Format the data for display
                                bottom_3_display = bottom_3.copy()
                                bottom_3_display[SALES_VALUE_GBP_COL] = bottom_3_display[SALES_VALUE_GBP_COL].apply(format_currency_int)
                                bottom_3_display['Listing_AOV'] = bottom_3_display['Listing_AOV'].apply(format_currency)
                                bottom_3_display[ORDER_QTY_COL_RAW] = bottom_3_display[ORDER_QTY_COL_RAW].apply(lambda x: f"{x:,}")
                                
                                bottom_3_display = bottom_3_display.rename(columns={
                                    LISTING_COL: 'Listing',
                                    SALES_VALUE_GBP_COL: 'Total Sales',
                                    ORDER_QTY_COL_RAW: 'Orders',
                                    'Listing_AOV': 'AOV'
                                })
                                
                                # Add rank column (showing worst first)
                                bottom_3_display.insert(0, 'Rank', [f"#{len(range_listings)-2+i}" for i in range(len(bottom_3_display))])
                                
                                st.dataframe(
                                    bottom_3_display[['Rank', 'Listing', 'Total Sales', 'Orders', 'AOV']], 
                                    use_container_width=True, 
                                    hide_index=True
                                )
                                
                                # Show performance metrics
                                bottom_total_sales = bottom_3[SALES_VALUE_GBP_COL].sum()
                                bottom_3_contribution = (bottom_total_sales / range_total_sales * 100) if range_total_sales > 0 else 0
                                
                                st.warning(f"""
                                **Bottom 3 Performance:**
                                - Combined Sales: {format_currency_int(bottom_total_sales)}
                                - Contribution to {price_range}: {bottom_3_contribution:.1f}%
                                - Improvement Opportunity: Consider price optimization
                                """)
                        else:
                            st.info(f"Only {len(range_listings)} listings in {price_range}. Need more than 6 listings for separate top/bottom analysis.")
                            
                else:
                    st.info(f"No listings found in {price_range} price range.")
    else:
        st.warning(f"Listing performance analysis requires '{LISTING_COL}' column in your data.")
        st.info("💡 **Tip:** Make sure your Google Sheet has a listing or SKU column for detailed listing analysis.")
    
    # 7. Product Performance Analysis by Price Range
    st.markdown("#### 🏷️ Top & Bottom Performing Products by Price Range")
    
    # Use cached product performance data
    if not product_performance.empty:
        # Create tabs for each price range
        product_range_tabs = st.tabs([f"🏷️ {pr}" for pr in product_performance['Applicable_Price_Range'].unique()])
        
        for i, price_range in enumerate(product_performance['Applicable_Price_Range'].unique()):
            with product_range_tabs[i]:
                range_products = product_performance[product_performance['Applicable_Price_Range'] == price_range].copy()
                
                if len(range_products) > 0:
                    # Sort by sales value for top/bottom analysis
                    range_products_sorted = range_products.sort_values(SALES_VALUE_GBP_COL, ascending=False)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**🔥 Top 5 Products - {price_range}**")
                        top_5 = range_products_sorted.head(5).copy()
                        
                        if not top_5.empty:
                            # Format the data for display
                            top_5_display = top_5.copy()
                            top_5_display[SALES_VALUE_GBP_COL] = top_5_display[SALES_VALUE_GBP_COL].apply(format_currency_int)
                            top_5_display['Product_AOV'] = top_5_display['Product_AOV'].apply(format_currency)
                            top_5_display[ORDER_QTY_COL_RAW] = top_5_display[ORDER_QTY_COL_RAW].apply(lambda x: f"{x:,}")
                            
                            top_5_display = top_5_display.rename(columns={
                                PRODUCT_COL: 'Product',
                                SALES_VALUE_GBP_COL: 'Total Sales',
                                ORDER_QTY_COL_RAW: 'Orders',
                                'Product_AOV': 'AOV'
                            })
                            
                            # Add rank column
                            top_5_display.insert(0, 'Rank', [f"#{i+1}" for i in range(len(top_5_display))])
                            
                            st.dataframe(
                                top_5_display[['Rank', 'Product', 'Total Sales', 'Orders', 'AOV']], 
                                use_container_width=True, 
                                hide_index=True
                            )
                            
                            # Show performance metrics
                            top_total_sales = top_5[SALES_VALUE_GBP_COL].sum()
                            range_total_sales = range_products[SALES_VALUE_GBP_COL].sum()
                            top_5_contribution = (top_total_sales / range_total_sales * 100) if range_total_sales > 0 else 0
                            
                            st.success(f"""
                            **Top 5 Performance:**
                            - Combined Sales: {format_currency_int(top_total_sales)}
                            - Contribution to {price_range}: {top_5_contribution:.1f}%
                            - Products Analyzed: {len(range_products)} total
                            """)
                        else:
                            st.info("No products found in this price range.")
                    
                    with col2:
                        st.markdown(f"**📉 Bottom 5 Products - {price_range}**")
                        
                        # Only show bottom products if we have more than 10 total (to avoid overlap with top 5)
                        if len(range_products_sorted) > 10:
                            bottom_5 = range_products_sorted.tail(5).copy()
                            # Reverse order to show worst first
                            bottom_5 = bottom_5.iloc[::-1]
                            
                            if not bottom_5.empty:
                                # Format the data for display
                                bottom_5_display = bottom_5.copy()
                                bottom_5_display[SALES_VALUE_GBP_COL] = bottom_5_display[SALES_VALUE_GBP_COL].apply(format_currency_int)
                                bottom_5_display['Product_AOV'] = bottom_5_display['Product_AOV'].apply(format_currency)
                                bottom_5_display[ORDER_QTY_COL_RAW] = bottom_5_display[ORDER_QTY_COL_RAW].apply(lambda x: f"{x:,}")
                                
                                bottom_5_display = bottom_5_display.rename(columns={
                                    PRODUCT_COL: 'Product',
                                    SALES_VALUE_GBP_COL: 'Total Sales',
                                    ORDER_QTY_COL_RAW: 'Orders',
                                    'Product_AOV': 'AOV'
                                })
                                
                                # Add rank column (showing worst first)
                                bottom_5_display.insert(0, 'Rank', [f"#{len(range_products)-4+i}" for i in range(len(bottom_5_display))])
                                
                                st.dataframe(
                                    bottom_5_display[['Rank', 'Product', 'Total Sales', 'Orders', 'AOV']], 
                                    use_container_width=True, 
                                    hide_index=True
                                )
                                
                                # Show performance metrics
                                bottom_total_sales = bottom_5[SALES_VALUE_GBP_COL].sum()
                                bottom_5_contribution = (bottom_total_sales / range_total_sales * 100) if range_total_sales > 0 else 0
                                
                                st.warning(f"""
                                **Bottom 5 Performance:**
                                - Combined Sales: {format_currency_int(bottom_total_sales)}
                                - Contribution to {price_range}: {bottom_5_contribution:.1f}%
                                - Improvement Opportunity: Consider price optimization
                                """)
                        else:
                            st.info(f"Only {len(range_products)} products in {price_range}. Need more than 10 products for separate top/bottom analysis.")
                            
                else:
                    st.info(f"No products found in {price_range} price range.")
    else:
        st.warning(f"Product performance analysis requires '{PRODUCT_COL}' column in your data.")
        st.info("💡 **Tip:** Make sure your Google Sheet has a product column for detailed product analysis.")
