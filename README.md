# 🏨 Hotel Booking Management System

Flask web application để quản lý đặt phòng khách sạn với tích hợp Google Sheets và AI.

## ✨ Tính năng

- 📊 Dashboard với thống kê doanh thu
- 📅 Lịch quản lý đặt phòng 
- 🤖 AI trích xuất thông tin từ ảnh
- 📈 Biểu đồ và báo cáo
- 📱 Responsive design
- ☁️ Tích hợp Google Sheets

## 🚀 Deploy lên Koyeb (Miễn phí, Always-on)

### 1. Chuẩn bị Repository

```bash
git clone <your-repo>
cd hotel_flask_app
```

### 2. Environment Variables cần thiết

Trong Koyeb Dashboard, thêm các biến môi trường:

```
FLASK_SECRET_KEY = your_secret_key_here
DEFAULT_SHEET_ID = your_google_sheet_id
WORKSHEET_NAME = BookingManager
MESSAGE_TEMPLATE_WORKSHEET = MessageTemplate
GOOGLE_API_KEY = your_google_ai_api_key
PORT = 8080
FLASK_ENV = production
```

**Quan trọng nhất - GCP_CREDENTIALS_JSON:**
```json
{"type":"service_account","project_id":"...","private_key":"...","client_email":"..."}
```

### 3. Deploy

1. Kết nối GitHub repo với Koyeb
2. Koyeb tự detect Dockerfile
3. Thêm environment variables
4. Click Deploy

### 4. Kiểm tra

- App sẽ chạy tại: `https://your-app-name.koyeb.app`
- Không bao giờ ngủ (Always-on)
- SSL tự động

## 🔧 Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env với thông tin thực

# Run locally
python app.py
```

## 📁 Cấu trúc Project

```
hotel_flask_app/
├── app.py              # Main Flask application
├── logic.py            # Business logic
├── gcp_helper.py       # Google Cloud helper
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container config
├── start.sh           # Startup script
├── koyeb.toml         # Koyeb configuration
├── templates/         # HTML templates
├── static/           # CSS, JS, images
└── .env.example      # Environment template
```

## 🛠️ Troubleshooting

**Build failed với pandas:**
- Đã fix với pandas 2.2.0 + Python 3.11

**Google Sheets connection:**
- Kiểm tra `GCP_CREDENTIALS_JSON` format
- Đảm bảo service account có quyền access

**App not loading:**
- Check logs trong Koyeb Dashboard
- Verify environment variables

## 📞 Support

Nếu gặp vấn đề, check:
1. Koyeb Dashboard → App → Logs
2. Environment variables
3. Google credentials format
