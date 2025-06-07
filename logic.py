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

def parse_app_standard_date(date_input: Any) -> Optional[datetime.date]:
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

def import_from_gsheet(sheet_id: str, gcp_creds_dict: dict, worksheet_name: Optional[str] = None) -> pd.DataFrame:
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
        data = worksheet.get_all_values()
        if not data or len(data) < 2:
            return pd.DataFrame()
        df = pd.DataFrame(data[1:], columns=data[0])
        # Chuyển đổi kiểu dữ liệu sau khi tải
        for col_num_common in ["Tổng thanh toán", "Hoa hồng"]:
            if col_num_common in df.columns:
                 df[col_num_common] = df[col_num_common].apply(clean_currency_value)
        cols_to_datetime = ['Check-in Date', 'Check-out Date', 'Booking Date']
        for col_dt in cols_to_datetime:
            if col_dt in df.columns:
                df[col_dt] = pd.to_datetime(df[col_dt], errors='coerce')

        if 'Stay Duration' not in df.columns and 'Check-in Date' in df.columns and 'Check-out Date' in df.columns:
             df['Stay Duration'] = (df['Check-out Date'] - df['Check-in Date']).dt.days
             df['Stay Duration'] = df['Stay Duration'].apply(lambda x: max(0, x) if pd.notna(x) else 0)
        if 'Giá mỗi đêm' not in df.columns and 'Tổng thanh toán' in df.columns and 'Stay Duration' in df.columns:
            df['Tổng thanh toán'] = pd.to_numeric(df['Tổng thanh toán'], errors='coerce').fillna(0)
            df['Giá mỗi đêm'] = np.where(
                (df['Stay Duration'].notna()) & (df['Stay Duration'] > 0) & (df['Tổng thanh toán'].notna()),
                df['Tổng thanh toán'] / df['Stay Duration'],
                0.0
            ).round(0)
        return df
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Lỗi: Không tìm thấy Google Sheet với ID '{sheet_id}'. Vui lòng kiểm tra lại ID.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Lỗi không xác định khi tải từ Google Sheet: {e}")
        return pd.DataFrame()

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

def create_demo_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    print("Đang tạo dữ liệu demo...")
    demo_data = {
        'Tên chỗ nghỉ': ['Home in Old Quarter - Night market', 'Old Quarter Home- Kitchen & Balcony', 'Home in Old Quarter - Night market', 'Old Quarter Home- Kitchen & Balcony', 'Riverside Boutique Apartment'],
        'Vị trí': ['Phố Cổ Hà Nội, Hoàn Kiếm, Vietnam', '118 Phố Hàng Bạc, Hoàn Kiếm, Vietnam', 'Phố Cổ Hà Nội, Hoàn Kiếm, Vietnam', '118 Phố Hàng Bạc, Hoàn Kiếm, Vietnam', 'Quận 2, TP. Hồ Chí Minh, Vietnam'],
        'Tên người đặt': ['Demo User Alpha', 'Demo User Beta', 'Demo User Alpha', 'Demo User Gamma', 'Demo User Delta'],
        'Thành viên Genius': ['Không', 'Có', 'Không', 'Có', 'Không'],
        'Ngày đến': ['ngày 22 tháng 5 năm 2025', 'ngày 23 tháng 5 năm 2025', 'ngày 25 tháng 5 năm 2025', 'ngày 26 tháng 5 năm 2025', 'ngày 1 tháng 6 năm 2025'],
        'Ngày đi': ['ngày 23 tháng 5 năm 2025', 'ngày 24 tháng 5 năm 2025', 'ngày 26 tháng 5 năm 2025', 'ngày 28 tháng 5 năm 2025', 'ngày 5 tháng 6 năm 2025'],
        'Được đặt vào': ['ngày 20 tháng 5 năm 2025', 'ngày 21 tháng 5 năm 2025', 'ngày 22 tháng 5 năm 2025', 'ngày 23 tháng 5 năm 2025', 'ngày 25 tháng 5 năm 2025'],
        'Tình trạng': ['OK', 'OK', 'Đã hủy', 'OK', 'OK'],
        'Tổng thanh toán': [300000, 450000, 200000, 600000, 1200000],
        'Hoa hồng': [60000, 90000, 40000, 120000, 240000],
        'Tiền tệ': ['VND', 'VND', 'VND', 'VND', 'VND'],
        'Số đặt phòng': [f'DEMO{i+1:09d}' for i in range(5)],
        'Người thu tiền': ['LOC LE', 'THAO LE', 'LOC LE', 'THAO LE', 'LOC LE']
    }
    df_demo = pd.DataFrame(demo_data)
    df_demo['Check-in Date'] = df_demo['Ngày đến'].apply(parse_app_standard_date)
    df_demo['Check-out Date'] = df_demo['Ngày đi'].apply(parse_app_standard_date)
    df_demo['Booking Date'] = df_demo['Được đặt vào'].apply(parse_app_standard_date)
    df_demo['Check-in Date'] = pd.to_datetime(df_demo['Check-in Date'], errors='coerce')
    df_demo['Check-out Date'] = pd.to_datetime(df_demo['Check-out Date'], errors='coerce')
    df_demo['Booking Date'] = pd.to_datetime(df_demo['Booking Date'], errors='coerce')
    df_demo.dropna(subset=['Check-in Date', 'Check-out Date'], inplace=True)
    if not df_demo.empty:
        df_demo['Stay Duration'] = (df_demo['Check-out Date'] - df_demo['Check-in Date']).dt.days
        df_demo['Stay Duration'] = df_demo['Stay Duration'].apply(lambda x: max(0, x) if pd.notna(x) else 0)
    else: df_demo['Stay Duration'] = 0

    if 'Tổng thanh toán' in df_demo.columns and 'Stay Duration' in df_demo.columns:
        df_demo['Tổng thanh toán'] = pd.to_numeric(df_demo['Tổng thanh toán'], errors='coerce').fillna(0)
        df_demo['Giá mỗi đêm'] = np.where(
            (df_demo['Stay Duration'].notna()) & (df_demo['Stay Duration'] > 0) & (df_demo['Tổng thanh toán'].notna()),
            df_demo['Tổng thanh toán'] / df_demo['Stay Duration'],
            0.0
        ).round(0)
    else:
        df_demo['Giá mỗi đêm'] = 0.0

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
    Prepares various data aggregations for charts.
    """
    if df.empty:
        return {
            'monthly_revenue': pd.DataFrame(),
            'revenue_by_room': pd.DataFrame(),
            'revenue_by_party': pd.DataFrame()
        }

    # Doanh thu theo tháng
    monthly_revenue_df = pd.DataFrame()
    if 'Check-in' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Check-in']):
        monthly_revenue_df = df.resample('M', on='Check-in')['Price'].sum().reset_index()
        monthly_revenue_df['Check-in'] = monthly_revenue_df['Check-in'].dt.strftime('%Y-%m')

    # Doanh thu theo loại phòng
    revenue_by_room_df = df.groupby('Room Type')['Price'].sum().reset_index()

    # Doanh thu theo kênh bán
    revenue_by_party_df = df.groupby('Purchase Party')['Price'].sum().reset_index()

    return {
        'monthly_revenue': monthly_revenue_df,
        'revenue_by_room': revenue_by_room_df,
        'revenue_by_party': revenue_by_party_df
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

        # Lấy header để đảm bảo đúng thứ tự cột
        headers = worksheet.row_values(1)
        
        # Tạo list giá trị theo đúng thứ tự header
        row_to_append = [new_booking_data.get(header, "") for header in headers]
        
        worksheet.append_row(row_to_append, value_input_option='USER_ENTERED')
        print("Đã thêm đặt phòng mới vào Google Sheet thành công.")

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Lỗi: Không tìm thấy Google Sheet với ID '{sheet_id}'.")
        raise
    except Exception as e:
        print(f"Lỗi không xác định khi ghi vào Google Sheet: {e}")
        raise 