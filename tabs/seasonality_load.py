# tabs/seasonality_load.py - Simplified Version
import streamlit as st
import pandas as pd
import numpy as np
import datetime
from datetime import timedelta

# Currency symbol mapping
CURRENCY_SYMBOLS = {
    'USD': '$',
    'GBP': '£',
    'EUR': '€',
    'CAD': 'CA$',
    'MXN': 'MX$',
    'AUD': 'A$',
    'JPY': '¥',
    'CNY': '¥',
    'INR': '₹',
    # Add more as needed
}

def get_currency_symbol(currency_code):
    """Return the currency symbol for a given currency code."""
    return CURRENCY_SYMBOLS.get(currency_code, currency_code)

from config import (
    SEASON_COL, DATE_COL, SKU_COL, ORDER_QTY_COL_RAW, CUSTOM_YEAR_COL,
    LISTING_COL, SALES_CHANNEL_COL, SALES_VALUE_GBP_COL, 
    SALES_VALUE_TRANS_CURRENCY_COL, ORIGINAL_CURRENCY_COL
)

@st.cache_data(ttl=300, show_spinner=False)  # Cache for 5 minutes
def get_seasonality_data(df, selected_sales_channels, selected_years, selected_listings, selected_seasons):
    """Cache heavy computations for seasonality analysis to prevent reprocessing on filter changes"""
    # Create a unique key for this data combination
    cache_key = f"{hash(tuple(selected_sales_channels))}_{hash(tuple(selected_years))}_{hash(tuple(selected_listings))}_{hash(tuple(selected_seasons))}"
    
    # Filter the dataframe based on selections
    filters = [
        df[SALES_CHANNEL_COL].isin(selected_sales_channels),
        df[CUSTOM_YEAR_COL].isin(selected_years),
        df[LISTING_COL].isin(selected_listings)
    ]
    
    if selected_seasons and "ALL" not in selected_seasons:
        filters.append(df[SEASON_COL].isin(selected_seasons))
    
    filtered_df = df[pd.concat(filters, axis=1).all(axis=1)].copy()
    
    if filtered_df.empty:
        return None, cache_key
    
    # Perform the heavy seasonality computations once and cache them
    season_data = filtered_df.groupby([LISTING_COL, CUSTOM_YEAR_COL]).agg({
        ORDER_QTY_COL_RAW: 'sum',
        SALES_VALUE_GBP_COL: 'sum'
    }).reset_index()
    
    # Calculate average price
    season_data['avg_price'] = season_data[SALES_VALUE_GBP_COL] / season_data[ORDER_QTY_COL_RAW]
    
    return season_data, cache_key


def display_tab(df, available_custom_years, current_custom_year=None, yoy_default_years=None):
    """Display seasonality load planning data with unit sales by year."""
    
    st.markdown("## Seasonality Load Planning")
    st.markdown("Analyze units sold across multiple years for specific season, date range, and channels.")

    # Check for required columns
    required_cols = {
        SEASON_COL, DATE_COL, SKU_COL, ORDER_QTY_COL_RAW, CUSTOM_YEAR_COL,
        LISTING_COL, SALES_CHANNEL_COL, SALES_VALUE_GBP_COL,
        SALES_VALUE_TRANS_CURRENCY_COL, ORIGINAL_CURRENCY_COL
    }
    missing_cols = required_cols.difference(df.columns)
    if missing_cols:
        st.error(f"Required columns missing from the input data: {missing_cols}.")
        return

    # --- Initial Data Processing and Type Conversion ---
    df_processed = df.copy()
    try:
        # Convert date columns
        df_processed[DATE_COL] = pd.to_datetime(df_processed[DATE_COL], errors='coerce')
        
        # Convert numeric columns
        num_cols = [ORDER_QTY_COL_RAW, CUSTOM_YEAR_COL]
        for col in num_cols:
            if col in df_processed.columns:
                df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce')
        
        # Ensure year is integer
        if CUSTOM_YEAR_COL in df_processed.columns:
            df_processed[CUSTOM_YEAR_COL] = df_processed[CUSTOM_YEAR_COL].astype('Int64')
        
        # Clean string columns
        str_cols = [SEASON_COL, SKU_COL, LISTING_COL, SALES_CHANNEL_COL]
        for col in str_cols:
            if col in df_processed.columns:
                df_processed[col] = df_processed[col].fillna('').astype(str).str.strip()
        
        # Drop rows with missing required values
        df_processed.dropna(subset=[DATE_COL, ORDER_QTY_COL_RAW, CUSTOM_YEAR_COL, SKU_COL, LISTING_COL], inplace=True)
        
        if df_processed.empty:
            st.warning("No data available after initial processing and NA removal.")
            return
    except Exception as e:
        st.error(f"Error preparing data types: {e}")
        return

    # --- Filters Section ---
    with st.container():
        st.markdown("### 🔍 Data Filters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Year Selection - Default to 2023, 2024, 2025 if available
            all_years = sorted(df_processed[CUSTOM_YEAR_COL].unique())
            default_years = [yr for yr in [2023, 2024, 2025] if yr in all_years]
            
            selected_years = st.multiselect(
                "Select Years to Compare",
                options=all_years,
                default=default_years,
                key="seasonality_years"
            )
            
            if not selected_years:
                selected_years = default_years if default_years else all_years
            
            # Season Selection
            available_seasons = sorted(df_processed[SEASON_COL].dropna().unique())
            season_options = [s for s in available_seasons if s and s.strip() and s.upper() != "ALL"]
            
            if not season_options:
                st.warning("No specific seasons found in the data.")
                selected_season = None
            else:
                selected_season = st.selectbox(
                    "Select Season",
                    options=season_options,
                    index=0,
                    key="seasonality_season"
                )
        
        with col2:
            # Sales Channel Selection
            available_channels = sorted(df_processed[SALES_CHANNEL_COL].dropna().unique())
            selected_channels = st.multiselect(
                "Sales Channels",
                options=available_channels,
                default=[],
                key="seasonality_channels",
                help="Select sales channels to filter data. Leave empty for all channels."
            )
            
            # Date Range Selection
            st.write("Month-Day Range")
            date_cols = st.columns(2)
            
            month_names = {m: datetime.date(2000, m, 1).strftime('%b') for m in range(1, 13)}
            
            with date_cols[0]:
                start_month = st.selectbox(
                    "Start Month",
                    options=list(month_names.keys()),
                    index=0,
                    format_func=month_names.get,
                    key="start_month"
                )
                start_day = st.number_input(
                    "Start Day",
                    min_value=1,
                    max_value=31,
                    value=1,
                    step=1,
                    key="start_day"
                )
            
            with date_cols[1]:
                end_month = st.selectbox(
                    "End Month",
                    options=list(month_names.keys()),
                    index=11,
                    format_func=month_names.get,
                    key="end_month"
                )
                end_day = st.number_input(
                    "End Day",
                    min_value=1,
                    max_value=31,
                    value=31,
                    step=1,
                    key="end_day"
                )
            
            # Validate day inputs
            if not (1 <= start_day <= 31 and 1 <= end_day <= 31):
                st.warning("Please select valid days (1-31).")
            
            start_month_day = (start_month, start_day)
            end_month_day = (end_month, end_day)

    # --- Apply Filters ---
    filtered_df = df_processed.copy()
    filter_applied = False
    
    # Filter by season
    if selected_season:
        filtered_df = filtered_df[filtered_df[SEASON_COL] == selected_season]
        filter_applied = True
        
        if filtered_df.empty:
            st.warning(f"No data found for Season: {selected_season}")
    
    # Filter by sales channel
    if selected_channels:
        filtered_df = filtered_df[filtered_df[SALES_CHANNEL_COL].isin(selected_channels)]
        filter_applied = True
        
        if filtered_df.empty:
            st.warning(f"No data found for selected Sales Channels")
    
    # Filter by month-day range
    if pd.api.types.is_datetime64_any_dtype(filtered_df[DATE_COL]):
        filtered_df['month_day'] = filtered_df[DATE_COL].apply(
            lambda d: (d.month, d.day) if pd.notna(d) else None
        )
        filtered_df.dropna(subset=['month_day'], inplace=True)
        
        # Apply month-day filter
        if start_month_day <= end_month_day:
            # Normal range (e.g., Mar 1 - Jun 30)
            mask = (filtered_df['month_day'] >= start_month_day) & (filtered_df['month_day'] <= end_month_day)
        else:
            # Inverted range that spans year boundary (e.g., Nov 1 - Feb 28)
            mask = (filtered_df['month_day'] >= start_month_day) | (filtered_df['month_day'] <= end_month_day)
        
        filtered_df = filtered_df[mask].copy()
        filter_applied = True
        
        # Clean up temporary column
        if 'month_day' in filtered_df.columns:
            filtered_df.drop(columns=['month_day'], inplace=True)
    
    # Display filter summary
    start_m_name = month_names.get(start_month_day[0], '?')
    end_m_name = month_names.get(end_month_day[0], '?')
    date_range_str = f"{start_m_name} {start_month_day[1]} - {end_m_name} {end_month_day[1]}"
    
    filter_summary = []
    if selected_season:
        filter_summary.append(f"Season: {selected_season}")
    if selected_channels:
        filter_summary.append(f"Channels: {', '.join(selected_channels)}")
    filter_summary.append(f"Date Range: {date_range_str}")
    
    st.markdown("### 📋 Applied Filters")
    st.markdown(", ".join(filter_summary))
    
    if filtered_df.empty and filter_applied:
        st.error("No data found matching all selected filters.")
        return

    # --- Display Data by Listings ---
    if not filtered_df.empty:
        # Group by listing with custom sorting order
        all_listings_unsorted = filtered_df[LISTING_COL].unique()
        
        # Define custom order for important listings
        preferred_order = [
            "Pattern Pants",
            "Patterned Pants",
            "Solid Pants",
            "Pattern Shorts",
            "Patterned Shorts",
            "Solid Shorts",
            "Patterned Polos",
            "Pattern Polos",
            "Solid Polos"
        ]
        
        # Create a sorted list with preferred items first, then the rest alphabetically
        all_listings = []
        
        # First add the preferred listings in the specified order (if they exist in the data)
        for listing in preferred_order:
            if listing in all_listings_unsorted:
                all_listings.append(listing)
        
        # Then add any remaining listings in alphabetical order
        remaining_listings = sorted([l for l in all_listings_unsorted if l not in preferred_order])
        all_listings.extend(remaining_listings)
        
        for listing in all_listings:
            listing_data = filtered_df[filtered_df[LISTING_COL] == listing].copy()
            
            # Skip if no data for this listing
            if listing_data.empty:
                continue
            
            # Determine the currency for this listing/channel selection
            # If we have multiple currencies, default to showing in GBP
            channel_currencies = listing_data[ORIGINAL_CURRENCY_COL].dropna().unique()
            
            if len(channel_currencies) == 1:
                # Single currency - use it
                currency_code = channel_currencies[0]
                value_column = SALES_VALUE_TRANS_CURRENCY_COL
                currency_symbol = get_currency_symbol(currency_code)
            else:
                # Multiple currencies - default to GBP
                currency_code = 'GBP'
                value_column = SALES_VALUE_GBP_COL
                currency_symbol = '£'
            
            # Store the currency info for later use
            listing_currency = {
                'code': currency_code,
                'symbol': currency_symbol
            }
                
            # Aggregate by SKU and year
            agg_data = listing_data.groupby([SKU_COL, CUSTOM_YEAR_COL]).agg({
                ORDER_QTY_COL_RAW: 'sum',
                value_column: 'sum'
            }).reset_index()
            
            # Calculate average price
            agg_data['Avg_Price'] = agg_data[value_column] / agg_data[ORDER_QTY_COL_RAW]
            agg_data['Avg_Price'] = agg_data['Avg_Price'].fillna(0).round(2)
            
            # Create pivot tables for units and average price
            units_pivot = agg_data.pivot(
                index=SKU_COL,
                columns=CUSTOM_YEAR_COL,
                values=ORDER_QTY_COL_RAW
            )
            
            price_pivot = agg_data.pivot(
                index=SKU_COL,
                columns=CUSTOM_YEAR_COL,
                values='Avg_Price'
            )
            
            # Combine units and price pivots
            pivot_data = units_pivot.copy()
            
            # Add price columns with a prefix
            for year_col in price_pivot.columns:
                pivot_data[f'Price_{year_col}'] = price_pivot[year_col]
            
            # Reset index to make SKU a regular column
            pivot_data = pivot_data.reset_index()
            
            # Fill NaN with zeros
            pivot_data = pivot_data.fillna(0)
            
            # Identify unit and price year columns
            unit_year_cols = [col for col in pivot_data.columns if col != SKU_COL and not str(col).startswith('Price_')]
            price_year_cols = [col for col in pivot_data.columns if str(col).startswith('Price_')]
            
            # Filter to selected years
            if selected_years:
                unit_year_cols = [col for col in unit_year_cols if col in selected_years]
                price_year_cols = [f'Price_{col}' for col in unit_year_cols]
            
            # Ensure we have at least some year columns
            if not unit_year_cols:
                st.warning(f"No data for selected years for {listing}.")
                continue
                
            # Reorder columns to put SKU first, then units and prices for each year
            display_cols = [SKU_COL]
            
            for year in sorted(unit_year_cols):
                display_cols.append(year)
                display_cols.append(f'Price_{year}')
            
            # Format column headers with year names
            renamed_cols = {
                SKU_COL: "Product SKU"
            }
            
            for year in unit_year_cols:
                renamed_cols[year] = f"Units {int(year)}"
                renamed_cols[f'Price_{year}'] = f"Avg {listing_currency['symbol']} {int(year)}"
            
            # Create a copy of the pivot data for our display
            final_df = pivot_data[display_cols].copy()
            final_df = final_df.rename(columns=renamed_cols)
            
            # Add display versions of the unit columns that include growth rates
            sorted_unit_cols = sorted([col for col in final_df.columns if "Units" in col], 
                                      key=lambda x: int(x.split(" ")[-1]))
            
            # Convert only numeric columns to integers and format prices
            for col in final_df.columns:
                if col != "Product SKU":
                    if "Units" in col:
                        final_df[col] = final_df[col].fillna(0).astype(int)
                    elif "Avg" in col:
                        final_df[col] = final_df[col].fillna(0).round(2)
            
            # Calculate growth rates between years for each SKU
            unit_cols = [col for col in final_df.columns if "Units" in col]
            price_cols = [col for col in final_df.columns if f"Avg {listing_currency['symbol']}" in col]
            sorted_unit_cols = sorted(unit_cols, key=lambda x: int(x.split(" ")[-1]))
            
            # Create growth rate dataframes (we won't add these to final_df)
            growth_rates = {}
            
            for i in range(1, len(sorted_unit_cols)):
                current_col = sorted_unit_cols[i]
                prev_col = sorted_unit_cols[i-1]
                current_year = current_col.split(" ")[-1]
                prev_year = prev_col.split(" ")[-1]
                growth_col = f"Growth_{prev_year}_{current_year}"
                
                # Calculate growth rates for each SKU
                growth_rates[growth_col] = pd.Series(index=final_df.index)
                
                for idx in final_df.index:
                    current_units = final_df.at[idx, current_col]
                    prev_units = final_df.at[idx, prev_col]
                    
                    if prev_units > 0:
                        growth_pct = ((current_units / prev_units) - 1) * 100
                        growth_rates[growth_col][idx] = growth_pct
                    else:
                        growth_rates[growth_col][idx] = None
            
            # Calculate unit totals and average prices
            unit_totals = {}
            price_weighted_totals = {}
            yoy_growth = {}  # Store YoY growth percentages
            
            # Make sure we have matching unit and price columns
            prev_year_total = None
            prev_year_price = None
            
            for i, unit_col in enumerate(sorted_unit_cols):
                total_units = final_df[unit_col].sum()
                unit_totals[unit_col] = total_units
                
                # Find the corresponding price column by year
                year = unit_col.split(" ")[-1]
                matching_price_cols = [col for col in price_cols if year in col]
                
                if matching_price_cols:
                    corresponding_price_col = matching_price_cols[0]
                    
                    # Calculate weighted average price (total revenue / total units)
                    total_revenue = (final_df[unit_col] * final_df[corresponding_price_col]).sum()
                    
                    if total_units > 0:
                        weighted_avg_price = total_revenue / total_units
                    else:
                        weighted_avg_price = 0
                        
                    price_weighted_totals[corresponding_price_col] = round(weighted_avg_price, 2)
                    
                    # Calculate YoY growth if we have a previous year to compare
                    if prev_year_total is not None and prev_year_total > 0:
                        yoy_percent = ((total_units - prev_year_total) / prev_year_total) * 100
                        yoy_growth[f"growth_{year}"] = round(yoy_percent, 1)
                        
                        # Calculate price change percentage
                        if prev_year_price is not None and prev_year_price > 0:
                            price_percent = ((weighted_avg_price - prev_year_price) / prev_year_price) * 100
                            yoy_growth[f"price_growth_{year}"] = round(price_percent, 1)
                    
                    # Store this year's values for next year's comparison
                    prev_year_total = total_units
                    prev_year_price = weighted_avg_price
                else:
                    # If no matching price column, set a default of 0
                    price_col_name = f"Avg {listing_currency['symbol']} {year}"
                    price_weighted_totals[price_col_name] = 0.0
            
            # Complete totals dictionary
            totals = {"Product SKU": "TOTAL"}
            totals.update(unit_totals)
            totals.update(price_weighted_totals)
            
            # Complete totals dictionary
            totals = {"Product SKU": "TOTAL"}
            totals.update(unit_totals)
            totals.update(price_weighted_totals)
            
            # Display header with listing name and totals
            st.markdown(f"### {listing}")
            
            # Create columns for year totals
            total_cols = st.columns(len(unit_cols))
            
            # Display totals in a highlighted section above the table
            with st.container():
                st.markdown("""
                <style>
                .total-box {
                    background-color: rgba(13, 17, 23, 0.9);  /* Match dark theme */
                    border-radius: 5px;
                    padding: 10px;
                    margin-bottom: 10px;
                }
                .total-title {
                    font-weight: bold;
                    color: #f0f6fc;  /* Light text for dark theme */
                }
                .total-value {
                    font-weight: bold;
                    font-size: 18px;
                }
                .stMetric {
                    width: 100%;
                }
                /* Make metric labels have consistent size */
                .stMetricLabel {
                    height: 1.5em;
                    overflow: hidden;
                    white-space: nowrap;
                    text-overflow: ellipsis;
                }
                .stColumnContainer {
                    column-gap: 0px;
                }
                </style>
                """, unsafe_allow_html=True)
                
                st.markdown('<div class="total-box">', unsafe_allow_html=True)
                st.markdown('<span class="total-title">Category Totals:</span>', unsafe_allow_html=True)
                
                cols = st.columns(len(unit_cols))
                for i, year_col in enumerate(unit_cols):
                    year = year_col.split(" ")[-1]
                    price_col_name = f"Avg {listing_currency['symbol']} {year}"
                    growth_key = f"growth_{year}"
                    price_growth_key = f"price_growth_{year}"
                    
                    with cols[i]:
                        # Display units with YoY growth delta if available
                        if growth_key in yoy_growth:
                            growth_val = yoy_growth[growth_key]
                            delta_text = f"{growth_val:+.1f}% vs prev year"
                            st.metric(f"{year}", f"{int(totals[year_col]):,} units", delta=delta_text)
                        else:
                            st.metric(f"{year}", f"{int(totals[year_col]):,} units", delta=None)
                        
                        # Display average price with YoY price change if available
                        if price_col_name in totals:
                            if price_growth_key in yoy_growth:
                                price_growth = yoy_growth[price_growth_key]
                                price_delta = f"{price_growth:+.1f}% vs prev year"
                                st.metric("Avg Price", f"{listing_currency['symbol']}{totals[price_col_name]}", delta=price_delta)
                            else:
                                st.metric("Avg Price", f"{listing_currency['symbol']}{totals[price_col_name]}", delta=None)
                        else:
                            st.metric("Avg Price", f"{listing_currency['symbol']}0.00", delta=None)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Display the table
            st.dataframe(
                final_df, 
                use_container_width=True, 
                column_config={
                    # Configure column formatting as needed
                    "Product SKU": st.column_config.TextColumn(
                        "Product SKU",
                        width="medium"
                    ),
                    **{col: st.column_config.NumberColumn(
                        format="%d",
                        width="small"
                    ) for col in final_df.columns if "Units" in col},
                    **{col: st.column_config.NumberColumn(
                        format=f"{listing_currency['symbol']}%.2f",
                        width="small"
                    ) for col in final_df.columns if "Avg" in col},
                },
                hide_index=True,
            )
            
            # Separator between listings
            st.markdown("---")
