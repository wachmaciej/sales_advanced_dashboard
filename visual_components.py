# Enhanced Visual Components
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

def create_enhanced_dataframe(df, title="Data Table", height=400):
    """Create a beautifully styled dataframe display"""
    st.markdown(f"""
    <div style="
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        border: 1px solid #e2e8f0;
        margin: 1rem 0;
    ">
        <h4 style="
            color: #1e293b;
            margin: 0 0 1rem 0;
            font-weight: 600;
        ">{title}</h4>
    </div>
    """, unsafe_allow_html=True)
    
    return st.dataframe(
        df,
        use_container_width=True,
        height=height,
        hide_index=True
    )

def create_gauge_chart(value, max_value, title, color="#3b82f6", suffix=""):
    """Create a modern gauge chart"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title, 'font': {'size': 16}},
        gauge = {
            'axis': {'range': [None, max_value], 'tickwidth': 1, 'tickcolor': "inherit"},
            'bar': {'color': color},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 2,
            'bordercolor': "rgba(128,128,128,0.3)",
            'steps': [
                {'range': [0, max_value*0.3], 'color': "#fef3c7"},
                {'range': [max_value*0.3, max_value*0.7], 'color': "#dbeafe"},
                {'range': [max_value*0.7, max_value], 'color': "#dcfce7"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_value*0.9
            }
        },
        number = {'suffix': suffix}
    ))
    
    fig.update_layout(
        height=300,
        font={'color': "inherit", 'family': "Arial"},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    
    return fig

def create_progress_ring(percentage, title, color="#3b82f6"):
    """Create a modern progress ring chart"""
    fig = go.Figure(data=[go.Pie(
        labels=['Complete', 'Remaining'],
        values=[percentage, 100-percentage],
        hole=.7,
        marker_colors=[color, '#f1f5f9'],
        textinfo='none',
        hoverinfo='none',
        showlegend=False
    )])
    
    fig.add_annotation(
        x=0.5, y=0.5,
        text=f"{percentage:.1f}%",
        showarrow=False,
        font_size=24,
        font_color=color,
        font_weight="bold"
    )
    
    fig.add_annotation(
        x=0.5, y=0.35,
        text=title,
        showarrow=False,
        font_size=14,
        font_color="#64748b"
    )
    
    fig.update_layout(
        height=200,
        showlegend=False,
        margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor="rgba(0,0,0,0)"
    )
    
    return fig

def create_comparison_bar(data_dict, title="Comparison", colors=None):
    """Create a horizontal comparison bar chart"""
    if colors is None:
        colors = ["#3b82f6", "#8b5cf6", "#06d6a0", "#f59e0b", "#ef4444"]
    
    categories = list(data_dict.keys())
    values = list(data_dict.values())
    
    fig = go.Figure(data=[
        go.Bar(
            y=categories,
            x=values,
            orientation='h',
            marker_color=colors[:len(categories)],
            text=values,
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title=title,
        title_font_size=16,
        title_font_weight="bold",
        height=max(200, len(categories) * 50),
        margin=dict(t=50, b=30, l=100, r=30),
        xaxis_title="Value",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(128,128,128,0.2)", linecolor="rgba(128,128,128,0.3)"),
        yaxis=dict(gridcolor="rgba(128,128,128,0.2)", linecolor="rgba(128,128,128,0.3)")
    )
    
    return fig

def create_trend_sparkline(values, color="#3b82f6", height=100):
    """Create a simple trend sparkline"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        y=values,
        mode='lines',
        line=dict(color=color, width=2),
        fill='tonexty',
        fillcolor=f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.3)',
        showlegend=False,
        hovertemplate='Value: %{y}<extra></extra>'
    ))
    
    fig.update_layout(
        height=height,
        margin=dict(t=0, b=0, l=0, r=0),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_kpi_card(title, value, delta=None, trend_data=None, icon="📊"):
    """Create an enhanced KPI card with optional trend sparkline"""
    delta_html = ""
    if delta:
        delta_color = "#22c55e" if isinstance(delta, (int, float)) and delta > 0 else "#ef4444"
        delta_symbol = "↗️" if isinstance(delta, (int, float)) and delta > 0 else "↘️"
        delta_html = f'''
        <div style="
            color: {delta_color}; 
            font-size: 0.9rem; 
            margin-top: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        ">
            {delta_symbol} {delta}
        </div>
        '''
    
    trend_html = ""
    if trend_data:
        # This would need to be implemented with a mini chart
        trend_html = '<div style="margin-top: 1rem; height: 40px; background: #f8fafc; border-radius: 4px;"></div>'
    
    return f'''
    <div style="
        background: linear-gradient(135deg, white 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease;
        height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    ">
        <div>
            <div style="
                display: flex;
                align-items: center;
                gap: 0.5rem;
                color: #64748b;
                font-size: 0.9rem;
                font-weight: 500;
                margin-bottom: 0.75rem;
            ">
                <span style="font-size: 1.25rem;">{icon}</span>
                {title}
            </div>
            <div style="
                color: #1e293b;
                font-size: 2.25rem;
                font-weight: 700;
                line-height: 1;
            ">
                {value}
            </div>
            {delta_html}
        </div>
        {trend_html}
    </div>
    '''
