"""
Simple test để kiểm tra biểu đồ có hoạt động không
"""

import pandas as pd
import plotly.express as px
import json

def test_chart_creation():
    print("=== TEST TẠO BIỂU ĐỒ ===")
    
    # Tạo dữ liệu demo
    data = {
        'Tháng': ['2024-01', '2024-02', '2024-03', '2024-04'],
        'Doanh thu': [1000000, 1500000, 1200000, 1800000]
    }
    
    df = pd.DataFrame(data)
    print("✅ Tạo DataFrame demo thành công")
    print(df)
    
    # Tạo biểu đồ
    try:
        fig = px.line(df, x='Tháng', y='Doanh thu', 
                     title='📊 Doanh thu Hàng tháng', markers=True)
        
        chart_json = json.loads(fig.to_json())
        print("✅ Tạo biểu đồ JSON thành công")
        print(f"Chart có {len(chart_json)} keys: {list(chart_json.keys())}")
        
        # Kiểm tra cấu trúc
        if 'data' in chart_json and 'layout' in chart_json:
            print("✅ Cấu trúc JSON hợp lệ")
            print(f"Data traces: {len(chart_json['data'])}")
            print(f"Layout title: {chart_json['layout'].get('title', {}).get('text', 'No title')}")
        else:
            print("❌ Cấu trúc JSON không hợp lệ")
            
    except Exception as e:
        print(f"❌ Lỗi tạo biểu đồ: {e}")
    
    # Test pie chart
    try:
        collector_data = [
            {'Người thu tiền': 'LOC LE', 'Tổng thanh toán': 2000000},
            {'Người thu tiền': 'THAO LE', 'Tổng thanh toán': 1500000}
        ]
        
        collector_chart = {
            'data': [{
                'type': 'pie',
                'labels': [row['Người thu tiền'] for row in collector_data],
                'values': [row['Tổng thanh toán'] for row in collector_data],
            }],
            'layout': {
                'title': '💰 Doanh thu theo Người thu tiền'
            }
        }
        
        print("✅ Tạo pie chart thành công")
        print(f"Labels: {collector_chart['data'][0]['labels']}")
        print(f"Values: {collector_chart['data'][0]['values']}")
        
    except Exception as e:
        print(f"❌ Lỗi tạo pie chart: {e}")

if __name__ == "__main__":
    test_chart_creation()
