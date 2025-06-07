import os
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
import json
from functools import lru_cache
from pathlib import Path
import pandas as pd
import plotly
import plotly.express as px
import calendar
from datetime import datetime
import google.generativeai as genai

# Import các hàm logic
from logic import (
    import_from_gsheet, create_demo_data, prepare_charts_data, 
    get_month_activities, extract_booking_info_from_image_content,
    append_booking_to_sheet,
    get_message_templates, add_message_template,
    find_booking_by_id, update_booking_in_sheet, delete_booking_from_sheet
)

# Cấu hình đường dẫn và secrets
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Lấy API Key từ biến môi trường và cấu hình Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
else:
    print("CẢNH BÁO: GOOGLE_API_KEY không được tìm thấy. Tính năng thêm từ ảnh sẽ không hoạt động.")

# Khởi tạo ứng dụng Flask
app = Flask(__name__, template_folder=BASE_DIR / "templates", static_folder=BASE_DIR / "static")
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# KHỐI MÃ GỐC - KHÔNG CÓ BASE64
GCP_CREDS_JSON = os.getenv("GCP_CREDS_JSON")
DEFAULT_SHEET_ID = os.getenv("DEFAULT_SHEET_ID")
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME")
MESSAGE_TEMPLATE_WORKSHEET = os.getenv("MESSAGE_TEMPLATE_WORKSHEET")

# Define hotel capacity
TOTAL_CAPACITY = 10 

try:
    GCP_CREDS_DICT = json.loads(GCP_CREDS_JSON)
except Exception as e:
    print(f"Lỗi khi phân tích credentials JSON: {e}")
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
    
    # Chuẩn bị dữ liệu cho biểu đồ
    charts_data = prepare_charts_data(active_bookings)
    
    # Tạo biểu đồ và chuyển thành JSON
    fig_monthly = px.bar(charts_data['monthly_revenue'], x='Tháng', y='Tổng thanh toán', title='Doanh thu hàng tháng')
    monthly_chart_json = json.dumps(fig_monthly, cls=plotly.utils.PlotlyJSONEncoder)

    fig_room = px.pie(charts_data['room_revenue'], names='Tên chỗ nghỉ', values='Tổng thanh toán', title='Tỷ trọng Doanh thu theo Loại phòng', hole=0.3)
    room_chart_json = json.dumps(fig_room, cls=plotly.utils.PlotlyJSONEncoder)

    fig_collector = px.bar(charts_data['collector_revenue'], x='Người thu tiền', y='Tổng thanh toán', title='Doanh thu theo Người thu tiền')
    collector_chart_json = json.dumps(fig_collector, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template(
        'dashboard.html',
        total_bookings=total_bookings_count,
        active_bookings=active_bookings_count,
        monthly_revenue_chart=monthly_chart_json,
        room_revenue_chart=room_chart_json,
        collector_revenue_chart=collector_chart_json
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

@app.route('/calendar/')
@app.route('/calendar/<int:year>/<int:month>')
def calendar_view(year=None, month=None):
    if year is None or month is None:
        today = datetime.today()
        return redirect(url_for('calendar_view', year=today.year, month=today.month))

    df, _ = load_data()
    
    # SỬA LỖI: Gọi trực tiếp từ module, không cần tạo đối tượng Calendar
    month_matrix = calendar.monthcalendar(year, month)
    
    # Use the new logic function to get all activities for the month
    activities = get_month_activities(year, month, df, TOTAL_CAPACITY)

    # Calculate next and previous month for navigation
    current_date = datetime(year, month, 1)
    next_month_date = current_date + pd.DateOffset(months=1)
    prev_month_date = current_date - pd.DateOffset(months=1)

    return render_template(
        'calendar.html',
        month_matrix=month_matrix,
        year=year,
        month=month,
        month_name=calendar.month_name[month],
        activities=activities,
        next_year=next_month_date.year,
        next_month=next_month_date.month,
        prev_year=prev_month_date.year,
        prev_month=prev_month_date.month
    )

@app.route('/bookings/add_from_image', methods=['GET', 'POST'])
def add_from_image():
    if request.method == 'POST':
        if 'image_file' not in request.files:
            flash('Không có phần file nào', 'danger')
            return redirect(request.url)
        
        file = request.files['image_file']
        
        if file.filename == '':
            flash('Không có file nào được chọn', 'danger')
            return redirect(request.url)
            
        if file:
            image_bytes = file.read()
            extracted_data = extract_booking_info_from_image_content(image_bytes)
            
            if extracted_data is None:
                flash('Không thể trích xuất dữ liệu từ ảnh. Vui lòng thử lại.', 'danger')
                return render_template('add_from_image.html', extracted_data=None)

            # Convert data to JSON to pass to the template
            extracted_data_json = json.dumps(extracted_data)
            return render_template('add_from_image.html', extracted_data=extracted_data, extracted_data_json=extracted_data_json)
            
    return render_template('add_from_image.html', extracted_data=None)

@app.route('/bookings/save_extracted', methods=['POST'])
def save_extracted_bookings():
    extracted_data_json = request.form.get('extracted_data')
    if not extracted_data_json:
        flash('Không có dữ liệu để lưu.', 'danger')
        return redirect(url_for('add_from_image'))
        
    try:
        bookings_to_save = json.loads(extracted_data_json)
        
        # Get credentials and sheet info
        if not GCP_CREDS_DICT:
            flash('Credentials Google Cloud không được cấu hình. Không thể lưu.', 'danger')
            return redirect(url_for('add_from_image'))

        count = 0
        for booking in bookings_to_save:
            # Here you might want to add validation for each booking
            append_booking_to_sheet(booking, GCP_CREDS_DICT, DEFAULT_SHEET_ID, WORKSHEET_NAME)
            count += 1
            
        flash(f'Đã lưu thành công {count} đặt phòng mới!', 'success')
    except json.JSONDecodeError:
        flash('Lỗi xử lý dữ liệu. Vui lòng thử lại.', 'danger')
    except Exception as e:
        flash(f'Đã xảy ra lỗi khi lưu: {e}', 'danger')

    return redirect(url_for('view_bookings'))

@app.route('/templates', methods=['GET', 'POST'])
def manage_templates():
    if request.method == 'POST':
        subject = request.form.get('subject')
        label = request.form.get('label')
        content = request.form.get('content')

        if not subject or not content:
            flash('Chủ đề và Nội dung là bắt buộc.', 'warning')
        else:
            try:
                new_template = {'Subject': subject, 'Label': label, 'Content': content}
                add_message_template(
                    new_template, 
                    gcp_creds_dict=GCP_CREDS_DICT, 
                    sheet_id=DEFAULT_SHEET_ID, 
                    worksheet_name=MESSAGE_TEMPLATE_WORKSHEET
                )
                flash('Thêm mẫu tin nhắn thành công!', 'success')
            except Exception as e:
                flash(f'Lỗi khi thêm mẫu tin nhắn: {e}', 'danger')
        
        return redirect(url_for('manage_templates'))

    # SỬA LỖI: Gọi đúng hàm với đúng worksheet từ biến môi trường
    templates = get_message_templates(
        gcp_creds_dict=GCP_CREDS_DICT,
        sheet_id=DEFAULT_SHEET_ID,
        worksheet_name=MESSAGE_TEMPLATE_WORKSHEET
    )
    return render_template('templates.html', templates=templates)

# DYNAMIC ROUTES FOR BOOKING ACTIONS

@app.route('/booking/<booking_id>/edit', methods=['GET', 'POST'])
def edit_booking(booking_id):
    df, _ = load_data()
    booking_data = find_booking_by_id(df, booking_id)

    if not booking_data:
        flash(f'Không tìm thấy đặt phòng với ID {booking_id}.', 'warning')
        return redirect(url_for('view_bookings'))

    if request.method == 'POST':
        # Create a dictionary with all form data
        updated_data = request.form.to_dict()
        try:
            # The key for the sheet must match the booking ID from the URL
            success = update_booking_in_sheet(booking_id, updated_data, GCP_CREDS_DICT, DEFAULT_SHEET_ID, WORKSHEET_NAME)
            if success:
                flash(f'Đặt phòng {booking_id} đã được cập nhật thành công!', 'success')
            else:
                flash(f'Không thể cập nhật đặt phòng {booking_id}.', 'danger')
        except Exception as e:
            flash(f'Lỗi khi cập nhật đặt phòng: {e}', 'danger')
        
        return redirect(url_for('view_bookings'))

    # For GET request, show the form with existing data
    return render_template('edit_booking.html', booking=booking_data)

@app.route('/booking/<booking_id>/delete', methods=['POST'])
def delete_booking(booking_id):
    try:
        success = delete_booking_from_sheet(booking_id, GCP_CREDS_DICT, DEFAULT_SHEET_ID, WORKSHEET_NAME)
        if success:
            flash(f'Đặt phòng {booking_id} đã được xóa thành công!', 'success')
        else:
            flash(f'Không thể xóa đặt phòng {booking_id}. Nó có thể đã bị xóa hoặc không tồn tại.', 'warning')
    except Exception as e:
        flash(f'Lỗi khi xóa đặt phòng: {e}', 'danger')

    return redirect(url_for('view_bookings'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)