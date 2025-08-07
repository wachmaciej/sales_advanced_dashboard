# Modern Dashboard Theme Configuration
# Add these color and styling constants to your existing config.py

# Color Palette - Modern Blue Theme
COLORS = {
    "primary": "#3b82f6",
    "primary_dark": "#1d4ed8", 
    "secondary": "#64748b",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "background": "#f8fafc",
    "surface": "#ffffff",
    "text_primary": "#1e293b",
    "text_secondary": "#64748b",
    "border": "#e2e8f0"
}

# Modern Chart Color Schemes
CHART_COLORS = [
    "#3b82f6", "#8b5cf6", "#06d6a0", "#f59e0b", 
    "#ef4444", "#84cc16", "#ec4899", "#14b8a6"
]

# Plotly Theme Configuration
PLOTLY_THEME = {
    "layout": {
        "colorway": CHART_COLORS,
        "font": {"family": "Inter, -apple-system, BlinkMacSystemFont, sans-serif"},
        "plot_bgcolor": "rgba(0,0,0,0)",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "gridcolor": "rgba(128,128,128,0.2)",
        "showgrid": True
    }
}

# Dashboard Icons
ICONS = {
    "kpi": "📊",
    "trends": "📈", 
    "prices": "💰",
    "products": "🛍️",
    "table": "📋",
    "category": "📂",
    "seasonality": "🌊",
    "unrecognised": "❓",
    "loading": "🔄",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️"
}

# Modern CSS Classes
CSS_CLASSES = {
    "card": """
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease;
    """,
    "header": """
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #cbd5e1;
        margin-bottom: 1.5rem;
    """,
    "metric": """
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease;
    """
}
