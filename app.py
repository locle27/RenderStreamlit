import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, abort
from dotenv import load_dotenv
import json
import pandas as pd
from functools import lru_cache
from pathlib import Path
import datetime
import plotly.express as px
import plotly.utils
from logic import (
    parse_app_standard_date,
    convert_display_date_to_app_format,
    get_cleaned_room_types,
    import_from_gsheet,
    upload_to_gsheet,
    create_demo_data,
    filter_data,
    calculate_kpis,
    append_booking_to_sheet,
    prepare_charts_data,
    find_booking_by_id,
    update_booking_in_sheet,
    delete_booking_from_sheet
)

# Cấu hình đường dẫn và secrets
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

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
def root():
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        if password == os.getenv('APP_PASSWORD'):
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Incorrect password")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    df, active_bookings = load_data()
    
    # Default values for filters
    start_date_str = request.args.get('start_date') or df['Check-in'].min().strftime('%Y-%m-%d')
    end_date_str = request.args.get('end_date') or df['Check-out'].max().strftime('%Y-%m-%d')
    room_types = request.args.getlist('room_type')
    purchase_parties = request.args.getlist('purchase_party')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)

    start_date = parse_app_standard_date(start_date_str)
    end_date = parse_app_standard_date(end_date_str)

    if not room_types:
        room_types = ['All']
    if not purchase_parties:
        purchase_parties = ['All']

    # Filter data
    filtered_df = filter_data(df, start_date, end_date, room_types, purchase_parties, min_price, max_price)

    # Calculate KPIs
    kpis = calculate_kpis(filtered_df)

    # Generate charts
    charts_data = prepare_charts_data(filtered_df)

    # Revenue by Room Type Chart
    if not charts_data['revenue_by_room'].empty:
        fig_room_type = px.pie(charts_data['revenue_by_room'], names='Room Type', values='Price', title='Doanh thu theo Loại phòng')
        revenue_by_room_type_chart = json.dumps(fig_room_type, cls=plotly.utils.PlotlyJSONEncoder)
    else:
        revenue_by_room_type_chart = None

    # Revenue by Purchase Party Chart
    if not charts_data['revenue_by_party'].empty:
        fig_purchase_party = px.pie(charts_data['revenue_by_party'], names='Purchase Party', values='Price', title='Doanh thu theo Kênh bán')
        revenue_by_purchase_party_chart = json.dumps(fig_purchase_party, cls=plotly.utils.PlotlyJSONEncoder)
    else:
        revenue_by_purchase_party_chart = None

    # Monthly Revenue Chart
    if not charts_data['monthly_revenue'].empty:
        fig_monthly_revenue = px.bar(charts_data['monthly_revenue'], x='Check-in', y='Price', title='Doanh thu hàng tháng')
        monthly_revenue_chart = json.dumps(fig_monthly_revenue, cls=plotly.utils.PlotlyJSONEncoder)
    else:
        monthly_revenue_chart = None
    
    # Get filter options
    all_room_types = get_cleaned_room_types(df)
    all_purchase_parties = df['Purchase Party'].unique().tolist()
    
    return render_template(
        'dashboard.html',
        kpis=kpis,
        revenue_by_room_type_chart=revenue_by_room_type_chart,
        revenue_by_purchase_party_chart=revenue_by_purchase_party_chart,
        monthly_revenue_chart=monthly_revenue_chart,
        all_room_types=all_room_types,
        all_purchase_parties=all_purchase_parties,
        start_date=start_date_str,
        end_date=end_date_str,
        selected_room_types=room_types,
        selected_purchase_parties=purchase_parties,
        min_price=min_price,
        max_price=max_price
    )

@app.route('/bookings')
def view_bookings():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

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

@app.route('/booking/<booking_id>/edit', methods=['GET', 'POST'])
def edit_booking(booking_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    df, _ = load_data()
    booking_data = find_booking_by_id(df, booking_id)

    if not booking_data:
        abort(404)

    if request.method == 'POST':
        try:
            form_data = request.form.to_dict()
            
            # Convert date formats back to Vietnamese style for the sheet
            for date_field in ['Ngày đến', 'Ngày đi', 'Được đặt vào']:
                if form_data.get(date_field):
                    date_obj = datetime.datetime.strptime(form_data[date_field], '%Y-%m-%d')
                    form_data[date_field] = f"ngày {date_obj.day} tháng {date_obj.month} năm {date_obj.year}"

            success = update_booking_in_sheet(
                booking_id=booking_id,
                updated_data=form_data,
                gcp_creds_dict=GCP_CREDS_DICT,
                sheet_id=DEFAULT_SHEET_ID,
                worksheet_name=WORKSHEET_NAME
            )

            if success:
                load_data.cache_clear()
                flash('Cập nhật đặt phòng thành công!', 'success')
            else:
                flash('Cập nhật đặt phòng thất bại.', 'danger')

            return redirect(url_for('view_bookings'))

        except Exception as e:
            print(f"Lỗi khi cập nhật đặt phòng: {e}")
            flash(f'Đã có lỗi xảy ra khi cập nhật: {e}', 'danger')
            return redirect(url_for('edit_booking', booking_id=booking_id))

    # For GET request, convert date format for the form
    for date_field in ['Ngày đến', 'Ngày đi', 'Được đặt vào']:
        if booking_data.get(date_field):
            parsed_date = parse_app_standard_date(booking_data[date_field])
            if parsed_date:
                booking_data[date_field] = parsed_date.strftime('%Y-%m-%d')

    return render_template('edit_booking.html', booking=booking_data)

@app.route('/bookings/add', methods=['GET', 'POST'])
def add_booking():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            # Lấy dữ liệu từ form
            form_data = request.form.to_dict()

            # Chuyển đổi định dạng ngày
            for date_field in ['Ngày đến', 'Ngày đi', 'Được đặt vào']:
                if form_data.get(date_field):
                    date_obj = datetime.datetime.strptime(form_data[date_field], '%Y-%m-%d')
                    form_data[date_field] = f"ngày {date_obj.day} tháng {date_obj.month} năm {date_obj.year}"

            # Gọi hàm để thêm dữ liệu vào Google Sheet
            append_booking_to_sheet(
                new_booking_data=form_data,
                gcp_creds_dict=GCP_CREDS_DICT,
                sheet_id=DEFAULT_SHEET_ID,
                worksheet_name=WORKSHEET_NAME
            )
            
            # Xóa cache để tải lại dữ liệu mới
            load_data.cache_clear()

            flash('Thêm đặt phòng mới thành công!', 'success')
            return redirect(url_for('view_bookings'))
        
        except Exception as e:
            print(f"Lỗi khi thêm đặt phòng: {e}")
            flash(f'Đã có lỗi xảy ra: {e}', 'danger')
            return redirect(url_for('add_booking'))

    return render_template('add_booking.html')

@app.route('/booking/<booking_id>/delete', methods=['POST'])
def delete_booking(booking_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        success = delete_booking_from_sheet(
            booking_id=booking_id,
            gcp_creds_dict=GCP_CREDS_DICT,
            sheet_id=DEFAULT_SHEET_ID,
            worksheet_name=WORKSHEET_NAME
        )
        if success:
            load_data.cache_clear()
            flash('Đặt phòng đã được xóa thành công!', 'success')
        else:
            flash('Xóa đặt phòng thất bại. Không tìm thấy ID.', 'danger')
    except Exception as e:
        print(f"Lỗi khi xóa đặt phòng: {e}")
        flash(f'Đã có lỗi xảy ra khi xóa: {e}', 'danger')

    return redirect(url_for('view_bookings'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('data', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 