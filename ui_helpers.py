# Modern UI Enhancement Utilities
import streamlit as st

def apply_modern_theme():
    """Apply modern CSS theme to Streamlit app"""
    st.markdown("""
    <style>
        /* Enhanced button styling */
        .stButton > button {
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 500;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
        }
        
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }
        
        /* Enhanced selectbox styling */
        .stSelectbox > div > div {
            background-color: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }
        
        /* Enhanced multiselect styling */
        .stMultiSelect > div > div {
            background-color: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }
        
        /* Enhanced slider styling */
        .stSlider > div > div > div {
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        }
        
        /* Chart title styling */
        .chart-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e2e8f0;
        }
        
        /* Info box styling */
        .info-box {
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border: 1px solid #3b82f6;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        /* Warning box styling */
        .warning-box {
            background: linear-gradient(135deg, #fefce8 0%, #fef3c7 100%);
            border: 1px solid #f59e0b;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        /* Success box styling */
        .success-box {
            background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
            border: 1px solid #22c55e;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
        }
    </style>
    """, unsafe_allow_html=True)

def create_metric_card(title, value, delta=None, help_text=None):
    """Create a styled metric card"""
    delta_html = ""
    if delta:
        delta_color = "#22c55e" if delta > 0 else "#ef4444"
        delta_symbol = "↗️" if delta > 0 else "↘️"
        delta_html = f'<div style="color: {delta_color}; font-size: 0.9rem; margin-top: 0.25rem;">{delta_symbol} {delta}</div>'
    
    help_html = ""
    if help_text:
        help_html = f'<div style="color: #64748b; font-size: 0.8rem; margin-top: 0.5rem;">{help_text}</div>'
    
    return f"""
    <div style="
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease;
        text-align: center;
    ">
        <div style="color: #64748b; font-size: 0.9rem; font-weight: 500; margin-bottom: 0.5rem;">{title}</div>
        <div style="color: #1e293b; font-size: 2rem; font-weight: 700;">{value}</div>
        {delta_html}
        {help_html}
    </div>
    """

def create_section_header(title, icon="📊"):
    """Create a styled section header"""
    return f"""
    <div style="
        display: flex;
        align-items: center;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e2e8f0;
    ">
        <span style="font-size: 1.5rem; margin-right: 0.5rem;">{icon}</span>
        <h2 style="
            color: #1e293b;
            font-size: 1.5rem;
            font-weight: 600;
            margin: 0;
        ">{title}</h2>
    </div>
    """

def create_info_box(message, type="info"):
    """Create styled info boxes"""
    colors = {
        "info": {"bg": "linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)", "border": "#3b82f6", "icon": "ℹ️"},
        "warning": {"bg": "linear-gradient(135deg, #fefce8 0%, #fef3c7 100%)", "border": "#f59e0b", "icon": "⚠️"},
        "success": {"bg": "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)", "border": "#22c55e", "icon": "✅"},
        "error": {"bg": "linear-gradient(135deg, #fef2f2 0%, #fecaca 100%)", "border": "#ef4444", "icon": "❌"}
    }
    
    style = colors.get(type, colors["info"])
    
    return f"""
    <div style="
        background: {style['bg']};
        border: 1px solid {style['border']};
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        display: flex;
        align-items: center;
    ">
        <span style="font-size: 1.25rem; margin-right: 0.75rem;">{style['icon']}</span>
        <div style="color: #374151;">{message}</div>
    </div>
    """
