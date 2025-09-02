import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_loader import load_ppc_data_from_gsheet


def display_tab():
    """Display PPC Analytics tab with country selection and key metrics."""
    
    st.title("🎯 PPC Analytics Dashboard")
    st.markdown("Analyze advertising performance across different markets.")
    
    # Country selection
    countries = ["All Marketplaces", "US", "UK", "CA", "MX", "DE", "ES", "IT", "FR"]
    country_names = {
        "All Marketplaces": "🌍 All Marketplaces",
        "US": "🇺🇸 United States",
        "UK": "🇬🇧 United Kingdom", 
        "CA": "🇨🇦 Canada",
        "MX": "🇲🇽 Mexico",
        "DE": "🇩🇪 Germany",
        "ES": "🇪🇸 Spain",
        "IT": "🇮🇹 Italy",
        "FR": "🇫🇷 France"
    }
    
    # Currency symbols for each country - for "All Marketplaces" we'll use mixed currencies
    currency_symbols = {
        "All Marketplaces": "Mixed",
        "US": "$",
        "UK": "£",
        "CA": "C$",
        "MX": "MX$",
        "DE": "€",
        "ES": "€",
        "IT": "€",
        "FR": "€"
    }
    
    # Layout with columns for country selection
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        default_country = "US"
        default_index = countries.index(default_country) if default_country in countries else 0
        selected_country = st.selectbox(
            "Select Country/Market:",
            countries,
            format_func=lambda x: country_names[x],
            index=default_index
        )
    
    # Load data for selected country or all countries
    with st.spinner(f"Loading PPC data for {country_names[selected_country]}..."):
        if selected_country == "All Marketplaces":
            # Load data from all countries and combine
            all_dataframes = []
            individual_countries = ["US", "UK", "CA", "MX", "DE", "ES", "IT", "FR"]
            
            for country in individual_countries:
                try:
                    country_df = load_ppc_data_from_gsheet(country)
                    if not country_df.empty:
                        # Add country column to identify the source
                        country_df['Country'] = country
                        all_dataframes.append(country_df)
                except Exception as e:
                    st.warning(f"Could not load data for {country}: {str(e)}")
                    continue
            
            if all_dataframes:
                df_ppc = pd.concat(all_dataframes, ignore_index=True)
                st.info(f"✅ Combined data from {len(all_dataframes)} marketplaces ({len(df_ppc)} total records)")
            else:
                df_ppc = pd.DataFrame()
        else:
            df_ppc = load_ppc_data_from_gsheet(selected_country)
    
    # Get currency symbol for selected country - for mixed currencies, don't use symbol in formatting
    currency_symbol = currency_symbols[selected_country]
    
    if df_ppc.empty:
        st.warning(f"No data available for {country_names[selected_country]}. Please check the worksheet name and data.")
        return
    
    # Check for date column - it might be empty or named differently
    date_col = None
    possible_date_cols = ['Date', 'date', 'DATE', '']
    
    for col in possible_date_cols:
        if col in df_ppc.columns and not df_ppc[col].isna().all():
            date_col = col
            break
    
    # Date range filter
    if date_col is not None:
        # Clean and convert date column
        df_ppc[date_col] = df_ppc[date_col].replace('', pd.NaT)
        df_ppc[date_col] = pd.to_datetime(df_ppc[date_col], errors='coerce')
        df_ppc = df_ppc.dropna(subset=[date_col])
        
        if not df_ppc.empty:
            # Calculate the last 30 days of available data
            max_date = df_ppc[date_col].max()
            min_date = df_ppc[date_col].min()
            # Default to last 30 days of available data, but ensure it doesn't go below min_date
            default_start_date = max(max_date - pd.Timedelta(days=29), min_date)
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Start Date",
                    value=default_start_date.date(),
                    min_value=min_date.date(),
                    max_value=max_date.date()
                )
            with col2:
                end_date = st.date_input(
                    "End Date", 
                    value=max_date.date(),
                    min_value=min_date.date(),
                    max_value=max_date.date()
                )
            
            # Filter data by date range
            df_filtered = df_ppc[
                (df_ppc[date_col] >= pd.Timestamp(start_date)) & 
                (df_ppc[date_col] <= pd.Timestamp(end_date))
            ].copy()
        else:
            df_filtered = df_ppc.copy()
    else:
        st.warning("Date column not found or is empty in the data. Showing all records without date filtering.")
        df_filtered = df_ppc.copy()
    
    if df_filtered.empty:
        st.warning("No data available for the selected date range.")
        return
    
    # Last completed week metrics (Saturday to Friday)
    st.markdown("---")
    st.subheader("📅 Last Completed Week Performance (Saturday - Friday)")
    
    # Calculate last completed week
    if date_col:
        # Use original dataframe for week calculations
        df_week_calc = df_ppc.dropna(subset=[date_col]).copy()
        
        if not df_week_calc.empty:
            # Find the most recent Friday
            today = pd.Timestamp.now()
            # Friday is weekday 4, calculate days since last Friday
            days_since_friday = (today.weekday() - 4) % 7
            if days_since_friday == 0 and today.hour < 23:  # If today is Friday but not end of day
                days_since_friday = 7
            most_recent_friday = today - pd.Timedelta(days=days_since_friday)
            
            # Calculate the Saturday-Friday week
            week_start = most_recent_friday - pd.Timedelta(days=6)  # Saturday (6 days before Friday)
            week_end = most_recent_friday
            
            # Filter data for last completed week
            last_week_data = df_week_calc[
                (df_week_calc[date_col].dt.date >= week_start.date()) & 
                (df_week_calc[date_col].dt.date <= week_end.date())
            ]
            
            week_start_str = week_start.strftime('%b %d')
            week_end_str = week_end.strftime('%b %d, %Y')
            st.caption(f"📆 **Week Period**: {week_start_str} - {week_end_str} (Saturday to Friday)")
            
            if not last_week_data.empty:
                week_cols = st.columns(8)  # Changed from 6 to 8 columns to accommodate ACOS and TACOS
                
                # Week Ad Spend
                if 'Ad Spend' in last_week_data.columns:
                    week_ad_spend = pd.to_numeric(last_week_data['Ad Spend'], errors='coerce').sum()
                    with week_cols[0]:
                        if currency_symbol == "Mixed":
                            st.metric("Week Ad Spend", f"{week_ad_spend:,.0f} (Mixed)", help="Total spend for last completed week across all marketplaces")
                        else:
                            st.metric("Week Ad Spend", f"{currency_symbol}{week_ad_spend:,.0f}", help="Total spend for last completed week")
                
                # Week Ad Sales
                if 'Ad Sales' in last_week_data.columns:
                    week_ad_sales = pd.to_numeric(last_week_data['Ad Sales'], errors='coerce').sum()
                    with week_cols[1]:
                        if currency_symbol == "Mixed":
                            st.metric("Week Ad Sales", f"{week_ad_sales:,.0f} (Mixed)", help="Total ad sales for last completed week across all marketplaces")
                        else:
                            st.metric("Week Ad Sales", f"{currency_symbol}{week_ad_sales:,.0f}", help="Total ad sales for last completed week")
                
                # Week Total Sales
                if 'Total Sales' in last_week_data.columns:
                    week_total_sales = pd.to_numeric(last_week_data['Total Sales'], errors='coerce').sum()
                    with week_cols[2]:
                        if currency_symbol == "Mixed":
                            st.metric("Week Total Sales", f"{week_total_sales:,.0f} (Mixed)", help="Total sales for last completed week across all marketplaces")
                        else:
                            st.metric("Week Total Sales", f"{currency_symbol}{week_total_sales:,.0f}", help="Total sales for last completed week")
                
                # Week Avg % Ad Sales
                if '% Ad Sales' in last_week_data.columns:
                    week_avg_ad_sales_pct = pd.to_numeric(last_week_data['% Ad Sales'], errors='coerce').mean()
                    with week_cols[3]:
                        st.metric("Week Avg % Ad Sales", f"{week_avg_ad_sales_pct:.1f}%" if not pd.isna(week_avg_ad_sales_pct) else "N/A", 
                                 help="Average % ad sales for last completed week")
                
                # Week Clicks
                if 'Clicks' in last_week_data.columns:
                    week_clicks = pd.to_numeric(last_week_data['Clicks'], errors='coerce').sum()
                    with week_cols[4]:
                        st.metric("Week Clicks", f"{week_clicks:,.0f}", help="Total clicks for last completed week")
                
                # Week Impressions
                if 'Impressions' in last_week_data.columns:
                    week_impressions = pd.to_numeric(last_week_data['Impressions'], errors='coerce').sum()
                    with week_cols[5]:
                        st.metric("Week Impressions", f"{week_impressions:,.0f}", help="Total impressions for last completed week")
                
                # Week Average ACOS
                if 'ACOS' in last_week_data.columns:
                    week_avg_acos = pd.to_numeric(last_week_data['ACOS'], errors='coerce').mean()
                    with week_cols[6]:
                        st.metric("Week Avg ACOS", f"{week_avg_acos:.1f}%" if not pd.isna(week_avg_acos) else "N/A",
                                 help="Average ACOS for last completed week")
                
                # Week Average TACOS
                if 'TACOS' in last_week_data.columns:
                    week_avg_tacos = pd.to_numeric(last_week_data['TACOS'], errors='coerce').mean()
                    with week_cols[7]:
                        st.metric("Week Avg TACOS", f"{week_avg_tacos:.1f}%" if not pd.isna(week_avg_tacos) else "N/A",
                                 help="Average TACOS for last completed week")
            else:
                st.warning(f"No data found for last completed week ({week_start_str} - {week_end_str})")
        else:
            st.warning("No valid date data found for week calculations")
    else:
        st.warning("Date column not available for week calculations")
    
    # Charts section
    st.markdown("---")
    st.subheader("📈 Performance Trends")
    
    # Create small line charts for each metric in a grid layout
    metrics_to_chart = [
        'ACOS', 'TACOS', 'CPC', 'Ads CTR', 'Ads CVR', 'CPA',
        'Ad Spend', 'Ad Sales', '% Ad Sales', 
        'Total Sales', 'Total Units Ordered', 'Sessions', 'Page Views', 
        'Impressions', 'Clicks'
    ]
    
    # Filter to only available metrics
    available_metrics = [metric for metric in metrics_to_chart if metric in df_filtered.columns]
    
    if date_col and available_metrics:
        # For "All Marketplaces", we need to aggregate data by date first
        if selected_country == "All Marketplaces":
            # Clean and convert numeric columns before aggregation
            df_clean = df_filtered.copy()
            
            # Convert all metric columns to numeric, handling errors gracefully
            for metric in available_metrics:
                if metric in df_clean.columns:
                    df_clean[metric] = pd.to_numeric(df_clean[metric], errors='coerce')
            
            # Group by date and sum/average the metrics appropriately
            try:
                # Define aggregation rules
                sum_metrics = [m for m in available_metrics if m in ['Ad Spend', 'Ad Sales', 'Total Sales', 'Sessions', 'Page Views', 'Impressions', 'Clicks', 'Total Units Ordered'] and m in df_clean.columns]
                mean_metrics = [m for m in available_metrics if m in ['ACOS', 'TACOS', 'CPC', '% Ad Sales', 'Ads CTR', 'Ads CVR', 'CPA'] and m in df_clean.columns]
                
                # Create aggregation dictionary
                agg_dict = {}
                if sum_metrics:
                    agg_dict.update({metric: 'sum' for metric in sum_metrics})
                if mean_metrics:
                    agg_dict.update({metric: 'mean' for metric in mean_metrics})
                
                if agg_dict:
                    df_chart = df_clean.groupby(date_col).agg(agg_dict).reset_index()
                else:
                    df_chart = df_clean.copy()
            except Exception as e:
                st.error(f"Error aggregating data: {str(e)}")
                st.info("Falling back to raw data display...")
                df_chart = df_filtered.copy()
        else:
            df_chart = df_filtered.copy()
        
        # Create charts in a 3x4 grid
        cols_per_row = 3
        rows = (len(available_metrics) + cols_per_row - 1) // cols_per_row
        
        for row in range(rows):
            chart_cols = st.columns(cols_per_row)
            
            for col_idx in range(cols_per_row):
                metric_idx = row * cols_per_row + col_idx
                
                if metric_idx < len(available_metrics):
                    metric = available_metrics[metric_idx]
                    
                    with chart_cols[col_idx]:
                        # Create smooth line chart with enhanced styling
                        fig = go.Figure()
                        
                        # Color coding based on metric type
                        if metric in ['Ad Spend', 'Ad Sales', '% Ad Sales']:
                            color = '#FF6B6B'  # Red for ad-related metrics
                            fill_color = 'rgba(255, 107, 107, 0.1)'
                        elif metric in ['Total Sales', 'Total Units Ordered']:
                            color = '#00D4AA'  # Emerald green for total sales metrics
                            fill_color = 'rgba(0, 212, 170, 0.1)'
                        elif metric in ['ACOS', 'TACOS', 'CPC']:
                            color = '#FFE066'  # Bright yellow for ratios and CPC
                            fill_color = 'rgba(255, 224, 102, 0.1)'
                        elif metric in ['Sessions', 'Clicks', 'Impressions', 'Page Views']:
                            color = '#9B59B6'  # Purple for traffic metrics
                            fill_color = 'rgba(155, 89, 182, 0.1)'
                        else:
                            color = '#3498DB'  # Bright blue for other metrics
                            fill_color = 'rgba(52, 152, 219, 0.1)'
                        
                        # Add the line trace with smooth curves and fill - single aggregated line
                        fig.add_trace(go.Scatter(
                            x=df_chart[date_col],
                            y=pd.to_numeric(df_chart[metric], errors='coerce'),
                            mode='lines',
                            name=metric,
                            line=dict(
                                color=color, 
                                width=3,
                                shape='spline',  # Smooth curves
                                smoothing=1.3
                            ),
                            fill='tozeroy',
                            fillcolor=fill_color,
                            hovertemplate=f'<b>{metric}</b><br>' +
                                        'Date: %{x}<br>' +
                                        'Value: %{y:,.1f}<br>' +
                                        '<extra></extra>'
                        ))
                        
                        # Enhanced layout with modern styling
                        fig.update_layout(
                            title=dict(
                                text=f"<b>{metric}</b>",
                                font=dict(size=16, color='white'),
                                x=0.5,
                                xanchor='center'
                            ),
                            height=280,
                            showlegend=False,
                            margin=dict(l=10, r=10, t=50, b=20),
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            xaxis=dict(
                                showgrid=True,
                                gridwidth=1,
                                gridcolor='rgba(255,255,255,0.1)',
                                showticklabels=True,
                                tickfont=dict(size=10, color='rgba(255,255,255,0.8)'),
                                showline=False,
                                zeroline=False
                            ),
                            yaxis=dict(
                                showgrid=True,
                                gridwidth=1,
                                gridcolor='rgba(255,255,255,0.1)',
                                tickfont=dict(size=10, color='rgba(255,255,255,0.8)'),
                                showline=False,
                                zeroline=False
                            ),
                            hoverlabel=dict(
                                bgcolor="rgba(0,0,0,0.8)",
                                bordercolor=color,
                                font_size=12,
                                font_color="white"
                            )
                        )
                        
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("📊 Charts unavailable: Date column not found or no metric data available")
    
    # Download button
    csv = df_filtered.to_csv(index=False)
    download_label = f"📥 Download {selected_country} PPC Data as CSV" if selected_country != "All Marketplaces" else "📥 Download All Marketplaces PPC Data as CSV"
    filename = f"ppc_data_{selected_country}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv" if selected_country != "All Marketplaces" else f"ppc_data_all_marketplaces_{pd.Timestamp.now().strftime('%Y%m%d')}.csv"
    
    st.download_button(
        label=download_label,
        data=csv,
        file_name=filename,
        mime="text/csv"
    )
