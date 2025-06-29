# Örnek Yapılandırma Dosyası
# Bu dosyayı config.py olarak kopyalayın ve kendi ayarlarınızı girin

# Flask Ayarları
SECRET_KEY = 'your-secret-key-here'  # Güvenlik için rastgele bir anahtar
DEBUG = False  # Production'da False olmalı
HOST = '0.0.0.0'
PORT = 5003

# Veritabanı Ayarları (SQLite varsayılan)
DATABASE_TYPE = 'sqlite'  # 'sqlite' veya 'mysql'
SQLITE_DB_PATH = 'database.db'

# MySQL Ayarları (isteğe bağlı)
MYSQL_HOST = 'localhost'
MYSQL_USER = 'envanter_user'
MYSQL_PASSWORD = 'your_password'
MYSQL_DB = 'envanter_db'
MYSQL_PORT = 3306

# Dosya Yükleme Ayarları
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max dosya boyutu
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Upload Klasörleri
UPLOAD_FOLDER = 'static/uploads'
THUMBNAIL_FOLDER = 'static/thumbnails'

# QR Kod Ayarları
QR_CODE_SIZE = 10
QR_CODE_BORDER = 4

# Para Birimi Ayarları
DEFAULT_CURRENCY = 'TL'
SUPPORTED_CURRENCIES = ['TL', 'USD', 'EUR', 'GBP']

# Sayfalama Ayarları
ITEMS_PER_PAGE = 20

# Güvenlik Ayarları
CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000'] 