from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import sys
import os
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime

# Exe için klasör yolu ayarla - Standart yaklaşım
if getattr(sys, 'frozen', False):
    # Exe durumunda - exe'nin yanındaki klasör
    app_dir = os.path.dirname(sys.executable)
    DATABASE = os.path.join(app_dir, "database.db")
    UPLOAD_FOLDER = os.path.join(app_dir, 'static', 'uploads')
    static_folder = os.path.join(app_dir, 'static')
    print(f"🔧 Running as EXE - Upload folder: {UPLOAD_FOLDER}")
else:
    # Normal Python durumunda
    DATABASE = "database.db"
    UPLOAD_FOLDER = 'static/uploads'
    static_folder = 'static'
    print(f"🔧 Running as Script - Upload folder: {UPLOAD_FOLDER}")

app = Flask(__name__, static_folder=static_folder)
CORS(app)  # CORS'u açarak Android uygulamasının bağlanmasını sağlıyoruz
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# Check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    conn = get_db_connection()

    # Check if inventory table exists
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='inventory'")
    table_exists = cursor.fetchone() is not None

    if not table_exists:
        # Create the inventory table if it doesn't exist
        conn.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY,
                item_number TEXT NOT NULL,
                title TEXT NOT NULL,
                variation_details TEXT,
                available_quantity INTEGER NOT NULL CHECK(available_quantity >= 0),
                currency TEXT NOT NULL,
                start_price REAL NOT NULL CHECK(start_price >= 0),
                depot_info TEXT,
                image_path TEXT,
                updated_at TEXT
            )
        ''')
    else:
        # Check if image_path and updated_at columns exist
        cursor.execute("PRAGMA table_info(inventory)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]

        # Add image_path column if it doesn't exist
        if 'image_path' not in column_names:
            try:
                conn.execute("ALTER TABLE inventory ADD COLUMN image_path TEXT")
                print("Added image_path column to inventory table")
            except sqlite3.OperationalError:
                pass
        # Add updated_at column if it doesn't exist
        if 'updated_at' not in column_names:
            try:
                conn.execute("ALTER TABLE inventory ADD COLUMN updated_at TEXT")
                print("Added updated_at column to inventory table")
            except sqlite3.OperationalError:
                pass

    conn.commit()
    conn.close()


# Initialize database at startup
initialize_database()


# 📌 Sunucunun çalışıp çalışmadığını test etmek için
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Flask server is running!"})


# 📌 Envanteri alma (GET)
@app.route("/inventory", methods=["GET"])
def get_inventory():
    conn = get_db_connection()
    items = conn.execute("SELECT * FROM inventory ORDER BY COALESCE(updated_at, '') DESC, id DESC").fetchall()
    conn.close()
    return jsonify([dict(item) for item in items])


# 📌 Yeni ürün ekleme (POST)
@app.route("/add-item", methods=["POST"])
def add_item():
    data = request.get_json()
    conn = get_db_connection()
    now = datetime.utcnow().isoformat()

    # Telefondan gelen ID'yi kullan (eğer varsa)
    client_id = data.get("id", None)

    if client_id and client_id > 0:
        # Telefon tarafından gönderilen ID'yi kullan
        try:
            cursor = conn.execute(
                "INSERT INTO inventory (id, item_number, title, variation_details, available_quantity, currency, start_price, depot_info, image_path, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    client_id,
                    data["item_number"],
                    data["title"],
                    data.get("variation_details", ""),
                    data["available_quantity"],
                    data["currency"],
                    data["start_price"],
                    data.get("depot_info", ""),
                    data.get("image_url", None),
                    now
                )
            )
            item_id = client_id
        except sqlite3.IntegrityError:
            # ID çakışması durumunda rastgele bir ID oluştur
            cursor = conn.execute(
                "INSERT INTO inventory (item_number, title, variation_details, available_quantity, currency, start_price, depot_info, image_path, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    data["item_number"],
                    data["title"],
                    data.get("variation_details", ""),
                    data["available_quantity"],
                    data["currency"],
                    data["start_price"],
                    data.get("depot_info", ""),
                    data.get("image_url", None),
                    now
                )
            )
            item_id = cursor.lastrowid
    else:
        # ID gönderilmemişse veya geçersizse, otomatik olarak atanacak
        cursor = conn.execute(
            "INSERT INTO inventory (item_number, title, variation_details, available_quantity, currency, start_price, depot_info, image_path, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                data["item_number"],
                data["title"],
                data.get("variation_details", ""),
                data["available_quantity"],
                data["currency"],
                data["start_price"],
                data.get("depot_info", ""),
                data.get("image_url", None),
                now
            )
        )
        item_id = cursor.lastrowid

    conn.commit()

    # Eklenen ürünü veritabanından çek
    item = conn.execute("SELECT * FROM inventory WHERE id = ?", (item_id,)).fetchone()
    conn.close()

    # Sözlüğe dönüştür
    result = dict(item)

    # ID'yi doğru formatta döndür
    return jsonify(result), 201


# 📌 Ürün güncelleme (PUT)
@app.route("/edit-item/<int:id>", methods=["PUT"])
def edit_item(id):
    data = request.get_json()
    conn = get_db_connection()
    now = datetime.utcnow().isoformat()
    conn.execute(
        "UPDATE inventory SET item_number = ?, title = ?, variation_details = ?, available_quantity = ?, currency = ?, start_price = ?, depot_info = ?, updated_at = ? WHERE id = ?",
        (data["item_number"], data["title"], data.get("variation_details", ""), data["available_quantity"],
         data["currency"], data["start_price"], data.get("depot_info", ""), now, id)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Item updated successfully"})


# 📌 Ürün silme (DELETE)
@app.route("/delete-item/<int:id>", methods=["DELETE"])
def delete_item(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM inventory WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Item deleted successfully"})


# 📌 Resim yükleme (POST)
@app.route("/upload_image/<int:id>", methods=["POST"])
def upload_image(id):
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file and allowed_file(file.filename):
        # ID kontrolü
        try:
            id = int(id)  # ID'nin integer olduğundan emin ol
            if id <= 0:
                return jsonify({"error": "Invalid item ID"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid item ID format"}), 400

        # Ürün var mı kontrol et
        conn = get_db_connection()
        item = conn.execute("SELECT item_number FROM inventory WHERE id = ?", (id,)).fetchone()

        if not item:
            # Bu ID'ye sahip ürün yoksa, oluştur
            try:
                item_number = f"AUTO{id}"  # Otomatik ürün numarası
                cursor = conn.execute(
                    "INSERT INTO inventory (id, item_number, title, variation_details, available_quantity, currency, start_price, depot_info) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (id, item_number, f"Product {id}", "", 0, "$", 0.00, "")
                )
                conn.commit()

                # Tekrar kontrol et
                item = conn.execute("SELECT item_number FROM inventory WHERE id = ?", (id,)).fetchone()
                if not item:
                    conn.close()
                    return jsonify({"error": f"Failed to create item with ID: {id}"}), 500
            except sqlite3.IntegrityError as e:
                conn.close()
                return jsonify({"error": f"Database error: {str(e)}"}), 500

        # Dosya adı oluştur - Standart format
        item_number = item['item_number']
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        timestamp = str(int(datetime.now().timestamp()))
        new_filename = f"product_{item_number}_{id}_{timestamp}.{file_extension}"

        # Dosyayı kaydet
        file_path = os.path.join(UPLOAD_FOLDER, new_filename)
        file.save(file_path)

        # WEB ARAYÜZÜ İLE UYUMLU FORMATTA YOLU SAKLA
        # Web arayüzü tam dosya yolunu bekliyor
        full_file_path = os.path.join(UPLOAD_FOLDER, new_filename)

        # Veritabanını güncelle - web arayüzü ile aynı format (tam yol)
        conn.execute("UPDATE inventory SET image_path = ? WHERE id = ?", (full_file_path, id))
        conn.commit()
        conn.close()

        # Başarı yanıtı - Android için göreceli yol döndür
        return jsonify({
            "success": True,
            "message": "Image uploaded successfully",
            "image_url": f"static/uploads/{new_filename}",
            "item_id": id
        })

    return jsonify({"error": "File type not allowed"}), 400


# 📌 Resim URL'si alma (GET)
@app.route("/image/<int:id>", methods=["GET"])
def get_image_url(id):
    conn = get_db_connection()
    result = conn.execute("SELECT image_path FROM inventory WHERE id = ?", (id,)).fetchone()
    conn.close()

    if result and result['image_path']:
        image_path = result['image_path']

        # Dosya mevcut mu kontrol et
        if os.path.exists(image_path):
            # Dosya adını al ve Android için göreceli yol döndür
            filename = os.path.basename(image_path)
            android_path = f"static/uploads/{filename}"

            return jsonify({
                "success": True,
                "image_url": android_path,
                "item_id": id
            })
        else:
            # Dosya mevcut değilse, eski format kontrol et
            filename = os.path.basename(image_path)
            potential_path = os.path.join(UPLOAD_FOLDER, filename)

            if os.path.exists(potential_path):
                return jsonify({
                    "success": True,
                    "image_url": f"static/uploads/{filename}",
                    "item_id": id
                })

    # Resim yok
    return jsonify({
        "success": False,
        "error": "No image found for this item",
        "item_id": id
    }), 404


# 📌 Resim dosyasını gönderme
@app.route("/static/uploads/<path:filename>")
def serve_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# 📌 Tüm resimleri listele
@app.route("/images", methods=["GET"])
def get_all_images():
    conn = get_db_connection()
    results = conn.execute("SELECT id, item_number, image_path FROM inventory WHERE image_path IS NOT NULL").fetchall()
    conn.close()

    images = []
    for result in results:
        if result['image_path']:
            image_path = result['image_path']

            # Dosya mevcut mu kontrol et
            if os.path.exists(image_path):
                filename = os.path.basename(image_path)
                android_path = f"static/uploads/{filename}"

                images.append({
                    "id": result['id'],
                    "product_id": result['id'],
                    "image_url": android_path,
                    "timestamp": "N/A"
                })
            else:
                # Eski format kontrol et
                filename = os.path.basename(image_path)
                potential_path = os.path.join(UPLOAD_FOLDER, filename)

                if os.path.exists(potential_path):
                    images.append({
                        "id": result['id'],
                        "product_id": result['id'],
                        "image_url": f"static/uploads/{filename}",
                        "timestamp": "N/A"
                    })

    return jsonify(images)


# 📌 IP Address Update Endpoint for Dynamic IP Monitoring
@app.route("/api/ip-update", methods=["POST"])
def ip_update():
    """Receive IP address change notifications from IP monitor service"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        new_ip = data.get('new_ip')
        old_ip = data.get('old_ip')
        timestamp = data.get('timestamp')
        
        if not new_ip:
            return jsonify({"error": "No new IP address provided"}), 400
        
        # Log the IP change
        print(f"🌐 IP Address Updated: {old_ip} -> {new_ip} at {timestamp}")
        
        # Save to IP history database if exists
        try:
            if os.path.exists('ip_history.db'):
                conn = sqlite3.connect('ip_history.db')
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ip_history (ip_address, timestamp, location, isp, change_reason)
                    VALUES (?, ?, ?, ?, ?)
                """, (new_ip, timestamp, 'Auto-detected', 'Unknown', f'API notification from {old_ip}'))
                conn.commit()
                conn.close()
        except Exception as db_error:
            print(f"⚠️ Database logging failed: {db_error}")
        
        # Update current IP file
        try:
            with open('current_ip.txt', 'w') as f:
                f.write(f"{new_ip}\n{timestamp}")
        except Exception as file_error:
            print(f"⚠️ File update failed: {file_error}")
        
        # Notify connected clients (if any WebSocket connections exist)
        # This can be extended for real-time notifications
        
        return jsonify({
            "success": True,
            "message": "IP address updated successfully",
            "new_ip": new_ip,
            "old_ip": old_ip,
            "timestamp": timestamp
        })
        
    except Exception as e:
        print(f"❌ IP update error: {e}")
        return jsonify({"error": str(e)}), 500


# 📌 Get Current IP Status
@app.route("/api/ip-status", methods=["GET"])
def get_ip_status():
    """Get current IP address and status information"""
    try:
        current_ip = None
        last_update = None
        
        # Read current IP from file
        if os.path.exists('current_ip.txt'):
            try:
                with open('current_ip.txt', 'r') as f:
                    lines = f.read().strip().split('\n')
                    if len(lines) >= 1:
                        current_ip = lines[0]
                    if len(lines) >= 2:
                        last_update = lines[1]
            except Exception as e:
                print(f"⚠️ Failed to read IP file: {e}")
        
        # Get IP history if database exists
        history = []
        if os.path.exists('ip_history.db'):
            try:
                conn = sqlite3.connect('ip_history.db')
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT ip_address, timestamp, location, isp 
                    FROM ip_history 
                    ORDER BY timestamp DESC 
                    LIMIT 5
                """)
                results = cursor.fetchall()
                history = [
                    {
                        'ip': row[0],
                        'timestamp': row[1],
                        'location': row[2],
                        'isp': row[3]
                    }
                    for row in results
                ]
                conn.close()
            except Exception as e:
                print(f"⚠️ Failed to read IP history: {e}")
        
        return jsonify({
            "success": True,
            "current_ip": current_ip,
            "last_update": last_update,
            "history": history,
            "monitor_running": os.path.exists('ip_monitor.log')
        })
        
    except Exception as e:
        print(f"❌ IP status error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("🚀 Flask API Server starting...")
    print("📡 Server running on: http://localhost:5001")
    print("🌐 API endpoints available at: http://0.0.0.0:5001")
    print("💡 IP Monitor endpoints:")
    print("   POST /api/ip-update - Receive IP change notifications")
    print("   GET  /api/ip-status - Get current IP status")
    print("⚡ Press Ctrl+C to stop the server")
    print("-" * 50)
    try:
        app.run(host="0.0.0.0", port=5001, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        input("Press Enter to exit...")
    finally:
        print("👋 Server shutdown complete")
