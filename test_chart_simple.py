"""
Simple test to check if chart creation works
"""

import pandas as pd
import plotly.express as px
import json

def test_chart_creation():
    print("=== TEST CREATE CHART ===")
    
    # Create demo data
    data = {
        'Thang': ['2024-01', '2024-02', '2024-03', '2024-04'],
        'Doanh_thu': [1000000, 1500000, 1200000, 1800000]
    }
    
    df = pd.DataFrame(data)
    print("✓ Created demo DataFrame successfully")
    print(df)
    
    # Create chart
    try:
        fig = px.line(df, x='Thang', y='Doanh_thu', 
                     title='Monthly Revenue Chart', markers=True)
        
        chart_json = json.loads(fig.to_json())
        print("✓ Created chart JSON successfully")
        print(f"Chart has {len(chart_json)} keys: {list(chart_json.keys())}")
        
        # Check structure
        if 'data' in chart_json and 'layout' in chart_json:
            print("✓ JSON structure is valid")
            print(f"Data traces: {len(chart_json['data'])}")
            print(f"Layout title: {chart_json['layout'].get('title', {}).get('text', 'No title')}")
        else:
            print("✗ Invalid JSON structure")
            
    except Exception as e:
        print(f"✗ Error creating chart: {e}")
    
    # Test pie chart
    try:
        collector_data = [
            {'Nguoi_thu': 'LOC LE', 'Tong_thanh_toan': 2000000},
            {'Nguoi_thu': 'THAO LE', 'Tong_thanh_toan': 1500000}
        ]
        
        collector_chart = {
            'data': [{
                'type': 'pie',
                'labels': [row['Nguoi_thu'] for row in collector_data],
                'values': [row['Tong_thanh_toan'] for row in collector_data],
            }],
            'layout': {
                'title': 'Revenue by Collector'
            }
        }
        
        print("✓ Created pie chart successfully")
        print(f"Labels: {collector_chart['data'][0]['labels']}")
        print(f"Values: {collector_chart['data'][0]['values']}")
        
    except Exception as e:
        print(f"✗ Error creating pie chart: {e}")

if __name__ == "__main__":
    test_chart_creation()
