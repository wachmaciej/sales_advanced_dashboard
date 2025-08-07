# utils.py
import pandas as pd
import datetime
import calendar # Keep if needed, but get_custom_week_date_range doesn't use it directly
from config import CUSTOM_YEAR_COL, WEEK_AS_INT_COL # Import relevant config

# --- Formatting Functions ---
def format_currency(value):
    """Formats a numeric value as currency (£)."""
    if pd.isna(value): return "£N/A" # Handle NaN values
    try:
        return f"£{float(value):,.2f}"
    except (ValueError, TypeError):
        return "£Error" # Handle non-numeric input

def format_currency_int(value):
    """Formats a numeric value as integer currency (£)."""
    if pd.isna(value): return "£N/A" # Handle NaN values
    try:
        # Round before converting to int to handle decimals properly
        return f"£{int(round(float(value))):,}"
    except (ValueError, TypeError):
        return "£Error" # Handle non-numeric input

# --- ADDED: Dynamic Currency Formatter ---
def format_dynamic_currency(value, symbol=""):
    """Formats a numeric value as currency with a dynamic symbol."""
    if pd.isna(value): return "-" # Handle NaN values with a dash or N/A as preferred
    try:
        # Basic symbol placement, adjust if needed for specific currencies (e.g., EUR often has symbol after)
        return f"{symbol}{float(value):,.2f}"
    except (ValueError, TypeError):
        return "Error" # Handle non-numeric input
# --- END ADDED ---


# --- Date/Week Functions ---
def get_custom_week_date_range(week_year, week_number):
    """Gets the start and end date for a given custom week year and number (Sat-Fri)."""
    try:
        week_year = int(week_year)
        week_number = int(week_number)
        # Calculate the start of the first week of the week_year
        first_day = datetime.date(week_year, 1, 1)
        # Saturday=0, Sunday=1, ..., Friday=6
        first_day_custom_dow = (first_day.weekday() + 2) % 7
        first_week_start = first_day - datetime.timedelta(days=first_day_custom_dow)

        # Calculate the start date of the requested week
        # Subtract 1 because week numbers start from 1
        week_start = first_week_start + datetime.timedelta(weeks=week_number - 1)
        week_end = week_start + datetime.timedelta(days=6)
        return week_start, week_end
    except (ValueError, TypeError) as e:
        # Consider logging this warning instead of using st.warning if utils shouldn't depend on streamlit
        # print(f"Warning: Invalid input for get_custom_week_date_range: Year={week_year}, Week={week_number}. Error: {e}")
        return None, None

def get_current_custom_week(current_year=None):
    """
    Gets the current custom week number based on today's date.
    Custom weeks run Saturday to Friday.
    Returns the week number for the given year (defaults to current year).
    """
    if current_year is None:
        current_year = datetime.date.today().year
    
    today = datetime.date.today()
    
    # Calculate the start of the first week of the current_year
    first_day = datetime.date(current_year, 1, 1)
    # Saturday=0, Sunday=1, ..., Friday=6
    first_day_custom_dow = (first_day.weekday() + 2) % 7
    first_week_start = first_day - datetime.timedelta(days=first_day_custom_dow)
    
    # Calculate which week today falls into
    days_since_first_week = (today - first_week_start).days
    current_week = (days_since_first_week // 7) + 1
    
    # Ensure week number is positive and reasonable (1-53)
    if current_week < 1:
        current_week = 1
    elif current_week > 53:
        current_week = 53
    
    return current_week

# --- Collapsible Filter Function ---
def create_filter_section(title, key, default_expanded=False):
    """
    Creates a collapsible filter section that starts collapsed by default.
    
    Args:
        title (str): The title for the filter section
        key (str): Unique key for the filter section
        default_expanded (bool): Whether to start expanded
    
    Returns:
        streamlit.expander: The expander object
    """
    import streamlit as st
    
    # Create a toggle button for showing/hiding filters
    col1, col2 = st.columns([0.8, 0.2])
    
    with col1:
        st.markdown(f"**{title}**")
    
    with col2:
        show_filters = st.button(
            "🎛️ Filters" if not st.session_state.get(f"show_filters_{key}", default_expanded) else "📋 Hide",
            key=f"toggle_filters_{key}",
            help="Click to show/hide filter options"
        )
    
    # Toggle state when button is clicked
    if show_filters:
        current_state = st.session_state.get(f"show_filters_{key}", default_expanded)
        st.session_state[f"show_filters_{key}"] = not current_state
    
    # Return whether filters should be shown
    return st.session_state.get(f"show_filters_{key}", default_expanded)


# --- Target Calculation Functions ---
def filter_amazon_sales(df):
    """Filter sales data to only include Amazon channels."""
    from config import SALES_CHANNEL_COL, AMAZON_CHANNEL_FILTER
    
    if SALES_CHANNEL_COL not in df.columns:
        return pd.DataFrame()  # Return empty DataFrame if column doesn't exist
    
    return df[df[SALES_CHANNEL_COL].str.contains(AMAZON_CHANNEL_FILTER, case=False, na=False)]


def get_daily_target_actual(sales_df, targets_df, target_date):
    """Get target vs actual for a specific date (Amazon channels only)."""
    from config import DATE_COL, SALES_VALUE_GBP_COL, TARGET_DATE_COL, DAILY_TARGET_GBP_COL
    
    # Filter Amazon sales for the specific date
    amazon_sales = filter_amazon_sales(sales_df)
    date_sales = amazon_sales[amazon_sales[DATE_COL].dt.date == target_date]
    actual = date_sales[SALES_VALUE_GBP_COL].sum() if not date_sales.empty else 0
    
    # Get target for the date
    target_row = targets_df[targets_df[TARGET_DATE_COL].dt.date == target_date]
    target = target_row[DAILY_TARGET_GBP_COL].iloc[0] if not target_row.empty else 0
    
    return target, actual


def get_weekly_target_actual(sales_df, targets_df, week_start, week_end):
    """Get target vs actual for a week range (Amazon channels only)."""
    from config import DATE_COL, SALES_VALUE_GBP_COL, TARGET_DATE_COL, DAILY_TARGET_GBP_COL
    
    # Filter Amazon sales for the week
    amazon_sales = filter_amazon_sales(sales_df)
    week_sales = amazon_sales[
        (amazon_sales[DATE_COL].dt.date >= week_start) & 
        (amazon_sales[DATE_COL].dt.date <= week_end)
    ]
    actual = week_sales[SALES_VALUE_GBP_COL].sum() if not week_sales.empty else 0
    
    # Get targets for the week (sum of daily targets)
    week_targets = targets_df[
        (targets_df[TARGET_DATE_COL].dt.date >= week_start) & 
        (targets_df[TARGET_DATE_COL].dt.date <= week_end)
    ]
    target = week_targets[DAILY_TARGET_GBP_COL].sum() if not week_targets.empty else 0
    
    return target, actual


def calculate_variance(target, actual):
    """Calculate variance percentage and amount."""
    if target == 0:
        return 0, 0  # No variance calculation possible
    
    variance_amount = actual - target
    variance_percent = (variance_amount / target) * 100
    
    return variance_percent, variance_amount
