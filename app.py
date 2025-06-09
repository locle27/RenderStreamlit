import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from dotenv import load_dotenv
import json
from functools import lru_cache
from pathlib import Path
import pandas as pd
import plotly
import plotly.express as px
from datetime import datetime, timedelta
import calendar
import base64
import google.generativeai as genai
from io import BytesIO

# --- Cài đặt Chế độ ---
# Đặt thành True để bật thanh công cụ dev và chế độ debug.
# Đặt thành False để chạy ở chế độ production (tắt thanh công cụ).
DEV_MODE = True  # Bật development mode để tự động reload
# --------------------

# Import các hàm logic
from logic import (
    import_from_gsheet, create_demo_data,
    get_daily_activity, get_overall_calendar_day_info,
    extract_booking_info_from_image_content,
    export_data_to_new_sheet,
    append_multiple_bookings_to_sheet,
    delete_booking_by_id, update_row_in_gsheet,
    prepare_dashboard_data, delete_row_in_gsheet,
    delete_multiple_rows_in_gsheet,
    import_message_templates_from_gsheet,
    export_message_templates_to_gsheet
)

# Cấu hình
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__, template_folder=BASE_DIR / "templates", static_folder=BASE_DIR / "static")

# Sử dụng biến DEV_MODE để cấu hình app
app.config['ENV'] = 'production'  # Luôn sử dụng production mode
app.config['DEBUG'] = False  # Luôn tắt debug mode
app.secret_key = os.getenv("FLASK_SECRET_KEY", "a_default_secret_key_for_development")

# Vô hiệu hóa Debug Toolbar - Đã hoàn toàn bị xóa
# KHÔNG import hoặc sử dụng DebugToolbarExtension

@app.context_processor
def inject_dev_mode():
    return dict(dev_mode=app.config['DEBUG'])

@app.context_processor
def inject_pandas():
    return dict(pd=pd)

# --- Lấy thông tin từ .env ---
GCP_CREDS_FILE_PATH = os.getenv("GCP_CREDS_FILE_PATH")
DEFAULT_SHEET_ID = os.getenv("DEFAULT_SHEET_ID")
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TOTAL_HOTEL_CAPACITY = 4

# --- Khởi tạo ---
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# --- Hàm chính để tải dữ liệu ---
@lru_cache(maxsize=1)
def load_data():
    print("Đang tải dữ liệu đặt phòng từ nguồn...")
    try:
        df = import_from_gsheet(DEFAULT_SHEET_ID, GCP_CREDS_FILE_PATH, WORKSHEET_NAME)
        if df.empty:
            raise ValueError("Sheet đặt phòng trống hoặc không thể truy cập.")
        active_bookings = df[df['Tình trạng'] != 'Đã hủy'].copy()
        print("Tải dữ liệu từ Google Sheet thành công!")
        return df, active_bookings
    except Exception as e:
        print(f"Lỗi tải dữ liệu đặt phòng: {e}. Dùng dữ liệu demo.")
        df_demo, active_bookings_demo = create_demo_data()
        return df_demo, active_bookings_demo

# --- CÁC ROUTE CỦA ỨNG DỤNG ---

@app.route('/')
def dashboard():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not start_date_str or not end_date_str:
        # === PHẦN SỬA LỖI QUAN TRỌNG ===
        # Lấy ngày và giờ hiện tại, sau đó chỉ lấy phần ngày
        today_full = datetime.today()
        start_date = today_full.replace(day=1)
        _, last_day = calendar.monthrange(today_full.year, today_full.month)
        end_date = today_full.replace(day=last_day)
    else:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    df, _ = load_data()
    
    # Gọi hàm logic với các tham số sắp xếp
    sort_by = request.args.get('sort_by', 'Tháng')
    sort_order = request.args.get('sort_order', 'desc')
    dashboard_data = prepare_dashboard_data(df, start_date, end_date, sort_by, sort_order)

    # Chuẩn bị dữ liệu cho template
    monthly_revenue_list = dashboard_data.get('monthly_revenue_all_time', pd.DataFrame()).to_dict('records')
    genius_stats_list = dashboard_data.get('genius_stats', pd.DataFrame()).to_dict('records')
    monthly_guests_list = dashboard_data.get('monthly_guests_all_time', pd.DataFrame()).to_dict('records')
    weekly_guests_list = dashboard_data.get('weekly_guests_all_time', pd.DataFrame()).to_dict('records')
    monthly_collected_revenue_list = dashboard_data.get('monthly_collected_revenue', pd.DataFrame()).to_dict('records')

    # Tạo biểu đồ doanh thu hàng tháng với thiết kế đẹp hơn
    monthly_revenue_df = pd.DataFrame(monthly_revenue_list)
    monthly_revenue_chart_json = {}
    
    if not monthly_revenue_df.empty:
        # Sắp xếp lại theo tháng để biểu đồ đường đúng thứ tự
        monthly_revenue_df_sorted = monthly_revenue_df.sort_values('Tháng')
        
        # Tạo biểu đồ combo: line + bar
        fig = px.line(monthly_revenue_df_sorted, x='Tháng', y='Doanh thu', 
                     title='📊 Doanh thu Hàng tháng', markers=True)
        
        # Thêm bar chart cho cùng dữ liệu
        fig.add_bar(x=monthly_revenue_df_sorted['Tháng'], 
                   y=monthly_revenue_df_sorted['Doanh thu'],
                   name='Doanh thu',
                   opacity=0.3,
                   yaxis='y')
        
        # Cải thiện layout
        fig.update_layout(
            title={
                'text': '📊 Doanh thu Hàng tháng (Tất cả thời gian)', 
                'x': 0.5,
                'font': {'size': 18, 'family': 'Arial, sans-serif', 'color': '#2c3e50'}
            },
            xaxis_title='Tháng',
            yaxis_title='Doanh thu (VND)',
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font={'family': 'Arial, sans-serif', 'size': 12},
            margin=dict(l=60, r=30, t=80, b=50),
            height=400,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Cải thiện axes
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            showline=True,
            linewidth=1,
            linecolor='rgba(128,128,128,0.5)'
        )
        
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            showline=True,
            linewidth=1,
            linecolor='rgba(128,128,128,0.5)',
            tickformat=',.0f'
        )
        
        # Cải thiện line traces
        fig.update_traces(
            line=dict(width=3, color='#3498db'),
            marker=dict(size=8, color='#e74c3c', line=dict(width=2, color='white')),
            selector=dict(type='scatter')
        )
        
        # Cải thiện bar traces  
        fig.update_traces(
            marker=dict(color='#3498db', opacity=0.3),
            selector=dict(type='bar')
        )
        
        monthly_revenue_chart_json = json.loads(fig.to_json())

    # Tạo biểu đồ pie chart đẹp hơn cho người thu tiền
    collector_revenue_data = dashboard_data.get('collector_revenue_selected', pd.DataFrame()).to_dict('records')
    
    collector_chart_data = {
        'data': [{
            'type': 'pie',
            'labels': [row['Người thu tiền'] for row in collector_revenue_data],
            'values': [row['Tổng thanh toán'] for row in collector_revenue_data],
            'textinfo': 'label+percent+value',
            'textposition': 'auto',
            'hovertemplate': '<b>%{label}</b><br>' +
                           'Doanh thu: %{value:,.0f}đ<br>' +
                           'Tỷ lệ: %{percent}<br>' +
                           '<extra></extra>',
            'marker': {
                'colors': ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c'],
                'line': {
                    'color': '#ffffff',
                    'width': 2
                }
            },
            'hole': 0.4,  # Tạo donut chart
            'textfont': {
                'size': 12,
                'family': 'Arial, sans-serif'
            }
        }],
        'layout': {
            'title': {
                'text': '💰 Doanh thu theo Người thu tiền',
                'x': 0.5,
                'font': {
                    'size': 16,
                    'family': 'Arial, sans-serif',
                    'color': '#2c3e50'
                }
            },
            'showlegend': True,
            'legend': {
                'orientation': 'v',
                'x': 1.02,
                'y': 0.5,
                'font': {
                    'size': 11,
                    'family': 'Arial, sans-serif'
                }
            },
            'height': 350,
            'margin': {'l': 20, 'r': 100, 't': 60, 'b': 20},
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'font': {
                'family': 'Arial, sans-serif',
                'size': 12,
                'color': '#2c3e50'
            }
        }
    }

    collector_revenue_list = dashboard_data.get('collector_revenue_selected', pd.DataFrame()).to_dict('records')

    return render_template(
        'dashboard.html',
        total_revenue=dashboard_data.get('total_revenue_selected', 0),
        total_guests=dashboard_data.get('total_guests_selected', 0),
        monthly_revenue_list=monthly_revenue_list,
        genius_stats_list=genius_stats_list,
        monthly_guests_list=monthly_guests_list,
        weekly_guests_list=weekly_guests_list,
        monthly_collected_revenue_list=monthly_collected_revenue_list,
        monthly_revenue_chart_json=monthly_revenue_chart_json,
        collector_chart_json=collector_chart_data,
        collector_revenue_list=collector_revenue_list,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        current_sort_by=sort_by,
        current_sort_order=sort_order
    )

@app.route('/bookings')
def view_bookings():
    df, _ = load_data()
    
    # Lấy tham số từ URL
    search_term = request.args.get('search_term', '').strip().lower()
    sort_by = request.args.get('sort_by', 'Check-in Date') # Mặc định sắp xếp
    order = request.args.get('order', 'desc') # Mặc định giảm dần

    # Lọc theo từ khóa tìm kiếm
    if search_term:
        df = df[df.apply(lambda row: search_term in str(row).lower(), axis=1)]

    # Sắp xếp dữ liệu
    if sort_by in df.columns:
        ascending = order == 'asc'
        df = df.sort_values(by=sort_by, ascending=ascending)
    
    bookings_list = df.to_dict(orient='records')
    
    return render_template('bookings.html', 
                         bookings=bookings_list, 
                         search_term=search_term, 
                         booking_count=len(bookings_list),
                         current_sort_by=sort_by,
                         current_order=order)

@app.route('/calendar/')
@app.route('/calendar/<int:year>/<int:month>')
def calendar_view(year=None, month=None):
    today = datetime.today()
    if year is None or month is None:
        return redirect(url_for('calendar_view', year=today.year, month=today.month))
    
    current_month_start = datetime(year, month, 1)
    prev_month_date = (current_month_start.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_month_date = (current_month_start.replace(day=1) + timedelta(days=32)).replace(day=1)

    df, _ = load_data()
    month_activities = {}
    month_matrix = calendar.monthcalendar(year, month)
    
    calendar_data = []
    for week in month_matrix:
        week_data = []
        for day in week:
            if day != 0:
                current_date = datetime(year, month, day).date()
                date_str = current_date.strftime('%Y-%m-%d')
                day_info = get_overall_calendar_day_info(current_date, df, TOTAL_HOTEL_CAPACITY)
                week_data.append((current_date, date_str, day_info))
            else:
                week_data.append((None, None, None))
        calendar_data.append(week_data)

    return render_template(
        'calendar.html',
        calendar_data=calendar_data,
        current_month=current_month_start,
        prev_month=prev_month_date,
        next_month=next_month_date,
        today=today.date()
    )

@app.route('/calendar/details/<string:date_str>')
def calendar_details(date_str):
    try:
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Định dạng ngày không hợp lệ.", "danger")
        return redirect(url_for('calendar_view'))
    df, _ = load_data()
    activities = get_daily_activity(parsed_date, df)
    return render_template('calendar_details.html',
                           date=parsed_date.strftime('%d/%m/%Y'),
                           check_in=activities.get('check_in', []),
                           check_out=activities.get('check_out', []),
                           staying_over=activities.get('staying_over', []),
                           current_date=parsed_date)
    
@app.route('/bookings/add_from_image', methods=['GET'])
def add_from_image_page():
    return render_template('add_from_image.html')

@app.route('/api/process_pasted_image', methods=['POST'])
def process_pasted_image():
    data = request.get_json()
    if not data or 'image_b64' not in data:
        return jsonify({"error": "Yêu cầu không chứa dữ liệu ảnh."}), 400
    try:
        image_header, image_b64_data = data['image_b64'].split(',', 1)
        image_bytes = base64.b64decode(image_b64_data)
        extracted_data = extract_booking_info_from_image_content(image_bytes)
        return jsonify(extracted_data)
    except Exception as e:
        return jsonify({"error": f"Lỗi xử lý phía server: {str(e)}"}), 500

@app.route('/bookings/sync')
def sync_bookings():
    """
    Đây là nơi ĐÚNG và DUY NHẤT để gọi cache_clear.
    """
    try:
        load_data.cache_clear()
        flash('Dữ liệu đã được đồng bộ lại từ Google Sheets.', 'info')
        print("Cache đã được xóa thành công qua nút Đồng bộ.")
    except Exception as e:
        flash(f'Lỗi khi xóa cache: {e}', 'danger')

    return redirect(url_for('view_bookings'))

@app.route('/bookings/export')
def export_bookings():
    try:
        df, _ = load_data()
        if not df.empty:
            worksheet_name = export_data_to_new_sheet(df, GCP_CREDS_FILE_PATH, DEFAULT_SHEET_ID)
            flash(f'Đã export dữ liệu thành công ra sheet mới: "{worksheet_name}"', 'success')
        else:
            flash('Không có dữ liệu để export.', 'warning')
    except Exception as e:
        flash(f'Lỗi khi export dữ liệu: {e}', 'danger')
    return redirect(url_for('view_bookings'))
    
@app.route('/bookings/save_extracted', methods=['POST'])
def save_extracted_bookings():
    try:
        extracted_json_str = request.form.get('extracted_json')
        if not extracted_json_str:
            flash('Không có dữ liệu để lưu.', 'warning')
            return redirect(url_for('add_from_image_page'))

        bookings_to_save = json.loads(extracted_json_str)
        
        formatted_bookings = []
        for booking in bookings_to_save:
            if 'error' in booking: continue
            formatted_bookings.append({
                'Tên người đặt': booking.get('guest_name'),
                'Số đặt phòng': booking.get('booking_id'),
                'Check-in Date': booking.get('check_in_date'),
                'Check-out Date': booking.get('check_out_date'),
                'Tên chỗ nghỉ': booking.get('room_type'),
                'Tổng thanh toán': booking.get('total_payment'),
                'Tình trạng': 'OK'
            })

        if formatted_bookings:
            append_multiple_bookings_to_sheet(
                bookings=formatted_bookings,
                gcp_creds_file_path=GCP_CREDS_FILE_PATH,
                sheet_id=DEFAULT_SHEET_ID,
                worksheet_name=WORKSHEET_NAME
            )
            # === SỬA LỖI QUAN TRỌNG: Xóa cache sau khi thêm ===
            load_data.cache_clear()
            flash(f'Đã lưu thành công {len(formatted_bookings)} đặt phòng mới!', 'success')
        else:
            flash('Không có đặt phòng hợp lệ nào để lưu.', 'info')

    except Exception as e:
        flash(f'Lỗi khi lưu các đặt phòng đã trích xuất: {e}', 'danger')
        
    return redirect(url_for('view_bookings'))

@app.route('/booking/<booking_id>/edit', methods=['GET', 'POST'])
def edit_booking(booking_id):
    df, _ = load_data()
    booking = df[df['Số đặt phòng'] == booking_id].to_dict('records')[0] if not df.empty else {}
    
    if request.method == 'POST':
        new_data = {
            'Tên người đặt': request.form.get('Tên người đặt'),
            'Tên chỗ nghỉ': request.form.get('Tên chỗ nghỉ'),
            'Check-in Date': request.form.get('Check-in Date'),
            'Check-out Date': request.form.get('Check-out Date'),
            'Tổng thanh toán': request.form.get('Tổng thanh toán'),
            'Tình trạng': request.form.get('Tình trạng'),
            'Người thu tiền': request.form.get('Người thu tiền'),
        }
        
        success = update_row_in_gsheet(
            sheet_id=DEFAULT_SHEET_ID,
            gcp_creds_file_path=GCP_CREDS_FILE_PATH,
            worksheet_name=WORKSHEET_NAME,
            booking_id=booking_id,
            new_data=new_data
        )
        
        if success:
            # Xóa cache để tải lại dữ liệu mới
            load_data.cache_clear()
            flash('Đã cập nhật đặt phòng thành công!', 'success')
        else:
            flash('Có lỗi xảy ra khi cập nhật đặt phòng trên Google Sheet.', 'danger')
            
        return redirect(url_for('view_bookings'))
        
    return render_template('edit_booking.html', booking=booking)

@app.route('/booking/<booking_id>/delete', methods=['POST'])
def delete_booking(booking_id):
    success = delete_row_in_gsheet(
        sheet_id=DEFAULT_SHEET_ID,
        gcp_creds_file_path=GCP_CREDS_FILE_PATH,
        worksheet_name=WORKSHEET_NAME,
        booking_id=booking_id
    )
    
    if success:
        flash(f'Đã xóa thành công đặt phòng có ID: {booking_id}', 'success')
        load_data.cache_clear() # Xóa cache sau khi sửa đổi
    else:
        flash('Lỗi khi xóa đặt phòng.', 'danger')
    return redirect(url_for('view_bookings'))

@app.route('/bookings/delete_multiple', methods=['POST'])
def delete_multiple_bookings():
    data = request.get_json()
    ids_to_delete = data.get('ids')

    if not ids_to_delete:
        return jsonify({'success': False, 'message': 'Không có ID nào được cung cấp.'})

    try:
        success = delete_multiple_rows_in_gsheet(
            sheet_id=DEFAULT_SHEET_ID,
            gcp_creds_file_path=GCP_CREDS_FILE_PATH,
            worksheet_name=WORKSHEET_NAME,
            booking_ids=ids_to_delete
        )
        if success:
            load_data.cache_clear() # Xóa cache sau khi sửa đổi
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Lỗi khi xóa dữ liệu trên Google Sheets.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/templates')
def get_templates_page():
    """Trả về trang HTML cho quản lý templates"""
    return render_template('templates.html')

@app.route('/api/templates/debug')
def debug_templates():
    """Debug endpoint to check templates data"""
    templates_path = BASE_DIR / 'message_templates.json'
    
    debug_info = {
        'file_exists': templates_path.exists(),
        'file_path': str(templates_path),
        'file_size': templates_path.stat().st_size if templates_path.exists() else 0,
        'templates_count': 0,
        'sample_template': None,
        'error': None
    }
    
    try:
        if templates_path.exists():
            with open(templates_path, 'r', encoding='utf-8') as f:
                content = f.read()
                debug_info['file_content_length'] = len(content)
                
                templates = json.loads(content)
                debug_info['templates_count'] = len(templates)
                debug_info['templates_type'] = type(templates).__name__
                
                if templates:
                    debug_info['sample_template'] = templates[0]
                    debug_info['all_categories'] = list(set(t.get('Category', 'NO_CATEGORY') for t in templates))
                    
    except Exception as e:
        debug_info['error'] = str(e)
        
    return jsonify(debug_info)

@app.route('/api/templates')
def get_templates_api():
    """API endpoint trả về JSON data của templates"""
    templates_path = BASE_DIR / 'message_templates.json'
    try:
        print(f"DEBUG: Looking for templates file at: {templates_path}")
        
        if not templates_path.exists():
            print("DEBUG: Templates file does not exist")
            return jsonify([])
            
        with open(templates_path, 'r', encoding='utf-8') as f:
            templates = json.load(f)
            
        print(f"DEBUG: Successfully loaded {len(templates)} templates from file")
        
        # Validate templates data
        if not isinstance(templates, list):
            print("DEBUG: Templates data is not a list")
            return jsonify([])
            
        # Ensure each template has required fields
        valid_templates = []
        for i, template in enumerate(templates):
            if isinstance(template, dict) and 'Category' in template:
                valid_templates.append(template)
                print(f"DEBUG: Template {i}: Category='{template.get('Category')}', Label='{template.get('Label')}'")
            else:
                print(f"DEBUG: Skipping invalid template at index {i}: {template}")
        
        print(f"DEBUG: Returning {len(valid_templates)} valid templates")
        return jsonify(valid_templates)
        
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"DEBUG: Error loading templates: {e}")
        return jsonify([])
    except Exception as e:
        print(f"DEBUG: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/save_templates', methods=['POST'])
def save_templates_api():
    templates_path = BASE_DIR / 'message_templates.json'
    templates = request.get_json()
    with open(templates_path, 'w', encoding='utf-8') as f:
        json.dump(templates, f, ensure_ascii=False, indent=4)
    return jsonify({'success': True, 'message': 'Đã lưu các mẫu tin nhắn.'})

@app.route('/templates/import', methods=['GET'])
def import_templates():
    try:
        templates = import_message_templates_from_gsheet(
            sheet_id=DEFAULT_SHEET_ID,
            gcp_creds_file_path=GCP_CREDS_FILE_PATH
        )
        templates_path = BASE_DIR / 'message_templates.json'
        with open(templates_path, 'w', encoding='utf-8') as f:
            json.dump(templates, f, ensure_ascii=False, indent=4)
        flash(f'Đã import thành công {len(templates)} mẫu tin nhắn từ Google Sheets.', 'success')
        return redirect(url_for('get_templates_page'))
    except Exception as e:
        flash(f'Lỗi khi import: {str(e)}', 'danger')
        return redirect(url_for('get_templates_page'))

@app.route('/templates/export')
def export_templates_route():
    try:
        templates_path = BASE_DIR / 'message_templates.json'
        try:
            with open(templates_path, 'r', encoding='utf-8') as f:
                templates = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            templates = []
        if not templates:
            flash('Không có mẫu tin nhắn để export.', 'warning')
            return redirect(url_for('get_templates_page'))
        export_message_templates_to_gsheet(templates, DEFAULT_SHEET_ID, GCP_CREDS_FILE_PATH)
        flash('Đã export thành công tất cả các mẫu tin nhắn!', 'success')
    except Exception as e:
        flash(f'Lỗi khi export: {e}', 'danger')
    return redirect(url_for('get_templates_page'))

if __name__ == '__main__':
    # Sử dụng biến DEV_MODE để kiểm soát chế độ debug khi chạy trực tiếp
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5001)), debug=DEV_MODE)
