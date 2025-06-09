#!/usr/bin/env python3
"""
Script để kiểm tra và debug biểu đồ dashboard
"""

import sys
import os
from pathlib import Path

# Thêm thư mục project vào Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from app import app, load_data, prepare_dashboard_data
from datetime import datetime, timedelta
import calendar
import pandas as pd
import plotly.express as px
import json

def debug_chart_data():
    """Debug dữ liệu biểu đồ"""
    print("=== KIỂM TRA DỮ LIỆU BIỂU ĐỒ ===")
    
    # 1. Kiểm tra tải dữ liệu
    try:
        df, _ = load_data()
        print(f"✅ Tải dữ liệu thành công: {len(df)} dòng")
        print(f"Các cột: {list(df.columns)}")
    except Exception as e:
        print(f"❌ Lỗi tải dữ liệu: {e}")
        return
    
    # 2. Thiết lập thời gian mặc định
    today = datetime.today()
    start_date = today.replace(day=1)
    _, last_day = calendar.monthrange(today.year, today.month)
    end_date = today.replace(day=last_day)
    
    print(f"Thời gian: {start_date.strftime('%Y-%m-%d')} đến {end_date.strftime('%Y-%m-%d')}")
    
    # 3. Kiểm tra prepare_dashboard_data
    try:
        dashboard_data = prepare_dashboard_data(df, start_date, end_date, 'Tháng', 'desc')
        print(f"✅ Dashboard data keys: {list(dashboard_data.keys())}")
        
        # Kiểm tra monthly_revenue_all_time
        monthly_revenue = dashboard_data.get('monthly_revenue_all_time', pd.DataFrame())
        print(f"Monthly revenue data: {len(monthly_revenue)} rows")
        if not monthly_revenue.empty:
            print(monthly_revenue.head())
        
        # Kiểm tra collector_revenue_selected
        collector_revenue = dashboard_data.get('collector_revenue_selected', pd.DataFrame())
        print(f"Collector revenue data: {len(collector_revenue)} rows")
        if not collector_revenue.empty:
            print(collector_revenue.head())
            
    except Exception as e:
        print(f"❌ Lỗi prepare_dashboard_data: {e}")
        return
    
    # 4. Test tạo biểu đồ
    try:
        monthly_revenue_list = monthly_revenue.to_dict('records')
        monthly_revenue_df = pd.DataFrame(monthly_revenue_list)
        
        if not monthly_revenue_df.empty:
            print("✅ Tạo biểu đồ doanh thu...")
            monthly_revenue_df_sorted = monthly_revenue_df.sort_values('Tháng')
            
            fig = px.line(monthly_revenue_df_sorted, x='Tháng', y='Doanh thu', 
                         title='📊 Doanh thu Hàng tháng', markers=True)
            
            monthly_revenue_chart_json = json.loads(fig.to_json())
            print(f"✅ Biểu đồ JSON có {len(monthly_revenue_chart_json)} keys")
        else:
            print("⚠️ Không có dữ liệu cho biểu đồ")
            
    except Exception as e:
        print(f"❌ Lỗi tạo biểu đồ: {e}")
    
    # 5. Test pie chart
    try:
        collector_revenue_data = collector_revenue.to_dict('records')
        if collector_revenue_data:
            print("✅ Tạo pie chart...")
            collector_chart_data = {
                'data': [{
                    'type': 'pie',
                    'labels': [row['Người thu tiền'] for row in collector_revenue_data],
                    'values': [row['Tổng thanh toán'] for row in collector_revenue_data],
                }],
                'layout': {
                    'title': '💰 Doanh thu theo Người thu tiền'
                }
            }
            print(f"✅ Pie chart có {len(collector_chart_data['data'][0]['labels'])} labels")
        else:
            print("⚠️ Không có dữ liệu collector")
            
    except Exception as e:
        print(f"❌ Lỗi tạo pie chart: {e}")

def test_app_routes():
    """Test app routes"""
    print("\n=== KIỂM TRA APP ROUTES ===")
    
    with app.test_client() as client:
        # Test dashboard route
        try:
            response = client.get('/')
            print(f"✅ Dashboard route: {response.status_code}")
            if response.status_code != 200:
                print(f"Response data: {response.data[:500]}")
        except Exception as e:
            print(f"❌ Lỗi dashboard route: {e}")

if __name__ == "__main__":
    debug_chart_data()
    test_app_routes()
    print("\n=== HOÀN THÀNH DEBUG ===")
