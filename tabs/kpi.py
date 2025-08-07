# tabs/kpi.py
import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from utils import format_currency, format_currency_int, get_custom_week_date_range, get_current_custom_week, get_daily_target_actual, get_weekly_target_actual, calculate_variance
from config import (
    CUSTOM_YEAR_COL, WEEK_AS_INT_COL, SALES_VALUE_GBP_COL, ORDER_QTY_COL_RAW,
    CUSTOM_WEEK_START_COL, CUSTOM_WEEK_END_COL
)

def display_tab(df, available_years, current_year, df_targets=None):
    """Displays the KPI tab with modern styling and target performance cards."""
    
    # =============================================================================
    # Target Performance Cards
    # =============================================================================
    
    if df_targets is not None and not df_targets.empty:
        st.markdown("### 🎯 Target Performance (Amazon Marketplaces Only)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Last completed week target vs actual
            today = datetime.date.today()
            # Get the start of last completed week (assuming we want the week before current)
            days_since_saturday = (today.weekday() + 2) % 7  # Convert to Saturday=0 system
            last_week_end = today - datetime.timedelta(days=days_since_saturday + 1)  # Last Friday
            last_week_start = last_week_end - datetime.timedelta(days=6)  # Previous Saturday
            
            week_target, week_actual = get_weekly_target_actual(df, df_targets, last_week_start, last_week_end)
            week_var_pct, week_var_amt = calculate_variance(week_target, week_actual)
            
            # Color based on performance
            week_color = "#22c55e" if week_var_pct >= 0 else "#ef4444"
            week_icon = "🟢" if week_var_pct >= 0 else "🔴"
            
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
                padding: 1.5rem;
                border-radius: 12px;
                border: 1px solid #475569;
                margin-bottom: 1rem;
            ">
                <h4 style="color: #f1f5f9; margin: 0 0 1rem 0; display: flex; align-items: center;">
                    📅 Last Week Complete
                </h4>
                <p style="color: #94a3b8; margin: 0 0 0.5rem 0; font-size: 0.9rem;">
                    {last_week_start.strftime('%d %b')} - {last_week_end.strftime('%d %b %Y')}
                </p>
                <div style="display: flex; justify-content: space-between; margin-bottom: 1rem;">
                    <div>
                        <p style="color: #94a3b8; margin: 0; font-size: 0.8rem;">Target</p>
                        <p style="color: #f1f5f9; margin: 0; font-size: 1.2rem; font-weight: 600;">
                            {format_currency_int(week_target)}
                        </p>
                    </div>
                    <div>
                        <p style="color: #94a3b8; margin: 0; font-size: 0.8rem;">Actual</p>
                        <p style="color: #f1f5f9; margin: 0; font-size: 1.2rem; font-weight: 600;">
                            {format_currency_int(week_actual)}
                        </p>
                    </div>
                </div>
                <p style="color: {week_color}; margin: 0; font-weight: 600;">
                    {week_icon} {'+' if week_var_pct >= 0 else ''}{week_var_pct:.1f}% ({'+' if week_var_amt >= 0 else ''}{format_currency_int(week_var_amt)})
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Yesterday's target vs actual
            yesterday = today - datetime.timedelta(days=1)
            daily_target, daily_actual = get_daily_target_actual(df, df_targets, yesterday)
            daily_var_pct, daily_var_amt = calculate_variance(daily_target, daily_actual)
            
            # Color based on performance
            daily_color = "#22c55e" if daily_var_pct >= 0 else "#ef4444"
            daily_icon = "🟢" if daily_var_pct >= 0 else "🔴"
            
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
                padding: 1.5rem;
                border-radius: 12px;
                border: 1px solid #475569;
                margin-bottom: 1rem;
            ">
                <h4 style="color: #f1f5f9; margin: 0 0 1rem 0; display: flex; align-items: center;">
                    📈 Yesterday
                </h4>
                <p style="color: #94a3b8; margin: 0 0 0.5rem 0; font-size: 0.9rem;">
                    {yesterday.strftime('%d %b %Y')}
                </p>
                <div style="display: flex; justify-content: space-between; margin-bottom: 1rem;">
                    <div>
                        <p style="color: #94a3b8; margin: 0; font-size: 0.8rem;">Target</p>
                        <p style="color: #f1f5f9; margin: 0; font-size: 1.2rem; font-weight: 600;">
                            {format_currency_int(daily_target)}
                        </p>
                    </div>
                    <div>
                        <p style="color: #94a3b8; margin: 0; font-size: 0.8rem;">Actual</p>
                        <p style="color: #f1f5f9; margin: 0; font-size: 1.2rem; font-weight: 600;">
                            {format_currency_int(daily_actual)}
                        </p>
                    </div>
                </div>
                <p style="color: {daily_color}; margin: 0; font-weight: 600;">
                    {daily_icon} {'+' if daily_var_pct >= 0 else ''}{daily_var_pct:.1f}% ({'+' if daily_var_amt >= 0 else ''}{format_currency_int(daily_var_amt)})
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    else:
        st.info("💡 Target data not available. Add a 'TARGETS' sheet to enable target vs actual analysis.")
    
    # Enhanced filters section
    with st.expander("🔧 KPI Filters", expanded=True):
        today = datetime.date.today()
        selected_week = None
        available_weeks_in_current_year = []

        if CUSTOM_YEAR_COL not in df.columns or WEEK_AS_INT_COL not in df.columns:
            st.error(f"Missing '{CUSTOM_YEAR_COL}' or '{WEEK_AS_INT_COL}' for KPI calculations.")
        else:
                # Ensure Week column is numeric before filtering/sorting
                df[WEEK_AS_INT_COL] = pd.to_numeric(df[WEEK_AS_INT_COL], errors='coerce').astype('Int64')
                current_year_weeks = df[df[CUSTOM_YEAR_COL] == current_year][WEEK_AS_INT_COL].dropna()

                if not current_year_weeks.empty:
                    available_weeks_in_current_year = sorted(current_year_weeks.unique())
                else:
                    available_weeks_in_current_year = []

                # Determine the default week - prioritize current week if available
                current_week_number = get_current_custom_week(current_year)
                
                # Check if current week has data, otherwise fall back to last completed week
                default_week = None
                if current_week_number in available_weeks_in_current_year:
                    default_week = current_week_number
                else:
                    # Fallback to last completed week logic
                    full_weeks = []
                    last_available_week = None
                    
                    if available_weeks_in_current_year:
                         last_available_week = available_weeks_in_current_year[-1]
                         for wk in available_weeks_in_current_year:
                            if pd.notna(wk):
                                try:
                                    wk_int = int(wk)
                                    week_start_dt, week_end_dt = get_custom_week_date_range(current_year, wk_int)
                                    # Check if the week has completed
                                    if week_end_dt and week_end_dt < today:
                                        full_weeks.append(wk_int)
                                except (ValueError, TypeError):
                                    continue # Skip if week number is invalid
                    
                    # Set default: last full week, or last available week if no full weeks yet, or 1 if no weeks
                    default_week = full_weeks[-1] if full_weeks else (last_available_week if last_available_week is not None else 1)

                if available_weeks_in_current_year:
                    selected_week = st.selectbox(
                        "Select Week for KPI Calculation",
                        options=available_weeks_in_current_year,
                        index=available_weeks_in_current_year.index(default_week) if default_week in available_weeks_in_current_year else 0,
                        key="kpi_week",
                        help="Select the week to calculate KPIs for. Defaults to the current week if data is available, otherwise shows the last completed week."
                    )

                    # Display selected week's date range
                    if pd.notna(selected_week):
                         try:
                             selected_week_int_info = int(selected_week)
                             week_start_custom, week_end_custom = get_custom_week_date_range(current_year, selected_week_int_info)
                             if week_start_custom and week_end_custom:
                                 st.info(f"Selected Week {selected_week_int_info}: {week_start_custom.strftime('%d %b')} - {week_end_custom.strftime('%d %b, %Y')}")
                             else:
                                 st.warning(f"Could not determine date range for Week {selected_week_int_info}, Year {current_year}.")
                         except (ValueError, TypeError):
                             st.warning(f"Invalid week selected: {selected_week}")
                             selected_week = None # Reset selection if invalid
                    else:
                        selected_week = None # Handles potential NaN/None selection if options are weird
                else:
                    st.warning(f"No week data available for custom year {current_year}")
                    selected_week = None

    # --- KPI Calculation and Display ---
    if selected_week is not None and pd.notna(selected_week):
        try:
            selected_week_int = int(selected_week)

            # Filter data for the specific week across *all* years available in the dataframe for comparison
            kpi_data_all_years = df[df[WEEK_AS_INT_COL] == selected_week_int].copy()

            if kpi_data_all_years.empty:
                st.info(f"No sales data found for Week {selected_week_int} across any year to calculate KPIs.")
            else:
                # Ensure required columns are numeric
                kpi_data_all_years[SALES_VALUE_GBP_COL] = pd.to_numeric(kpi_data_all_years[SALES_VALUE_GBP_COL], errors='coerce')

                # Calculate Revenue Summary per Year for the selected week
                revenue_summary = kpi_data_all_years.groupby(CUSTOM_YEAR_COL)[SALES_VALUE_GBP_COL].sum()

                # Calculate Units Summary per Year (optional)
                units_summary = None
                if ORDER_QTY_COL_RAW in kpi_data_all_years.columns:
                    kpi_data_all_years[ORDER_QTY_COL_RAW] = pd.to_numeric(kpi_data_all_years[ORDER_QTY_COL_RAW], errors='coerce')
                    units_summary = kpi_data_all_years.groupby(CUSTOM_YEAR_COL)[ORDER_QTY_COL_RAW].sum().fillna(0)
                else:
                    st.info(f"Column '{ORDER_QTY_COL_RAW}' not found, units and AOV KPIs will not be shown.")

                # Get all years for comparison
                all_custom_years_in_df = sorted(pd.to_numeric(df[CUSTOM_YEAR_COL], errors='coerce').dropna().unique().astype(int))
                
                # === ENHANCED METRICS SECTION ===
                st.markdown("### 📊 Week Performance Metrics")
                
                # Create enhanced metric cards
                kpi_cols = st.columns(len(all_custom_years_in_df))
                chart_data = {'years': [], 'revenue': [], 'units': [], 'aov': []}
                
                # Store previous year's values for delta calculation
                prev_rev = 0
                prev_units = 0

                for idx, year in enumerate(all_custom_years_in_df):
                    with kpi_cols[idx]:
                        # Get current year's values for the selected week
                        revenue = revenue_summary.get(year, 0)
                        total_units = units_summary.get(year, 0) if units_summary is not None else 0
                        aov = revenue / total_units if total_units != 0 else 0
                        
                        # Store data for charts
                        chart_data['years'].append(str(year))
                        chart_data['revenue'].append(revenue)
                        chart_data['units'].append(total_units)
                        chart_data['aov'].append(aov)

                        # Enhanced Year Header
                        st.markdown(f"""
                        <div style="
                            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
                            color: white;
                            padding: 0.75rem;
                            border-radius: 8px;
                            text-align: center;
                            margin-bottom: 1rem;
                            font-weight: bold;
                            font-size: 1.1rem;
                        ">
                            📅 {year}
                        </div>
                        """, unsafe_allow_html=True)

                        # --- Revenue Metric ---
                        numeric_delta_rev = None
                        delta_rev_str = None
                        delta_rev_color = "off"

                        if idx > 0: # Can only calculate delta if not the first year
                            if prev_rev != 0 or revenue != 0:
                                numeric_delta_rev = revenue - prev_rev
                                delta_rev_str = f"{int(round(numeric_delta_rev)):,}"
                                delta_rev_color = "normal"

                        st.metric(
                            label="💰 Revenue",
                            value=format_currency_int(revenue),
                            delta=delta_rev_str,
                            delta_color=delta_rev_color
                        )

                        # --- Units Metric ---
                        if units_summary is not None:
                            delta_units_str = None
                            delta_units_color = "off"

                            if idx > 0:
                                if prev_units != 0:
                                    delta_units_percent = ((total_units - prev_units) / prev_units) * 100
                                    delta_units_str = f"{delta_units_percent:.1f}%"
                                    delta_units_color = "normal"
                                elif total_units != 0:
                                    delta_units_str = "+Units"
                                    delta_units_color = "normal"

                            st.metric(
                                label="📦 Units Sold",
                                value=f"{int(total_units):,}" if pd.notna(total_units) else "N/A",
                                delta=delta_units_str,
                                delta_color=delta_units_color
                            )

                            # --- AOV Metric ---
                            delta_aov_str = None
                            delta_aov_color = "off"

                            if idx > 0:
                                prev_aov = prev_rev / prev_units if prev_units != 0 else 0
                                if prev_aov != 0:
                                    delta_aov_percent = ((aov - prev_aov) / prev_aov) * 100
                                    delta_aov_str = f"{delta_aov_percent:.1f}%"
                                    delta_aov_color = "normal"
                                elif aov != 0:
                                    delta_aov_str = "+AOV"
                                    delta_aov_color = "normal"

                            st.metric(
                                label="🛒 Avg Order Value",
                                value=format_currency(aov),
                                delta=delta_aov_str,
                                delta_color=delta_aov_color
                            )

                        # Update previous values for the next iteration's delta calculation
                        prev_rev = revenue
                        prev_units = total_units

                # === YEAR-TO-DATE REVENUE COMPARISON ===
                st.markdown("---")
                st.markdown("### 📈 Year-to-Date Revenue Comparison")
                st.markdown("""
                <p style="color: #64748b; margin-bottom: 1.5rem;">
                    Compare current year revenue from beginning of year to current week vs same period in previous years
                </p>
                """, unsafe_allow_html=True)
                
                # Calculate YTD revenue for comparison years (2023, 2024, 2025)
                current_week_int = int(selected_week)
                comparison_years = [2023, 2024, 2025]
                ytd_data = {}
                
                for comp_year in comparison_years:
                    if comp_year in all_custom_years_in_df:
                        # Filter data from week 1 to current selected week for this year
                        ytd_filter = (df[CUSTOM_YEAR_COL] == comp_year) & (df[WEEK_AS_INT_COL] <= current_week_int)
                        ytd_revenue = df[ytd_filter][SALES_VALUE_GBP_COL].sum()
                        ytd_data[comp_year] = ytd_revenue
                
                # Display YTD comparison metrics
                if len(ytd_data) >= 2:
                    ytd_cols = st.columns(len(ytd_data))
                    
                    for idx, (year, ytd_revenue) in enumerate(ytd_data.items()):
                        with ytd_cols[idx]:
                            # Calculate delta vs previous year
                            delta_str = None
                            delta_color = "off"
                            
                            if idx > 0:
                                prev_year = list(ytd_data.keys())[idx-1]
                                prev_ytd = ytd_data[prev_year]
                                
                                if prev_ytd > 0:
                                    delta_amount = ytd_revenue - prev_ytd
                                    delta_percent = (delta_amount / prev_ytd) * 100
                                    delta_str = f"{delta_percent:+.1f}% (£{delta_amount:,.0f})"
                                    delta_color = "normal"
                            
                            # Year label with styling
                            if year == 2025:
                                year_label = f"🎯 {year} YTD"
                                help_text = f"Revenue from Week 1 to Week {current_week_int} in {year}"
                            else:
                                year_label = f"📊 {year} YTD"
                                help_text = f"Revenue from Week 1 to Week {current_week_int} in {year}"
                            
                            st.metric(
                                label=year_label,
                                value=f"£{ytd_revenue/1000000:.1f}M" if ytd_revenue > 1000000 else f"£{ytd_revenue/1000:.0f}K",
                                delta=delta_str,
                                delta_color=delta_color,
                                help=help_text
                            )
                else:
                    st.info("Need at least 2 years of data to show YTD comparison")

                # === ENHANCED CHARTS SECTION ===
                if len(all_custom_years_in_df) > 1:
                    st.markdown("---")
                    st.markdown("### 📈 Year-over-Year Comparison Charts")
                    
                    # Create two columns for charts
                    chart_col1, chart_col2 = st.columns(2)
                    
                    with chart_col1:
                        # Revenue Comparison Bar Chart
                        fig_revenue = go.Figure(data=[
                            go.Bar(
                                x=chart_data['years'],
                                y=chart_data['revenue'],
                                name='Revenue',
                                marker_color=['#3b82f6', '#8b5cf6', '#06d6a0', '#f59e0b'][:len(chart_data['years'])],
                                text=[format_currency_int(r) for r in chart_data['revenue']],
                                textposition='auto',
                            )
                        ])
                        
                        fig_revenue.update_layout(
                            title=f"💰 Revenue Comparison - Week {selected_week_int}",
                            xaxis_title="Year",
                            yaxis_title="Revenue (£)",
                            showlegend=False,
                            height=400,
                            plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)",
                            xaxis=dict(gridcolor="rgba(128,128,128,0.2)", linecolor="rgba(128,128,128,0.3)"),
                            yaxis=dict(gridcolor="rgba(128,128,128,0.2)", linecolor="rgba(128,128,128,0.3)")
                        )
                        
                        st.plotly_chart(fig_revenue, use_container_width=True)
                    
                    with chart_col2:
                        if units_summary is not None:
                            # Units & AOV Dual Axis Chart
                            fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
                            
                            # Units bar chart
                            fig_dual.add_trace(
                                go.Bar(
                                    x=chart_data['years'],
                                    y=chart_data['units'],
                                    name='Units Sold',
                                    marker_color='#06d6a0',
                                    opacity=0.7
                                ),
                                secondary_y=False,
                            )
                            
                            # AOV line chart
                            fig_dual.add_trace(
                                go.Scatter(
                                    x=chart_data['years'],
                                    y=chart_data['aov'],
                                    name='AOV',
                                    mode='lines+markers',
                                    line=dict(color='#ef4444', width=3),
                                    marker=dict(size=8)
                                ),
                                secondary_y=True,
                            )
                            
                            fig_dual.update_xaxes(title_text="Year")
                            fig_dual.update_yaxes(title_text="📦 Units Sold", secondary_y=False)
                            fig_dual.update_yaxes(title_text="🛒 AOV (£)", secondary_y=True)
                            
                            fig_dual.update_layout(
                                title=f"📦 Units vs 🛒 AOV - Week {selected_week_int}",
                                height=400,
                                plot_bgcolor="rgba(0,0,0,0)",
                                paper_bgcolor="rgba(0,0,0,0)",
                                xaxis=dict(gridcolor="rgba(128,128,128,0.2)", linecolor="rgba(128,128,128,0.3)"),
                                yaxis=dict(gridcolor="rgba(128,128,128,0.2)", linecolor="rgba(128,128,128,0.3)"),
                                yaxis2=dict(gridcolor="rgba(128,128,128,0.2)", linecolor="rgba(128,128,128,0.3)")
                            )
                            
                            st.plotly_chart(fig_dual, use_container_width=True)
                
                # === WEEKLY TREND CONTEXT ===
                st.markdown("---")
                st.markdown("### 🔍 Weekly Context Analysis")
                
                # Show performance context for the selected week across all available weeks
                context_col1, context_col2 = st.columns(2)
                
                with context_col1:
                    # Current year weekly performance trend
                    current_year_data = df[df[CUSTOM_YEAR_COL] == current_year].copy()
                    if not current_year_data.empty:
                        weekly_revenue = current_year_data.groupby(WEEK_AS_INT_COL)[SALES_VALUE_GBP_COL].sum().reset_index()
                        
                        fig_trend = go.Figure()
                        fig_trend.add_trace(go.Scatter(
                            x=weekly_revenue[WEEK_AS_INT_COL],
                            y=weekly_revenue[SALES_VALUE_GBP_COL],
                            mode='lines+markers',
                            name=f'{current_year} Weekly Revenue',
                            line=dict(color='#3b82f6', width=2),
                            marker=dict(size=6)
                        ))
                        
                        # Highlight selected week
                        if selected_week_int in weekly_revenue[WEEK_AS_INT_COL].values:
                            selected_revenue = weekly_revenue[weekly_revenue[WEEK_AS_INT_COL] == selected_week_int][SALES_VALUE_GBP_COL].iloc[0]
                            fig_trend.add_trace(go.Scatter(
                                x=[selected_week_int],
                                y=[selected_revenue],
                                mode='markers',
                                name=f'Week {selected_week_int}',
                                marker=dict(color='#ef4444', size=12, symbol='diamond')
                            ))
                        
                        fig_trend.update_layout(
                            title=f"📊 {current_year} Weekly Revenue Trend",
                            xaxis_title="Week Number",
                            yaxis_title="Revenue (£)",
                            height=350,
                            plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)",
                            xaxis=dict(gridcolor="rgba(128,128,128,0.2)", linecolor="rgba(128,128,128,0.3)"),
                            yaxis=dict(gridcolor="rgba(128,128,128,0.2)", linecolor="rgba(128,128,128,0.3)")
                        )
                        
                        st.plotly_chart(fig_trend, use_container_width=True)
                
                with context_col2:
                    # Performance summary table
                    st.markdown("#### 📋 Week Performance Summary")
                    
                    summary_data = []
                    for year in all_custom_years_in_df:
                        rev = chart_data['revenue'][chart_data['years'].index(str(year))]
                        units = chart_data['units'][chart_data['years'].index(str(year))]
                        aov_val = chart_data['aov'][chart_data['years'].index(str(year))]
                        
                        summary_data.append({
                            'Year': year,
                            'Revenue': format_currency_int(rev),
                            'Units': f"{int(units):,}",
                            'AOV': format_currency(aov_val)
                        })
                    
                    summary_df = pd.DataFrame(summary_data)
                    
                    # Style the dataframe
                    st.dataframe(
                        summary_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Year": st.column_config.NumberColumn("📅 Year", format="%d"),
                            "Revenue": st.column_config.TextColumn("💰 Revenue"),
                            "Units": st.column_config.TextColumn("📦 Units"),
                            "AOV": st.column_config.TextColumn("🛒 AOV")
                        }
                    )

        except (ValueError, TypeError):
            st.error(f"Invalid week number encountered: {selected_week}. Cannot calculate KPIs.")
    elif selected_week is None and available_weeks_in_current_year: # Check if selection is None but options existed
        st.info("Select a valid week from the filters above to view KPIs.")
    # No message needed if available_weeks_in_current_year is empty, warning already shown
    
    # === SALES PATTERNS SECTION ===
    st.markdown("---")
    create_sales_patterns_section(df)


def create_sales_patterns_section(df):
    """Create the sales patterns day-of-week analysis section."""
    from config import DATE_COL, SALES_VALUE_GBP_COL, ORDER_QTY_COL_RAW, CUSTOM_YEAR_COL
    import plotly.express as px
    import plotly.graph_objects as go
    
    st.markdown("### 📅 Sales Patterns - Day of Week Analysis")
    
    # Simple metric selector
    col1, col2 = st.columns([1, 3])
    with col1:
        metric_type = st.selectbox(
            "📊 Select Metric",
            options=["Average Revenue", "Average Units Ordered", "Average Order Value"],
            index=0,
            key="kpi_patterns_metric"
        )
    
    # Prepare data
    df_analysis = df.copy()
    
    # Ensure date column is datetime
    if DATE_COL in df_analysis.columns:
        df_analysis[DATE_COL] = pd.to_datetime(df_analysis[DATE_COL], errors='coerce')
        df_analysis = df_analysis.dropna(subset=[DATE_COL])
    else:
        st.error(f"Date column '{DATE_COL}' not found in data.")
        return
    
    # Add day of week to dataframe
    df_analysis['day_of_week'] = df_analysis[DATE_COL].dt.day_name()
    df_analysis['day_num'] = df_analysis[DATE_COL].dt.dayofweek  # For proper ordering
    
    # Define day order
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Get available years
    available_years = sorted(df_analysis[CUSTOM_YEAR_COL].unique())
    
    # Calculate metrics for each year
    yearly_stats = []
    
    for year in available_years:
        year_data = df_analysis[df_analysis[CUSTOM_YEAR_COL] == year].copy()
        
        if metric_type == "Average Revenue":
            # Group by day of week and date, then calculate daily totals, then average
            daily_totals = year_data.groupby([year_data[DATE_COL].dt.date, 'day_of_week'])[SALES_VALUE_GBP_COL].sum().reset_index()
            daily_totals.columns = ['date', 'day_of_week', 'daily_revenue']
            
            daily_stats = daily_totals.groupby('day_of_week')['daily_revenue'].mean().reset_index()
            daily_stats.columns = ['day_of_week', 'avg_value']
            
            y_label = "Average Daily Revenue (£)"
            title = "Average Daily Revenue by Day of Week"
            value_format = "£{:,.0f}"
            
        elif metric_type == "Average Units Ordered":
            # Group by day of week and date, then calculate daily totals, then average
            daily_totals = year_data.groupby([year_data[DATE_COL].dt.date, 'day_of_week'])[ORDER_QTY_COL_RAW].sum().reset_index()
            daily_totals.columns = ['date', 'day_of_week', 'daily_units']
            
            daily_stats = daily_totals.groupby('day_of_week')['daily_units'].mean().reset_index()
            daily_stats.columns = ['day_of_week', 'avg_value']
            
            y_label = "Average Daily Units Ordered"
            title = "Average Daily Units Ordered by Day of Week"
            value_format = "{:,.0f}"
            
        else:  # Average Order Value
            # Calculate daily order values, then average by day of week
            daily_aov = year_data.groupby([year_data[DATE_COL].dt.date, 'day_of_week']).agg({
                SALES_VALUE_GBP_COL: 'sum',
                ORDER_QTY_COL_RAW: 'sum'
            }).reset_index()
            daily_aov['daily_aov'] = daily_aov[SALES_VALUE_GBP_COL] / daily_aov[ORDER_QTY_COL_RAW]
            daily_aov = daily_aov.dropna(subset=['daily_aov'])  # Remove days with 0 orders
            
            daily_stats = daily_aov.groupby('day_of_week')['daily_aov'].mean().reset_index()
            daily_stats.columns = ['day_of_week', 'avg_value']
            
            y_label = "Average Order Value (£)"
            title = "Average Order Value by Day of Week"
            value_format = "£{:,.2f}"
        
        # Reorder by day of week and add year info
        daily_stats['day_of_week'] = pd.Categorical(daily_stats['day_of_week'], categories=day_order, ordered=True)
        daily_stats = daily_stats.sort_values('day_of_week').reset_index(drop=True)
        daily_stats['year'] = year
        
        yearly_stats.append(daily_stats)
    
    # Combine all years data
    if yearly_stats:
        all_stats = pd.concat(yearly_stats, ignore_index=True)
        
        # Create multi-year comparison chart
        fig = go.Figure()
        
        # Color palette for years
        colors = ['#3b82f6', '#059669', '#dc2626', '#ea580c', '#7c3aed']
        
        for i, year in enumerate(available_years):
            year_data = all_stats[all_stats['year'] == year]
            
            fig.add_trace(go.Bar(
                name=str(year),
                x=year_data['day_of_week'],
                y=year_data['avg_value'],
                marker_color=colors[i % len(colors)],
                opacity=0.8,
                text=[value_format.format(v) for v in year_data['avg_value']],
                textposition='auto',
                hovertemplate=f'<b>{year}</b><br>' +
                             '%{x}<br>' +
                             f'{y_label}: %{{y:,.2f}}<extra></extra>'
            ))
        
        # Update layout
        fig.update_layout(
            title=f"{title} - Year Comparison",
            xaxis_title="Day of Week",
            yaxis_title=y_label,
            barmode='group',  # Group bars by day
            height=500,
            font_family="Inter, -apple-system, BlinkMacSystemFont, sans-serif",
            plot_bgcolor="rgba(0,0,0,0)",  # Transparent background
            paper_bgcolor="rgba(0,0,0,0)",  # Transparent background
            margin=dict(t=60, b=40, l=40, r=40),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(0,0,0,0)"  # Transparent legend background
            )
        )
        
        fig.update_xaxes(gridcolor="rgba(128,128,128,0.2)", linecolor="rgba(128,128,128,0.3)")
        fig.update_yaxes(gridcolor="rgba(128,128,128,0.2)", linecolor="rgba(128,128,128,0.3)", rangemode="tozero")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show summary statistics by year
        st.markdown("#### 📊 Year-by-Year Summary")
        
        summary_cols = st.columns(len(available_years))
        
        for i, year in enumerate(available_years):
            year_data = all_stats[all_stats['year'] == year]
            
            with summary_cols[i]:
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, {colors[i % len(colors)]}15 0%, {colors[i % len(colors)]}25 100%);
                    border: 1px solid {colors[i % len(colors)]}40;
                    padding: 1rem;
                    border-radius: 8px;
                    margin-bottom: 1rem;
                ">
                    <h4 style="color: {colors[i % len(colors)]}; margin: 0; text-align: center;">📅 {year}</h4>
                </div>
                """, unsafe_allow_html=True)
                
                if not year_data.empty:
                    # Best day
                    best_day = year_data.loc[year_data['avg_value'].idxmax(), 'day_of_week']
                    best_value = year_data['avg_value'].max()
                    st.metric(
                        "🏆 Best Day",
                        best_day,
                        value_format.format(best_value)
                    )
                    
                    # Worst day
                    worst_day = year_data.loc[year_data['avg_value'].idxmin(), 'day_of_week']
                    worst_value = year_data['avg_value'].min()
                    st.metric(
                        "📉 Lowest Day",
                        worst_day,
                        value_format.format(worst_value)
                    )
                    
                    # Weekend vs Weekday
                    weekend_avg = year_data[year_data['day_of_week'].isin(['Saturday', 'Sunday'])]['avg_value'].mean()
                    weekday_avg = year_data[~year_data['day_of_week'].isin(['Saturday', 'Sunday'])]['avg_value'].mean()
                    ratio = weekend_avg / weekday_avg if weekday_avg > 0 else 0
                    st.metric(
                        "📅 Weekend/Weekday",
                        f"{ratio:.1f}x",
                        f"W/E: {value_format.format(weekend_avg)}"
                    )
        
        # Year-over-year change analysis
        if len(available_years) > 1:
            st.markdown("---")
            st.markdown("#### 📈 Year-over-Year Changes")
            
            # Create change analysis table
            change_data = []
            
            for day in day_order:
                day_changes = {'Day': day}
                
                for i in range(1, len(available_years)):
                    current_year = available_years[i]
                    prev_year = available_years[i-1]
                    
                    current_value = all_stats[(all_stats['year'] == current_year) & 
                                            (all_stats['day_of_week'] == day)]['avg_value'].iloc[0]
                    prev_value = all_stats[(all_stats['year'] == prev_year) & 
                                         (all_stats['day_of_week'] == day)]['avg_value'].iloc[0]
                    
                    if prev_value > 0:
                        change_pct = ((current_value - prev_value) / prev_value) * 100
                        day_changes[f'{prev_year} → {current_year}'] = f"{change_pct:+.1f}%"
                    else:
                        day_changes[f'{prev_year} → {current_year}'] = "N/A"
                
                change_data.append(day_changes)
            
            change_df = pd.DataFrame(change_data)
            
            st.dataframe(
                change_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Day": st.column_config.TextColumn("📅 Day", width="small"),
                }
            )
    
    else:
        st.warning("No data available for sales patterns analysis.")