# EbayStock - Inventory Management System

A comprehensive inventory management system with both web and desktop interfaces, designed for efficient stock tracking, QR code generation, and multi-format export capabilities.

## 🚀 Features

### Core Functionality
- **Inventory Management**: Add, edit, delete, and track inventory items
- **QR Code Generation**: Automatic QR code creation for each item
- **Image Upload**: Support for product images with thumbnail generation
- **Label Printing**: Generate printable labels for inventory items
- **Multi-format Export**: Export data to Excel and CSV formats
- **Search & Filter**: Advanced search and filtering capabilities
- **Dynamic IP Monitoring**: Automatic IP address change detection and notification system

### Technical Features
- **Web Interface**: Modern, responsive Flask-based web application
- **Desktop Application**: Standalone desktop version with GUI
- **Database Support**: SQLite and MySQL database integration
- **REST API**: RESTful API endpoints for integration
- **Image Processing**: Automatic image optimization and thumbnail generation
- **IP Monitoring Service**: Background service for automatic IP change detection
- **Real-time Notifications**: Webhook and file-based notification system

## 🛠️ Technology Stack

- **Backend**: Python 3.x, Flask
- **Database**: SQLite (default), MySQL (optional)
- **Frontend**: HTML5, CSS3, JavaScript
- **Image Processing**: Pillow (PIL)
- **QR Codes**: qrcode library
- **Excel Export**: pandas, openpyxl
- **Desktop GUI**: tkinter

## 📋 Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/anatolianstar/ebaystock.git
   cd ebaystock
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configuration**
   ```bash
   cp config.example.py config.py
   # Edit config.py with your database settings
   ```

## 🚀 Usage

### Web Application
```bash
python flaskapi.py
```
Access the web interface at `http://localhost:5000`

### Desktop Application
```bash
python envanterdesktop.py
```

### Main Application
```bash
python app.py
```

### CSV to Excel Converter
```bash
python CSVtoEXCEL.py
```

### IP Monitoring Service
```bash
python ip_monitor_service.py
```
Access the IP Monitor Dashboard at `http://localhost:5000/ip-monitor`

## 📁 Project Structure

```
ebaystock/
├── app.py                  # Main application entry point
├── flaskapi.py            # Flask web API
├── envanterdesktop.py     # Desktop GUI application
├── CSVtoEXCEL.py         # CSV to Excel converter
├── ip_monitor_service.py  # IP monitoring service
├── config.example.py      # Configuration template
├── database.db           # SQLite database
├── ip_history.db          # IP monitoring history
├── requirements.txt       # Python dependencies
├── templates/            # HTML templates
│   ├── index.html        # Main inventory page
│   ├── add_item.html     # Add new item form
│   ├── edit_item.html    # Edit item form
│   ├── upload_image.html # Image upload interface
│   ├── print_label.html  # Label printing page
│   ├── ip_dashboard.html # IP monitoring dashboard
│   └── upload.html       # File upload interface
├── static/              # Static assets
│   ├── icons/           # Application icons
│   ├── thumbnails/      # Generated thumbnails
│   └── uploads/         # Uploaded files
└── fonts/               # Custom fonts for labels
```

## 🔌 API Endpoints

### Items Management
- `GET /api/items` - Get all items
- `POST /api/items` - Create new item
- `PUT /api/items/<id>` - Update item
- `DELETE /api/items/<id>` - Delete item

### Image Management
- `POST /api/upload-image` - Upload product image
- `GET /api/thumbnails/<filename>` - Get thumbnail

### Export Functions
- `GET /api/export/excel` - Export to Excel
- `GET /api/export/csv` - Export to CSV

### IP Monitoring
- `POST /api/ip-update` - Receive IP change notifications
- `GET /api/ip-status` - Get current IP status and history

## 🎨 Features Overview

### Inventory Management
- Add new products with detailed information
- Edit existing inventory items
- Delete items with confirmation
- Bulk operations support

### Image Processing
- Upload product images
- Automatic thumbnail generation
- Image optimization for web display
- Support for multiple image formats

### QR Code Generation
- Automatic QR code creation for each item
- Customizable QR code properties
- Print-ready QR codes for labels

### Label Printing
- Professional label templates
- Custom font support
- Batch printing capabilities
- Multiple label sizes

### Data Export
- Excel export with formatting
- CSV export for data portability
- Custom export templates
- Scheduled exports

### IP Monitoring
- Automatic IP address change detection
- Real-time notifications via webhooks
- IP history tracking and logging
- Dashboard for monitoring status
- Configurable check intervals
- Multiple IP detection services

## 🔧 Configuration

Edit `config.py` to customize:

```python
# Database settings
DATABASE_URL = 'sqlite:///database.db'
# or for MySQL:
# DATABASE_URL = 'mysql://user:password@localhost/dbname'

# Upload settings
UPLOAD_FOLDER = 'static/uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# Image settings
THUMBNAIL_SIZE = (150, 150)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# IP Monitoring settings
IP_CHECK_INTERVAL = 300  # 5 minutes
IP_SERVICES = [
    'https://api.ipify.org?format=json',
    'https://httpbin.org/ip'
]
WEBHOOK_URL = 'http://localhost:5001/api/ip-update'
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/anatolianstar/ebaystock/issues) page
2. Create a new issue with detailed description
3. Include error messages and system information

## 🙏 Acknowledgments

- Flask community for the excellent web framework
- Python libraries contributors
- Open source community for inspiration and tools

---

**Made with ❤️ for efficient inventory management**
