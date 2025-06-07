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
import calendar
from io import BytesIO
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
    if 'Check-out Date' in df.columns:
        df['Check-out Date'] = pd.to_datetime(df['Check-out Date'], errors='coerce')
        
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
        'Ngày đến': ['2025-05-22', '2025-05-23', '2025-05-26', '2025-06-01'],
        'Ngày đi': ['2025-05-23', '2025-05-24', '2025-05-28', '2025-06-05'],
        'Tình trạng': ['OK', 'OK', 'OK', 'OK'],
        'Tổng thanh toán': [300000, 450000, 600000, 1200000],
        'Số đặt phòng': [f'DEMO{i+1:09d}' for i in range(4)],
        'Người thu tiền': ['LOC LE', 'THAO LE', 'THAO LE', 'LOC LE']
    }
    df_demo = pd.DataFrame(demo_data)
    df_demo['Check-in Date'] = pd.to_datetime(df_demo['Ngày đến'], errors='coerce')
    df_demo['Check-out Date'] = pd.to_datetime(df_demo['Ngày đi'], errors='coerce')
    df_demo['Tổng thanh toán'] = pd.to_numeric(df_demo['Tổng thanh toán'], errors='coerce').fillna(0)
    active_bookings_demo = df_demo[df_demo['Tình trạng'] != 'Đã hủy'].copy()
    return df_demo, active_bookings_demo

def export_data_to_new_sheet(df: pd.DataFrame, gcp_creds_dict: dict, sheet_id: str) -> str:
    """Exports a DataFrame to a new worksheet in the specified spreadsheet."""
    print("Bắt đầu quá trình export...")
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(gcp_creds_dict, scopes=scope)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(sheet_id)

    worksheet_name = f"Export_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    
    df_str = df.astype(str)
    
    new_worksheet = spreadsheet.add_worksheet(
        title=worksheet_name, 
        rows=str(len(df_str) + 1), 
        cols=str(df_str.shape[1])
    )

    data_to_write = [df_str.columns.values.tolist()] + df_str.values.tolist()
    new_worksheet.update(data_to_write, 'A1')
    print(f"Export thành công ra sheet: {worksheet_name}")
    
    return worksheet_name

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
    if df.empty:
        return {
            'monthly_revenue': pd.DataFrame(columns=['Tháng', 'Tổng thanh toán']),
            'room_revenue': pd.DataFrame(columns=['Tên chỗ nghỉ', 'Tổng thanh toán']),
            'collector_revenue': pd.DataFrame(columns=['Người thu tiền', 'Tổng thanh toán'])
        }

    required_cols = {
        'Check-in Date': 'datetime64[ns]', 'Tổng thanh toán': 'float64',
        'Tên chỗ nghỉ': 'object', 'Người thu tiền': 'object'
    }
    
    for col, dtype in required_cols.items():
        if col not in df.columns:
            if 'datetime' in dtype: df[col] = pd.NaT
            elif 'float' in dtype: df[col] = 0.0
            else: df[col] = 'N/A'
        if 'datetime' in dtype: df[col] = pd.to_datetime(df[col], errors='coerce')
        elif 'float' in dtype: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df_monthly = df.dropna(subset=['Check-in Date']).copy()
    df_monthly['Tháng'] = df_monthly['Check-in Date'].dt.to_period('M').astype(str)
    monthly_revenue = df_monthly.groupby('Tháng')['Tổng thanh toán'].sum().reset_index()
    monthly_revenue = monthly_revenue.sort_values('Tháng')

    room_revenue = df.groupby('Tên chỗ nghỉ')['Tổng thanh toán'].sum().reset_index()
    room_revenue = room_revenue.sort_values('Tổng thanh toán', ascending=False)

    collector_revenue = df.groupby('Người thu tiền')['Tổng thanh toán'].sum().reset_index()
    collector_revenue = collector_revenue.sort_values('Tổng thanh toán', ascending=False)

    return {
        'monthly_revenue': monthly_revenue, 'room_revenue': room_revenue,
        'collector_revenue': collector_revenue
    }

def append_booking_to_sheet(new_booking_data: list, gcp_creds_dict: dict, sheet_id: str, worksheet_name: str) -> None:
    """Appends a new booking row to the specified Google Sheet."""
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ]
    creds = Credentials.from_service_account_info(gcp_creds_dict, scopes=scope)
    gc = gspread.authorize(creds)
    
    try:
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.worksheet(worksheet_name)
        worksheet.append_row(new_booking_data, value_input_option='USER_ENTERED')
        print(f"Đã thêm hàng mới vào sheet: {worksheet_name}")
    except Exception as e:
        print(f"Lỗi khi thêm hàng vào Google Sheet: {e}")
        raise

# ==============================================================================
# AI AND IMAGE PROCESSING FUNCTIONS
# ==============================================================================

def extract_booking_info_from_image_content(image_bytes: bytes) -> List[Dict[str, Any]]:
    try:
        img = Image.open(BytesIO(image_bytes))
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = """
        Bạn là một trợ lý nhập liệu chuyên nghiệp cho khách sạn, có nhiệm vụ trích xuất thông tin từ một hình ảnh.
        Hình ảnh này có thể chứa một bảng hoặc danh sách của NHIỀU đặt phòng.
        Nhiệm vụ của bạn:
        1. Quét toàn bộ hình ảnh và xác định từng hàng (mỗi hàng là một đặt phòng riêng biệt).
        2. Với MỖI đặt phòng, hãy trích xuất các thông tin sau.
        3. Trả về kết quả dưới dạng một MẢNG JSON (JSON array), trong đó mỗi phần tử của mảng là một đối tượng JSON đại diện cho một đặt phòng.
        Cấu trúc của mỗi đối tượng JSON trong mảng phải như sau:
        - "guest_name" (string): Họ và tên đầy đủ của khách.
        - "booking_id" (string): Mã số đặt phòng.
        - "check_in_date" (string): Ngày nhận phòng theo định dạng YYYY-MM-DD.
        - "check_out_date" (string): Ngày trả phòng theo định dạng YYYY-MM-DD.
        - "room_type" (string): Tên loại phòng đã đặt.
        - "total_payment" (number): Tổng số tiền thanh toán (chỉ lấy số).
        - "commission" (number): Tiền hoa hồng, nếu có (chỉ lấy số).
        YÊU CẦU CỰC KỲ QUAN TRỌNG:
        - Kết quả cuối cùng PHẢI là một mảng JSON, ví dụ: [ { ...booking1... }, { ...booking2... } ].
        - Chỉ trả về đối tượng JSON thô, không kèm theo bất kỳ văn bản giải thích hay định dạng markdown nào như ```json.
        - Nếu không tìm thấy thông tin cho trường nào, hãy đặt giá trị là null.
        """
        response = model.generate_content([prompt, img], stream=False)
        response.resolve()
        
        json_text = response.text.strip().replace('```json', '').replace('```', '').strip()
        list_of_bookings_data = json.loads(json_text)
        
        if isinstance(list_of_bookings_data, dict):
            list_of_bookings_data = [list_of_bookings_data]
            
        return list_of_bookings_data

    except json.JSONDecodeError:
        return [{"error": "Lỗi: AI trả về định dạng JSON không hợp lệ."}]
    except Exception as e:
        return [{"error": f"Lỗi không xác định khi xử lý ảnh: {str(e)}"}]

# ==============================================================================
# CALENDAR LOGIC FUNCTIONS
# ==============================================================================

def get_daily_activity(date_to_check: datetime.date, df: pd.DataFrame) -> dict:
    df['Check-in Date'] = pd.to_datetime(df['Check-in Date']).dt.date
    df['Check-out Date'] = pd.to_datetime(df['Check-out Date']).dt.date
    
    check_ins = df[df['Check-in Date'] == date_to_check]
    check_outs = df[df['Check-out Date'] == date_to_check]
    
    return {
        'check_in': check_ins.to_dict(orient='records'),
        'check_out': check_outs.to_dict(orient='records')
    }

def get_overall_calendar_day_info(date_to_check: datetime.date, df: pd.DataFrame, total_capacity: int) -> dict:
    df['Check-in Date'] = pd.to_datetime(df['Check-in Date']).dt.date
    df['Check-out Date'] = pd.to_datetime(df['Check-out Date']).dt.date
    
    active_on_date = df[
        (df['Check-in Date'] <= date_to_check) & (df['Check-out Date'] > date_to_check)
    ]
    occupied_units = len(active_on_date)
    available_units = max(0, total_capacity - occupied_units)
    
    return {
        'occupied_units': occupied_units,
        'available_units': available_units,
        'status_text': f"{available_units}/{total_capacity} trống"
    }

def get_month_activities(year: int, month: int, df: pd.DataFrame, total_capacity: int) -> Dict[int, Dict[str, Any]]:
    """
    Computes daily activities, check-ins, check-outs, and occupancy for a given month.
    """
    month_days = calendar.monthcalendar(year, month)
    activities = {}

    for week in month_days:
        for day in week:
            if day == 0:
                continue
            
            current_date = datetime.date(year, month, day)
            activities[day] = get_overall_calendar_day_info(current_date, df, total_capacity)
            
    return activities

# ==============================================================================
# MESSAGE TEMPLATE FUNCTIONS
# ==============================================================================

def get_message_templates(gcp_creds_dict: dict, sheet_id: str, worksheet_name: str) -> list:
    """Đọc dữ liệu từ sheet Mẫu Tin Nhắn."""
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(gcp_creds_dict, scopes=scope)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.worksheet(worksheet_name)
        # get_all_records sẽ trả về một list các dictionary, rất tiện lợi
        return worksheet.get_all_records()
    except Exception as e:
        print(f"Lỗi khi đọc mẫu tin nhắn: {e}")
        return []

def add_message_template(new_template_data: Dict[str, str], gcp_creds_dict: dict, sheet_id: str, worksheet_name: str) -> None:
    """
    Appends a new message template to the specified Google Sheet.
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