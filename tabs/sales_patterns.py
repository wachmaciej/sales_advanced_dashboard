# tabs/sales_patterns.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config import (
    CUSTOM_YEAR_COL, SALES_VALUE_GBP_COL, DATE_COL, ORDER_QTY_COL_RAW
)

def display_tab(df, available_years, default_years):
    """Displays the Sales Patterns tab with day-of-week analysis."""
    st.markdown("### 📅 Sales Patterns - Day of Week Analysis")
    
    # Simple metric selector
    col1, col2 = st.columns([1, 3])
    with col1:
        metric_type = st.selectbox(
            "📊 Select Metric",
            options=["Average Revenue", "Average Units Ordered", "Average Order Value"],
            index=0,
            key="patterns_metric_simple"
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
    
    # Calculate metrics based on selection
    if metric_type == "Average Revenue":
        # Group by day of week and date, then calculate daily totals, then average
        daily_totals = df_analysis.groupby([df_analysis[DATE_COL].dt.date, 'day_of_week'])[SALES_VALUE_GBP_COL].sum().reset_index()
        daily_totals.columns = ['date', 'day_of_week', 'daily_revenue']
        
        daily_stats = daily_totals.groupby('day_of_week')['daily_revenue'].mean().reset_index()
        daily_stats.columns = ['day_of_week', 'avg_value']
        
        y_label = "Average Daily Revenue (£)"
        title = "Average Daily Revenue by Day of Week"
        color_scale = 'Blues'
        value_format = "£{:,.0f}"
        
    elif metric_type == "Average Units Ordered":
        # Group by day of week and date, then calculate daily totals, then average
        daily_totals = df_analysis.groupby([df_analysis[DATE_COL].dt.date, 'day_of_week'])[ORDER_QTY_COL_RAW].sum().reset_index()
        daily_totals.columns = ['date', 'day_of_week', 'daily_units']
        
        daily_stats = daily_totals.groupby('day_of_week')['daily_units'].mean().reset_index()
        daily_stats.columns = ['day_of_week', 'avg_value']
        
        y_label = "Average Daily Units Ordered"
        title = "Average Daily Units Ordered by Day of Week"
        color_scale = 'Greens'
        value_format = "{:,.0f}"
        
    else:  # Average Order Value
        # Calculate daily order values, then average by day of week
        daily_aov = df_analysis.groupby([df_analysis[DATE_COL].dt.date, 'day_of_week']).agg({
            SALES_VALUE_GBP_COL: 'sum',
            ORDER_QTY_COL_RAW: 'sum'
        }).reset_index()
        daily_aov['daily_aov'] = daily_aov[SALES_VALUE_GBP_COL] / daily_aov[ORDER_QTY_COL_RAW]
        daily_aov = daily_aov.dropna(subset=['daily_aov'])  # Remove days with 0 orders
        
        daily_stats = daily_aov.groupby('day_of_week')['daily_aov'].mean().reset_index()
        daily_stats.columns = ['day_of_week', 'avg_value']
        
        y_label = "Average Order Value (£)"
        title = "Average Order Value by Day of Week"
        color_scale = 'Purples'
        value_format = "£{:,.2f}"
    
    # Reorder by day of week
    daily_stats['day_of_week'] = pd.Categorical(daily_stats['day_of_week'], categories=day_order, ordered=True)
    daily_stats = daily_stats.sort_values('day_of_week').reset_index(drop=True)
    
    # Create bar chart
    fig = px.bar(
        daily_stats,
        x='day_of_week',
        y='avg_value',
        title=title,
        labels={
            'avg_value': y_label,
            'day_of_week': 'Day of Week'
        },
        color='avg_value',
        color_continuous_scale=color_scale
    )
    
    # Add value labels on bars
    for i, row in daily_stats.iterrows():
        fig.add_annotation(
            x=row['day_of_week'],
            y=row['avg_value'],
            text=value_format.format(row['avg_value']),
            showarrow=False,
            yshift=10,
            font=dict(size=11, color="black")
        )
    
    # Update layout
    fig.update_layout(
        showlegend=False,
        height=500,
        font_family="Inter, -apple-system, BlinkMacSystemFont, sans-serif",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=60, b=40, l=40, r=40)
    )
    
    fig.update_xaxes(gridcolor="rgba(128,128,128,0.2)", linecolor="rgba(128,128,128,0.3)")
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.2)", linecolor="rgba(128,128,128,0.3)", rangemode="tozero")
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show summary statistics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        best_day = daily_stats.loc[daily_stats['avg_value'].idxmax(), 'day_of_week']
        best_value = daily_stats['avg_value'].max()
        st.metric(
            "🏆 Best Day",
            best_day,
            value_format.format(best_value)
        )
    
    with col2:
        worst_day = daily_stats.loc[daily_stats['avg_value'].idxmin(), 'day_of_week']
        worst_value = daily_stats['avg_value'].min()
        st.metric(
            "📉 Lowest Day",
            worst_day,
            value_format.format(worst_value)
        )
    
    with col3:
        weekend_avg = daily_stats[daily_stats['day_of_week'].isin(['Saturday', 'Sunday'])]['avg_value'].mean()
        weekday_avg = daily_stats[~daily_stats['day_of_week'].isin(['Saturday', 'Sunday'])]['avg_value'].mean()
        ratio = weekend_avg / weekday_avg if weekday_avg > 0 else 0
        st.metric(
            "📅 Weekend vs Weekday",
            f"{ratio:.1f}x",
            f"Weekend: {value_format.format(weekend_avg)}, Weekday: {value_format.format(weekday_avg)}"
        )
