# data_loader.py
import streamlit as st
import pandas as pd
import warnings
import gspread
from google.oauth2.service_account import Credentials
import os
import traceback
import re # Import regex for robust key extraction

from config import (
    # Constants for auth fallback and type conversion remain
    LOCAL_KEY_PATH, SCOPES,
    NUMERIC_COLS_CONFIG, DATE_COLS_CONFIG,
    TARGET_DATE_COL, DAILY_TARGET_GBP_COL
)

warnings.filterwarnings("ignore")

# Helper function to extract key from URL
def extract_sheet_key(url):
    """Extracts the Google Sheet key from various URL formats."""
    # Regex to find the key between /d/ and /edit or end of string
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if match:
        return match.group(1)
    else:
        # Fallback or error if needed, maybe raise an error
        # For simplicity, returning None here, will be caught later
        return None


@st.cache_data(ttl=18000, show_spinner="Fetching data from Google Sheet...")
def load_data_from_gsheet():
    """Loads data from the specified Google Sheet worksheet using secrets."""

    # --- DIAGNOSTIC PRINT ---
    # print("-" * 20)
    # print("DEBUG: Loaded st.secrets keys:", st.secrets.keys())
    # print("-" * 20)
    # --- END DIAGNOSTIC PRINT ---

    creds = None
    secrets_used = False

    # --- Authentication ---
    # Tries secrets first, then local file.
    try:
        # Check if secrets exist and contain the GCP key
        if hasattr(st, 'secrets') and "gcp_service_account" in st.secrets:
            creds_json_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(creds_json_dict, scopes=SCOPES)
            secrets_used = True
            # st.info("Using GCP credentials from Streamlit secrets.")
    except FileNotFoundError:
        # This means secrets.toml doesn't exist locally, proceed to local file check
        pass # Indentation fixed here (was potentially missing)
    except Exception as e_secrets:
        # Catch other potential errors during secrets processing
        st.warning(f"Error processing Streamlit secrets: {e_secrets}. Trying local key file.")
        pass # Indentation fixed here (was potentially missing)

    # Fallback to local JSON file if secrets weren't successfully used or available
    if not secrets_used:
        if os.path.exists(LOCAL_KEY_PATH):
            try:
                creds = Credentials.from_service_account_file(LOCAL_KEY_PATH, scopes=SCOPES)
                # st.info(f"Using GCP credentials from local file: '{LOCAL_KEY_PATH}'.")
            except Exception as e_local:
                # Handle errors loading from the local file specifically
                st.error(f"Error loading credentials from local file '{LOCAL_KEY_PATH}': {e_local}")
                st.stop() # Stop if local file exists but can't be read
        else:
            # This error occurs if secrets failed AND local file doesn't exist
            st.error(f"Authentication Error: GCP credentials not found in Streamlit Secrets and local key file '{LOCAL_KEY_PATH}' not found.")
            st.info("For deployment, add [gcp_service_account] section to secrets.toml. For local use, ensure service_account.json exists.")
            st.stop() # Stop execution if no credentials found

    # Final check if credentials object was successfully created by either method
    if not creds:
        st.error("Authentication failed. Could not load credentials object.")
        st.stop()

    # --- Authorize and Open Sheet ---
    try:
        client = gspread.authorize(creds)
        sheet_key = None # Initialize sheet_key
        worksheet_name = None # Initialize worksheet_name
        spreadsheet = None # Initialize spreadsheet

        try:
            # --- Read URL and Worksheet Name from Secrets ---
            sheet_url = st.secrets["google_sheet_url"]
            worksheet_name = st.secrets["worksheet_name"] # Read worksheet name

            # --- Extract the Key from the URL ---
            sheet_key = extract_sheet_key(sheet_url)
            if not sheet_key:
                st.error(f"Could not extract Google Sheet key from the URL in secrets: {sheet_url}")
                st.stop()

            # --- Open Sheet using Extracted Key ---
            spreadsheet = client.open_by_key(sheet_key)
            # st.success(f"Successfully opened Google Sheet: '{spreadsheet.title}'")

        except KeyError as e:
            # Handle case where keys are missing in secrets.toml
            st.error(f"Error: '{e.args[0]}' not found in Streamlit Secrets (secrets.toml).")
            st.info("Please ensure google_sheet_url and worksheet_name are defined in your secrets file.")
            st.info(f"Available keys found by Streamlit: {st.secrets.keys()}") # Keep debug info
            st.stop()
        except gspread.exceptions.SpreadsheetNotFound:
            st.error(f"Error: Google Sheet with extracted key '{sheet_key}' not found or not shared.")
            st.info(f"Ensure the URL in secrets is correct and the Sheet is shared with: {creds.service_account_email}")
            st.stop()
        except gspread.exceptions.APIError as api_error:
             st.error(f"Google Sheets API Error while opening spreadsheet: {api_error}")
             st.info("Check API permissions and sharing settings.")
             st.stop()
        except Exception as e_open: # Catch any other unexpected error during opening
             st.error(f"An unexpected error occurred while opening the sheet: {e_open}")
             st.error(traceback.format_exc())
             st.stop()


        # --- Open Worksheet using name from Secrets ---
        # Ensure spreadsheet object was created before proceeding
        if spreadsheet is None:
             st.error("Failed to open spreadsheet object. Cannot proceed.")
             st.stop()

        try:
            if not worksheet_name:
                 st.error("Worksheet name could not be read from secrets.")
                 st.stop()
            worksheet = spreadsheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            st.error(f"Error: Worksheet '{worksheet_name}' not found in the spreadsheet '{spreadsheet.title}'.")
            st.info("Check the worksheet_name in secrets.toml matches the actual tab name.")
            st.stop()
        except Exception as e_worksheet: # Catch any other error opening worksheet
            st.error(f"An error occurred opening worksheet '{worksheet_name}': {e_worksheet}")
            st.error(traceback.format_exc())
            st.stop()


        # --- Read Data and Convert Types (Moved inside the main try block) ---
        # This ensures df is only processed if sheet/worksheet opening succeeded
        try:
            data = worksheet.get_all_values()
            if not data or len(data) < 2:
                st.warning(f"No data found in worksheet '{worksheet_name}' or only headers present.")
                return pd.DataFrame() # Return empty DataFrame

            headers = data.pop(0)
            df = pd.DataFrame(data, columns=headers) # 'df' is defined here

            # --- Data Type Conversion section (uses NUMERIC/DATE_COLS_CONFIG) ---
            # Now this code only runs if 'df' was successfully created
            numeric_cols = [col for col in NUMERIC_COLS_CONFIG if col in df.columns]
            date_cols = [col for col in DATE_COLS_CONFIG if col in df.columns]

            for col in numeric_cols:
                # Check if column exists before processing (belt-and-suspenders)
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(r'[£,]', '', regex=True).str.strip()
                    df[col] = df[col].replace('', pd.NA)
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            for col in date_cols:
                 if col in df.columns:
                    df[col] = df[col].replace('', pd.NaT)
                    df[col] = pd.to_datetime(df[col], errors='coerce', infer_datetime_format=True)

            df = df.replace('', None)
            # st.success("Data loaded and types converted successfully.")
            return df # Return the processed DataFrame

        except Exception as e_read: # Catch errors during reading/processing
            st.error(f"An error occurred reading or processing data from worksheet '{worksheet_name}': {e_read}")
            st.error(traceback.format_exc())
            st.stop()


    # --- Outer Exception Handling ---
    # Catch errors that might occur during client authorization itself
    except gspread.exceptions.APIError as e_api:
        st.error(f"Google Sheets API Error during client authorization or initial access: {e_api}")
        st.stop()
    except Exception as e:
        st.error(f"An unexpected error occurred during Google Sheets access setup: {e}")
        st.error(traceback.format_exc())
        st.stop()


@st.cache_data(ttl=18000, show_spinner="Loading targets data...")
def load_targets_from_gsheet():
    """Loads target data from the TARGETS worksheet in the same Google Sheet."""
    
    try:
        # Reuse authentication setup from main function
        creds = None
        secrets_used = False

        # --- Authentication (same as main function) ---
        try:
            if hasattr(st, 'secrets') and "gcp_service_account" in st.secrets:
                creds_json_dict = dict(st.secrets["gcp_service_account"])
                creds = Credentials.from_service_account_info(creds_json_dict, scopes=SCOPES)
                secrets_used = True
            else:
                if os.path.exists(LOCAL_KEY_PATH):
                    creds = Credentials.from_service_account_file(LOCAL_KEY_PATH, scopes=SCOPES)
                else:
                    st.warning("No valid authentication found for Google Sheets. Check secrets or local key file.")
                    return None
        except Exception as auth_error:
            st.error(f"Authentication error: {auth_error}")
            return None

        # --- Open Sheet ---
        client = gspread.authorize(creds)
        
        # Get sheet URL and key from secrets
        sheet_url = st.secrets.get("google_sheet_url", "")
        sheet_key = extract_sheet_key(sheet_url)
        
        if not sheet_key:
            st.error("Could not extract sheet key from URL")
            return None
            
        spreadsheet = client.open_by_key(sheet_key)
        
        # --- Open TARGETS worksheet ---
        try:
            targets_worksheet = spreadsheet.worksheet("TARGETS")
        except gspread.exceptions.WorksheetNotFound:
            # List available worksheets for debugging
            available_sheets = [ws.title for ws in spreadsheet.worksheets()]
            st.warning(f"❌ TARGETS worksheet not found. Available sheets: {available_sheets}")
            st.info("💡 Make sure your sheet is named exactly 'TARGETS' (case-sensitive)")
            return None
        
        # --- Read targets data ---
        data = targets_worksheet.get_all_values()
        if not data or len(data) < 2:
            st.warning("TARGETS worksheet is empty or has no data rows")
            return None
            
        # Convert to DataFrame
        df_targets = pd.DataFrame(data[1:], columns=data[0])
        
        # Convert date column - handle DD/MM/YYYY format
        if TARGET_DATE_COL in df_targets.columns:
            df_targets[TARGET_DATE_COL] = pd.to_datetime(df_targets[TARGET_DATE_COL], format='%d/%m/%Y', errors='coerce')
        else:
            st.error(f"❌ Expected column '{TARGET_DATE_COL}' not found in TARGETS sheet")
        
        # Convert target values to numeric - clean currency formatting first
        if DAILY_TARGET_GBP_COL in df_targets.columns:
            # Remove currency symbols and commas, then convert to numeric
            df_targets[DAILY_TARGET_GBP_COL] = df_targets[DAILY_TARGET_GBP_COL].astype(str)
            df_targets[DAILY_TARGET_GBP_COL] = df_targets[DAILY_TARGET_GBP_COL].str.replace('£', '', regex=False)
            df_targets[DAILY_TARGET_GBP_COL] = df_targets[DAILY_TARGET_GBP_COL].str.replace(',', '', regex=False)
            df_targets[DAILY_TARGET_GBP_COL] = pd.to_numeric(df_targets[DAILY_TARGET_GBP_COL], errors='coerce')
        else:
            st.error(f"❌ Expected column '{DAILY_TARGET_GBP_COL}' not found in TARGETS sheet")
        
        # Remove rows with invalid data
        df_targets = df_targets.dropna(subset=[TARGET_DATE_COL, DAILY_TARGET_GBP_COL])
        
        return df_targets
        
    except Exception as e:
        st.error(f"Error loading targets data: {e}")
        return None


@st.cache_data(ttl=18000, show_spinner="Loading PPC data from Google Sheet...")
def load_ppc_data_from_gsheet(country="US"):
    """Loads PPC data from the new Google Sheet for the specified country.
    
    Args:
        country (str): Country code for the worksheet (US, UK, CA, MX, DE, ES, IT, FR)
    
    Returns:
        pd.DataFrame: DataFrame containing PPC data for the specified country
    """
    
    try:
        # --- Authentication (same as main function) ---
        creds = None
        secrets_used = False

        try:
            if hasattr(st, 'secrets') and "gcp_service_account" in st.secrets:
                creds_json_dict = dict(st.secrets["gcp_service_account"])
                creds = Credentials.from_service_account_info(creds_json_dict, scopes=SCOPES)
                secrets_used = True
            else:
                if os.path.exists(LOCAL_KEY_PATH):
                    creds = Credentials.from_service_account_file(LOCAL_KEY_PATH, scopes=SCOPES)
                else:
                    st.error("No valid authentication found for Google Sheets. Check secrets or local key file.")
                    return pd.DataFrame()
        except Exception as auth_error:
            st.error(f"Authentication error: {auth_error}")
            return pd.DataFrame()

        # --- Open New Sheet ---
        client = gspread.authorize(creds)
        
        # Get new sheet URL from secrets
        try:
            new_sheet_url = st.secrets["new_google_sheet_url"]
            sheet_key = extract_sheet_key(new_sheet_url)
            
            if not sheet_key:
                st.error("Could not extract sheet key from new_google_sheet_url")
                return pd.DataFrame()
                
            spreadsheet = client.open_by_key(sheet_key)
            
        except KeyError:
            st.error("'new_google_sheet_url' not found in secrets.toml")
            return pd.DataFrame()
        except gspread.exceptions.SpreadsheetNotFound:
            st.error(f"New Google Sheet not found or not shared with service account")
            return pd.DataFrame()
        
        # --- Open Country Worksheet ---
        try:
            worksheet = spreadsheet.worksheet(country)
        except gspread.exceptions.WorksheetNotFound:
            available_sheets = [ws.title for ws in spreadsheet.worksheets()]
            st.error(f"Worksheet '{country}' not found. Available sheets: {available_sheets}")
            return pd.DataFrame()
        
        # --- Read and Process Data ---
        data = worksheet.get_all_values()
        if not data or len(data) < 2:
            st.warning(f"No data found in worksheet '{country}' or only headers present.")
            return pd.DataFrame()

        headers = data.pop(0)
        df = pd.DataFrame(data, columns=headers)
        
        # Clean empty strings and convert to appropriate types
        df = df.replace('', pd.NA)
        
        # Convert numeric columns (assuming standard PPC metrics)
        numeric_columns = ['Sessions', 'Page Views', 'Impressions', 'Clicks', 'Ad Purchases', 
                          'Ad Units Sold', 'Ad Spend', 'Ad Sales', 'Total Sales', 
                          'Total Units Ordered', 'Total Ordered Items % Ad Sales', 
                          '% Ad Orders', 'Avg Order Value', 'Avg Units Per Order', 
                          'Organic Sales', 'Organic Orders', 'Ads CTR', 'ACOS', 
                          'TACOS', 'CPC', 'CPA']
        
        for col in numeric_columns:
            if col in df.columns:
                # Clean currency symbols and convert to numeric
                df[col] = df[col].astype(str).str.replace(r'[£$,]', '', regex=True).str.strip()
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Convert date column
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce', dayfirst=True)
        
        return df
        
    except Exception as e:
        st.error(f"Error loading PPC data for {country}: {e}")
        st.error(traceback.format_exc())
        return pd.DataFrame()

