import pandas as pd
import numpy as np
import datetime
import re
import xlrd
import openpyxl
import csv
from typing import Dict, List, Optional, Tuple, Any
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image
import json
import google.generativeai as genai
import plotly.express as px
import plotly.io as p_json
import plotly
# Thêm các import khác nếu cần 

def delete_booking_from_sheet(booking_id: str, gcp_creds_dict: dict, sheet_id: str, worksheet_name: str) -> bool:
    """
    Deletes a booking record from the specified Google Sheet.
    """
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ]
    creds = Credentials.from_service_account_info(gcp_creds_dict, scopes=scope)
    gc = gspread.authorize(creds)
    
    try:
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.worksheet(worksheet_name) if worksheet_name else sh.sheet1

        # Find the cell with the booking ID
        cell = worksheet.find(booking_id)
        if not cell:
            print(f"Lỗi: Không tìm thấy đặt phòng với ID '{booking_id}' để xóa.")
            return False

        # Delete the entire row
        worksheet.delete_rows(cell.row)
        print(f"Đã xóa đặt phòng ID '{booking_id}' khỏi Google Sheet.")
        return True

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Lỗi: Không tìm thấy Google Sheet với ID '{sheet_id}'.")
        return False
    except Exception as e:
        print(f"Lỗi không xác định khi xóa hàng khỏi Google Sheet: {e}")
        return False

def find_booking_by_id(df: pd.DataFrame, booking_id: str) -> Optional[Dict]:
    """
    Finds a single booking by its ID from the DataFrame.
    """
    if df is None or df.empty or 'Số đặt phòng' not in df.columns:
        return None
    
    booking_row = df[df['Số đặt phòng'] == booking_id]
    
    if not booking_row.empty:
        # Convert the row to a dictionary
        booking_dict = booking_row.iloc[0].to_dict()
        # Convert Timestamps to string for JSON serialization if needed later
        for key, value in booking_dict.items():
            if isinstance(value, pd.Timestamp):
                booking_dict[key] = value.strftime('%Y-%m-%d')
        return booking_dict
    
    return None

def update_booking_in_sheet(booking_id: str, updated_data: dict, gcp_creds_dict: dict, sheet_id: str, worksheet_name: str) -> bool:
    """
    Updates a booking record in the specified Google Sheet.
    """
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ]
    creds = Credentials.from_service_account_info(gcp_creds_dict, scopes=scope)
    gc = gspread.authorize(creds)
    
    try:
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.worksheet(worksheet_name) if worksheet_name else sh.sheet1

        # Find the cell with the booking ID
        cell = worksheet.find(booking_id)
        if not cell:
            print(f"Lỗi: Không tìm thấy đặt phòng với ID '{booking_id}' trong sheet.")
            return False

        # Get headers to maintain column order
        headers = worksheet.row_values(1)
        
        # Create a list of values in the correct order
        row_to_update = [updated_data.get(header, "") for header in headers]
        
        # Update the entire row
        worksheet.update(f'A{cell.row}:{chr(ord("A") + len(headers) - 1)}{cell.row}', [row_to_update])
        print(f"Đã cập nhật đặt phòng ID '{booking_id}' trong Google Sheet.")
        return True

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Lỗi: Không tìm thấy Google Sheet với ID '{sheet_id}'.")
        return False
    except Exception as e:
        print(f"Lỗi không xác định khi cập nhật Google Sheet: {e}")
        return False

def parse_app_standard_date(date_input: Any) -> datetime.date | None:
    if pd.isna(date_input): return None
    if isinstance(date_input, datetime.datetime): return date_input.date()
    if isinstance(date_input, datetime.date): return date_input
    if isinstance(date_input, pd.Timestamp): return date_input.date()
    date_str = str(date_input).strip().lower()
    try:
        if re.match(r"ngày\s*\d{1,2}\s*tháng\s*\d{1,2}\s*năm\s*\d{4}", date_str):
            m = re.search(r"ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", date_str)
            if m: return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        parsed_date = pd.to_datetime(date_str, errors='coerce', dayfirst=True).date()
        if parsed_date: return parsed_date
        parsed_date = pd.to_datetime(date_str, errors='coerce', dayfirst=False).date()
        if parsed_date: return parsed_date
    except Exception: pass
    return None

def convert_display_date_to_app_format(display_date_input: Any) -> Optional[str]:
    if pd.isna(display_date_input): return None
    if isinstance(display_date_input, (datetime.datetime, datetime.date, pd.Timestamp)):
        return f"ngày {display_date_input.day} tháng {display_date_input.month} năm {display_date_input.year}"
    cleaned_date_str = str(display_date_input).replace(',', '').strip().lower()
    m_vietnamese = re.search(r"(\d{1,2})\s*tháng\s*(\d{1,2})\s*(\d{4})", cleaned_date_str)
    if m_vietnamese:
        return f"ngày {m_vietnamese.group(1)} tháng {m_vietnamese.group(2)} năm {m_vietnamese.group(3)}"
    try:
        parsed = pd.to_datetime(cleaned_date_str, errors='coerce', dayfirst=True)
        if pd.notna(parsed): return f"ngày {parsed.day} tháng {parsed.month} năm {parsed.year}"
        parsed = pd.to_datetime(cleaned_date_str, errors='coerce', dayfirst=False)
        if pd.notna(parsed): return f"ngày {parsed.day} tháng {parsed.month} năm {parsed.year}"
    except Exception: pass
    return None

def clean_currency_value(value_input: Any) -> float:
    if pd.isna(value_input): return 0.0
    cleaned_str = str(value_input).strip()
    cleaned_str = re.sub(r'(?i)VND\s*', '', cleaned_str)
    cleaned_str = re.sub(r'[^\d,.-]', '', cleaned_str)
    if not cleaned_str: return 0.0
    has_dot, has_comma = '.' in cleaned_str, ',' in cleaned_str
    if has_dot and has_comma:
        last_dot_pos, last_comma_pos = cleaned_str.rfind('.'), cleaned_str.rfind(',')
        if last_comma_pos > last_dot_pos:
            cleaned_str = cleaned_str.replace('.', '').replace(',', '.')
        else:
            cleaned_str = cleaned_str.replace(',', '')
    elif has_comma:
        if cleaned_str.count(',') > 1 or (cleaned_str.count(',') == 1 and len(cleaned_str.split(',')[-1]) == 3 and len(cleaned_str.split(',')[0]) > 0):
            cleaned_str = cleaned_str.replace(',', '')
        else: cleaned_str = cleaned_str.replace(',', '.')
    elif has_dot:
        if cleaned_str.count('.') > 1 or (cleaned_str.count('.') == 1 and len(cleaned_str.split('.')[-1]) == 3 and len(cleaned_str.split('.')[0]) > 0):
            cleaned_str = cleaned_str.replace('.', '')
    numeric_val = pd.to_numeric(cleaned_str, errors='coerce')
    return numeric_val if pd.notna(numeric_val) else 0.0

def get_cleaned_room_types(df_source: Optional[pd.DataFrame]) -> List[str]:
    if df_source is None or df_source.empty or 'Tên chỗ nghỉ' not in df_source.columns:
        return []
    try:
        unique_values = df_source['Tên chỗ nghỉ'].dropna().unique()
    except Exception:
        return []
    cleaned_types = []
    seen_types = set()
    for val in unique_values:
        s_val = str(val).strip()
        if s_val and s_val not in seen_types:
            cleaned_types.append(s_val)
            seen_types.add(s_val)
    return sorted(cleaned_types)

def import_from_gsheet(sheet_id: str, gcp_creds_dict: dict, worksheet_name: str | None = None) -> pd.DataFrame:
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(gcp_creds_dict, scopes=scope)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    worksheet = sh.worksheet(worksheet_name) if worksheet_name else sh.sheet1
    data = worksheet.get_all_values()
    if not data or len(data) < 2:
        return pd.DataFrame()
    
    df = pd.DataFrame(data[1:], columns=data[0])
    
    # Chuẩn hóa kiểu dữ liệu ngay khi tải
    if 'Tổng thanh toán' in df.columns:
        df['Tổng thanh toán'] = pd.to_numeric(df['Tổng thanh toán'], errors='coerce').fillna(0)
    if 'Check-in Date' in df.columns:
        df['Check-in Date'] = pd.to_datetime(df['Check-in Date'], errors='coerce')
        
    return df

def upload_to_gsheet(df, sheet_id, gcp_creds_dict, worksheet_name=None):
    """
    Uploads a DataFrame to a Google Sheet using service account credentials
    provided as a dictionary (from st.secrets).
    """
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ]
    creds = Credentials.from_service_account_info(gcp_creds_dict, scopes=scope)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    if worksheet_name:
        try:
            worksheet = sh.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")
    else:
        worksheet = sh.sheet1
    worksheet.clear()
    df_str = df.astype(str)
    worksheet.update([df_str.columns.values.tolist()] + df_str.values.tolist())
    return sh.url

def create_demo_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    demo_data = {
        'Tên chỗ nghỉ': ['Home in Old Quarter', 'Old Quarter Home', 'Home in Old Quarter', 'Riverside Apartment'],
        'Tên người đặt': ['Demo User Alpha', 'Demo User Beta', 'Demo User Gamma', 'Demo User Delta'],
        'Ngày đến': ['ngày 22 tháng 5 năm 2025', 'ngày 23 tháng 5 năm 2025', 'ngày 26 tháng 5 năm 2025', 'ngày 1 tháng 6 năm 2025'],
        'Ngày đi': ['ngày 23 tháng 5 năm 2025', 'ngày 24 tháng 5 năm 2025', 'ngày 28 tháng 5 năm 2025', 'ngày 5 tháng 6 năm 2025'],
        'Tình trạng': ['OK', 'OK', 'OK', 'OK'],
        'Tổng thanh toán': [300000, 450000, 600000, 1200000],
        'Số đặt phòng': [f'DEMO{i+1:09d}' for i in range(4)],
        'Người thu tiền': ['LOC LE', 'THAO LE', 'THAO LE', 'LOC LE']
    }
    df_demo = pd.DataFrame(demo_data)
    df_demo['Check-in Date'] = pd.to_datetime(df_demo['Ngày đến'].apply(parse_app_standard_date), errors='coerce')
    df_demo['Tổng thanh toán'] = pd.to_numeric(df_demo['Tổng thanh toán'], errors='coerce').fillna(0)
    active_bookings_demo = df_demo[df_demo['Tình trạng'] != 'Đã hủy'].copy()
    return df_demo, active_bookings_demo

def filter_data(df, start_date, end_date, room_type, purchase_party, min_price, max_price):
    """
    Filter the dataframe based on user inputs.
    """
    filtered_df = df.copy()

    # Date range filtering
    if start_date is not None and end_date is not None:
        filtered_df = filtered_df[(filtered_df['Check-in'] >= start_date) & (filtered_df['Check-out'] <= end_date)]

    # Room type filtering
    if room_type and 'All' not in room_type:
        filtered_df = filtered_df[filtered_df['Room Type'].isin(room_type)]

    # Purchase party filtering
    if purchase_party and 'All' not in purchase_party:
        filtered_df = filtered_df[filtered_df['Purchase Party'].isin(purchase_party)]

    # Price range filtering
    if min_price is not None:
        filtered_df = filtered_df[filtered_df['Price'] >= min_price]
    if max_price is not None:
        filtered_df = filtered_df[filtered_df['Price'] <= max_price]

    return filtered_df

def calculate_kpis(df):
    """
    Calculate KPIs from the dataframe.
    """
    if df.empty:
        return {
            "total_revenue": 0,
            "total_bookings": 0,
            "average_booking_value": 0,
            "average_nights_per_booking": 0,
            "adr": 0,
            "occupancy_rate": 0
        }

    total_revenue = df['Price'].sum()
    total_bookings = df.shape[0]
    average_booking_value = total_revenue / total_bookings if total_bookings > 0 else 0
    
    # Calculate nights per booking
    df['nights'] = (df['Check-out'] - df['Check-in']).dt.days
    average_nights_per_booking = df['nights'].mean() if not df['nights'].empty else 0
    
    # Calculate Average Daily Rate (ADR)
    total_nights = df['nights'].sum()
    adr = total_revenue / total_nights if total_nights > 0 else 0

    # Calculate Occupancy Rate (example assumes 100 available rooms and uses date range)
    if not df.empty:
        days_in_period = (df['Check-out'].max() - df['Check-in'].min()).days
        if days_in_period > 0:
            occupancy_rate = (total_nights / (10 * days_in_period)) * 100 # Assuming 10 rooms available
        else:
            occupancy_rate = 0
    else:
        occupancy_rate = 0

    return {
        "total_revenue": total_revenue,
        "total_bookings": total_bookings,
        "average_booking_value": average_booking_value,
        "average_nights_per_booking": average_nights_per_booking,
        "adr": adr,
        "occupancy_rate": occupancy_rate
    }

def prepare_charts_data(df: pd.DataFrame) -> dict:
    """
    Chuẩn bị dữ liệu đã được tổng hợp cho các biểu đồ trên Dashboard.
    Sử dụng tên cột tiếng Việt từ dữ liệu gốc.
    """
    if df.empty:
        return {
            'monthly_revenue': pd.DataFrame(columns=['Tháng', 'Doanh thu']),
            'room_revenue': pd.DataFrame(columns=['Loại phòng', 'Doanh thu']),
            'collector_revenue': pd.DataFrame(columns=['Người thu tiền', 'Doanh thu'])
        }

    # Đảm bảo các cột cần thiết tồn tại và đúng kiểu dữ liệu
    required_cols = {
        'Check-in Date': 'datetime64[ns]',
        'Tổng thanh toán': 'float64',
        'Tên chỗ nghỉ': 'object',
        'Người thu tiền': 'object'
    }
    
    for col, dtype in required_cols.items():
        if col not in df.columns:
            # Nếu cột không tồn tại, tạo cột rỗng với kiểu dữ liệu phù hợp
            if 'datetime' in dtype:
                df[col] = pd.NaT
            elif 'float' in dtype:
                df[col] = 0.0
            else:
                df[col] = 'N/A'
        # Ép kiểu để đảm bảo tính toán chính xác
        if 'datetime' in dtype:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        elif 'float' in dtype:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 1. Doanh thu hàng tháng
    df_monthly = df.dropna(subset=['Check-in Date']).copy()
    df_monthly['Tháng'] = df_monthly['Check-in Date'].dt.to_period('M').astype(str)
    monthly_revenue = df_monthly.groupby('Tháng')['Tổng thanh toán'].sum().reset_index()
    monthly_revenue = monthly_revenue.sort_values('Tháng')

    # 2. Doanh thu theo loại phòng
    room_revenue = df.groupby('Tên chỗ nghỉ')['Tổng thanh toán'].sum().reset_index()
    room_revenue = room_revenue.sort_values('Tổng thanh toán', ascending=False)

    # 3. Doanh thu theo người thu tiền
    collector_revenue = df.groupby('Người thu tiền')['Tổng thanh toán'].sum().reset_index()
    collector_revenue = collector_revenue.sort_values('Tổng thanh toán', ascending=False)

    return {
        'monthly_revenue': monthly_revenue,
        'room_revenue': room_revenue,
        'collector_revenue': collector_revenue
    }

def append_booking_to_sheet(new_booking_data: dict, gcp_creds_dict: dict, sheet_id: str, worksheet_name: str) -> None:
    """
    Appends a new booking record to the specified Google Sheet.
    """
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ]
    creds = Credentials.from_service_account_info(gcp_creds_dict, scopes=scope)
    gc = gspread.authorize(creds)
    
    try:
        sh = gc.open_by_key(sheet_id)
        if worksheet_name:
            worksheet = sh.worksheet(worksheet_name)
        else:
            worksheet = sh.sheet1

        worksheet.append_row(list(new_booking_data.values()))
        print("Đã thêm hàng mới vào Google Sheet.")

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Lỗi: Không tìm thấy Google Sheet với ID '{sheet_id}'.")
        raise
    except Exception as e:
        print(f"Lỗi khi thêm hàng mới vào Google Sheet: {e}")
        raise

# ==============================================================================
# AI AND IMAGE PROCESSING FUNCTIONS
# ==============================================================================

def extract_booking_info_from_image_content(image_bytes: bytes) -> Optional[List[Dict[str, Any]]]:
    """
    Extracts booking information from an image using Google Gemini.
    
    NOTE: This is a placeholder implementation. The actual AI model call is needed.
    """
    print("Attempting to extract booking info from image...")
    
    # Placeholder: Check if the Gemini library is configured
    if not genai.get_model('models/gemini-pro-vision'):
        print("Lỗi: Gemini Pro Vision model is not configured. Cannot process image.")
        return None
        
    try:
        # This is where the actual call to the Gemini API would go.
        # For now, we will return a hardcoded sample result for demonstration.
        print("Bỏ qua lệnh gọi AI thực tế. Trả về dữ liệu mẫu.")
        sample_data = [
            {
                'Tên người đặt': 'John Doe (from Image)',
                'Số đặt phòng': 'IMG-12345',
                'Ngày đến': '2025-12-01',
                'Ngày đi': '2025-12-03',
                'Tên chỗ nghỉ': 'Sample Room',
                'Tổng thanh toán': 500000,
                'Tình trạng': 'OK'
            },
            {
                'Tên người đặt': 'Jane Smith (from Image)',
                'Số đặt phòng': 'IMG-67890',
                'Ngày đến': '2025-12-05',
                'Ngày đi': '2025-12-06',
                'Tên chỗ nghỉ': 'Another Sample Room',
                'Tổng thanh toán': 250000,
                'Tình trạng': 'OK'
            }
        ]
        return sample_data
    except Exception as e:
        print(f"An error occurred during image extraction: {e}")
        return None

# ==============================================================================
# CALENDAR LOGIC FUNCTIONS
# ==============================================================================

def get_daily_activity(date_to_check: datetime.date, df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Gets check-in and check-out activities for a specific day.
    """
    activities = {'check_in': [], 'check_out': []}
    if df.empty:
        return activities

    # Convert DataFrame date columns to datetime.date objects for comparison
    df['check_in_date_only'] = pd.to_datetime(df['Ngày đến'].apply(parse_app_standard_date), errors='coerce').dt.date
    df['check_out_date_only'] = pd.to_datetime(df['Ngày đi'].apply(parse_app_standard_date), errors='coerce').dt.date

    # Find check-ins for the given day
    check_ins = df[df['check_in_date_only'] == date_to_check]
    if not check_ins.empty:
        activities['check_in'] = check_ins['Tên người đặt'].tolist()

    # Find check-outs for the given day
    check_outs = df[df['check_out_date_only'] == date_to_check]
    if not check_outs.empty:
        activities['check_out'] = check_outs['Tên người đặt'].tolist()
        
    return activities

def get_overall_calendar_day_info(date_to_check: datetime.date, df: pd.DataFrame, total_capacity: int) -> Dict[str, Any]:
    """
    Calculates the occupancy info for a specific day.
    """
    if df.empty:
        return {'occupied_units': 0, 'available_units': total_capacity, 'status_text': f"{total_capacity}/{total_capacity} trống"}

    # Ensure date columns are present and in the correct format
    df['check_in_date_only'] = pd.to_datetime(df['Ngày đến'].apply(parse_app_standard_date), errors='coerce').dt.date
    df['check_out_date_only'] = pd.to_datetime(df['Ngày đi'].apply(parse_app_standard_date), errors='coerce').dt.date
    
    # A room is occupied if the guest has checked in but not yet checked out
    occupied_df = df[
        (df['check_in_date_only'] <= date_to_check) & 
        (df['check_out_date_only'] > date_to_check)
    ]
    
    occupied_units = len(occupied_df)
    available_units = total_capacity - occupied_units
    
    return {
        'occupied_units': occupied_units,
        'available_units': available_units,
        'status_text': f"{available_units}/{total_capacity} trống"
    }

def get_month_activities(year: int, month: int, df: pd.DataFrame, total_capacity: int) -> Dict[int, Dict[str, Any]]:
    """
    Aggregates all calendar activities and info for a given month.
    """
    month_activities = {}
    num_days_in_month = datetime.date(year, month + 1, 1) - datetime.date(year, month, 1) if month < 12 else datetime.date(year + 1, 1, 1) - datetime.date(year, month, 1)
    
    # Pre-calculate date columns to avoid recalculating in the loop
    df['check_in_date_only'] = pd.to_datetime(df['Ngày đến'].apply(parse_app_standard_date), errors='coerce').dt.date
    df['check_out_date_only'] = pd.to_datetime(df['Ngày đi'].apply(parse_app_standard_date), errors='coerce').dt.date

    for day_num in range(1, num_days_in_month.days + 1):
        current_date = datetime.date(year, month, day_num)
        
        daily_activities = get_daily_activity(current_date, df)
        daily_info = get_overall_calendar_day_info(current_date, df, total_capacity)
        
        month_activities[day_num] = {
            **daily_activities,
            **daily_info
        }
        
    return month_activities

# ==============================================================================
# MESSAGE TEMPLATE FUNCTIONS
# ==============================================================================

def get_message_templates(gcp_creds_dict: dict, sheet_id: str, worksheet_name: str) -> List[Dict[str, str]]:
    """
    Reads all message templates from a specified Google Sheet worksheet.
    """
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(gcp_creds_dict, scopes=scope)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        
        worksheet = sh.worksheet(worksheet_name)
        
        records = worksheet.get_all_records() # Returns a list of dictionaries
        return records
    except gspread.exceptions.WorksheetNotFound:
        print(f"Lỗi: Không tìm thấy worksheet với tên '{worksheet_name}'. Trả về danh sách rỗng.")
        return []
    except Exception as e:
        print(f"Lỗi khi đọc mẫu tin nhắn từ Google Sheet: {e}")
        return []

def add_message_template(new_template_data: Dict[str, str], gcp_creds_dict: dict, sheet_id: str, worksheet_name: str) -> None:
    """
    Appends a new message template to the specified Google Sheet worksheet.
    """
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(gcp_creds_dict, scopes=scope)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.worksheet(worksheet_name)

        # Get headers to ensure correct column order
        headers = worksheet.row_values(1)
        if not headers: # If sheet is empty, create headers
            headers = list(new_template_data.keys())
            worksheet.append_row(headers, value_input_option='USER_ENTERED')

        row_to_append = [new_template_data.get(header, "") for header in headers]
        worksheet.append_row(row_to_append, value_input_option='USER_ENTERED')
        print("Đã thêm mẫu tin nhắn mới vào Google Sheet.")
        
    except Exception as e:
        print(f"Lỗi khi thêm mẫu tin nhắn vào Google Sheet: {e}")
        raise 