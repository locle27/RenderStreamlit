import os
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
import json
from functools import lru_cache
from pathlib import Path
import pandas as pd
import plotly
import plotly.express as px

# Import các hàm logic
from logic import (
    import_from_gsheet, create_demo_data, prepare_charts_data,
    append_booking_to_sheet, find_booking_by_id,
    update_booking_in_sheet, delete_booking_from_sheet
)

# Cấu hình đường dẫn và secrets
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Khởi tạo ứng dụng Flask
app = Flask(__name__, template_folder=BASE_DIR / "templates", static_folder=BASE_DIR / "static")
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Lấy thông tin xác thực
GCP_CREDS_JSON = os.getenv("GCP_CREDS_JSON")
DEFAULT_SHEET_ID = os.getenv("DEFAULT_SHEET_ID")
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME")

try:
    GCP_CREDS_DICT = json.loads(GCP_CREDS_JSON)
except Exception:
    GCP_CREDS_DICT = None

@lru_cache(maxsize=1)
def load_data():
    print("Đang tải dữ liệu...")
    try:
        if not GCP_CREDS_DICT: raise ValueError("Credentials không hợp lệ")
        df = import_from_gsheet(DEFAULT_SHEET_ID, GCP_CREDS_DICT, WORKSHEET_NAME)
        if df.empty: raise ValueError("Sheet trống")
        active_bookings = df[df['Tình trạng'] != 'Đã hủy'].copy()
        return df, active_bookings
    except Exception as e:
        print(f"Lỗi tải dữ liệu: {e}. Dùng dữ liệu demo.")
        return create_demo_data()

@app.route('/')
def dashboard():
    df, active_bookings = load_data()
    
    # Dữ liệu cho các card
    total_bookings_count = len(df)
    active_bookings_count = len(active_bookings)
    
    # Dữ liệu cho biểu đồ
    charts_data = prepare_charts_data(active_bookings)
    
    # Tạo biểu đồ và chuyển thành JSON
    fig_monthly = px.bar(charts_data['monthly_revenue'], x='Month', y='Total Payment', title='Doanh thu hàng tháng')
    monthly_chart_json = json.dumps(fig_monthly, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template(
        'dashboard.html',
        total_bookings=total_bookings_count,
        active_bookings=active_bookings_count,
        monthly_revenue_chart=monthly_chart_json
    )

@app.route('/bookings')
def view_bookings():
    df, _ = load_data()
    search_term = request.args.get('search_term', '').strip().lower()
    
    if search_term:
        df_filtered = df[
            df['Tên người đặt'].str.lower().str.contains(search_term, na=False) |
            df['Số đặt phòng'].str.lower().str.contains(search_term, na=False)
        ]
    else:
        df_filtered = df
        
    bookings_list = df_filtered.to_dict(orient='records')
    return render_template('bookings.html', bookings=bookings_list, search_term=search_term, booking_count=len(bookings_list))

@app.route('/bookings/add', methods=['GET', 'POST'])
def add_booking():
    if request.method == 'POST':
        # Lấy dữ liệu từ form
        new_booking_data = {
            'Tên người đặt': request.form.get('guest_name'),
            'Số đặt phòng': request.form.get('booking_id'),
            # Thêm các trường khác từ form của bạn
        }
        # (Thêm logic xác thực dữ liệu ở đây)
        
        try:
            append_booking_to_sheet(new_booking_data)
            flash('Thêm đặt phòng thành công!', 'success')
        except Exception as e:
            flash(f'Lỗi khi thêm đặt phòng: {e}', 'danger')
            
        return redirect(url_for('view_bookings'))
        
    return render_template('add_booking.html')

# Thêm các route cho edit và delete ở đây...

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)