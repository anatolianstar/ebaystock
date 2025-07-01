import os
import sys
import tempfile
import sqlite3
from textwrap import wrap  # Metni belirli karakter sınırına göre sarmak için
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest
from datetime import datetime

# Flask imports
from flask import Flask, render_template, request, send_file, send_from_directory, redirect, url_for, flash

# PyInstaller için reportlab import'larını try-except ile sarmalayalım
try:
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase import pdfmetrics
    # Barcode import'unu ayrı try-catch ile yapalım
    try:
        from reportlab.graphics.barcode import code128
        BARCODE_AVAILABLE = True
    except Exception as barcode_error:
        print(f"Barcode modülü yüklenemedi: {barcode_error}")
        BARCODE_AVAILABLE = False
        code128 = None
    REPORTLAB_AVAILABLE = True
except Exception as reportlab_error:
    print(f"ReportLab yüklenemedi: {reportlab_error}")
    REPORTLAB_AVAILABLE = False
    BARCODE_AVAILABLE = False
    canvas = None
    TTFont = None
    pdfmetrics = None
    code128 = None

# QR Code import
try:
    import qrcode
    QR_AVAILABLE = True
except Exception as qr_error:
    print(f"QRCode modülü yüklenemedi: {qr_error}")
    QR_AVAILABLE = False
    qrcode = None

# Pandas import (Excel için)
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except Exception as pandas_error:
    print(f"Pandas yüklenemedi: {pandas_error}")
    PANDAS_AVAILABLE = False
    pd = None

# MySQL import (opsiyonel)
try:
    import pymysql
    MYSQL_AVAILABLE = True
except Exception as mysql_error:
    print(f"PyMySQL yüklenemedi: {mysql_error}")
    MYSQL_AVAILABLE = False
    pymysql = None

# PyInstaller için resource path ayarı
def resource_path(relative_path):
    """ PyInstaller ile paketlenmiş uygulamalar için doğru path'i döndür """
    try:
        # PyInstaller ile çalışıyorsa _MEIPASS kullan
        base_path = sys._MEIPASS
    except Exception:
        # Normal Python çalışıyorsa mevcut dizini kullan
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Flask uygulaması - PyInstaller için template ve static path düzeltmesi
if getattr(sys, 'frozen', False):
    # PyInstaller ile çalışırken
    template_dir = os.path.join(sys._MEIPASS, 'templates')
    static_dir = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
else:
    # Normal Python ile çalışırken
    app = Flask(__name__)

app.secret_key = "your_secret_key"

# Database.db dosyası exe ile aynı klasörde olacak
DATABASE_NAME = "database.db"

# PyInstaller ile exe yapıldığında database ve upload folder exe'nin yanında olsun
if getattr(sys, 'frozen', False):
    # PyInstaller ile çalışırken - exe'nin bulunduğu dizin
    app_dir = os.path.dirname(sys.executable)
    DATABASE = os.path.join(app_dir, DATABASE_NAME)
    UPLOAD_FOLDER = os.path.join(app_dir, 'static', 'uploads')
else:
    # Normal Python ile çalışırken - mevcut dizin
    DATABASE = DATABASE_NAME
    UPLOAD_FOLDER = 'static/uploads'

# Database yoksa boş bir tane oluştur
if not os.path.exists(DATABASE):
    try:
        conn = sqlite3.connect(DATABASE)
        conn.close()
        print(f"Database oluşturuldu: {DATABASE}")
    except Exception as e:
        print(f"Database oluşturma hatası: {e}")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Klasörü oluştur (eğer yoksa)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# İzin verilen uzantıları kontrol et
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Veritabanı bağlantısı
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Dict-like erişim sağlar
    return conn

# Veritabanını başlatma
def initialize_database():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY,
            item_number TEXT NOT NULL,
            title TEXT NOT NULL,
            variation_details TEXT,
            available_quantity INTEGER NOT NULL CHECK(available_quantity >= 0),
            currency TEXT NOT NULL,
            start_price REAL NOT NULL CHECK(start_price >= 0),
            depot_info TEXT,
            image_path TEXT
        )
    """)

    # Eğer image_path sütunu yoksa onu ekle
    try:
        conn.execute("ALTER TABLE inventory ADD COLUMN image_path TEXT")
    except sqlite3.OperationalError:
        # Sütun zaten varsa hata vermez
        pass

    conn.commit()
    conn.close()


@app.route("/print-label/<int:id>")
def print_label(id):
    try:
        # ReportLab ve Barcode modüllerinin varlığını kontrol et
        if not REPORTLAB_AVAILABLE:
            return "PDF oluşturucu (ReportLab) yüklü değil!", 500
        
        if not BARCODE_AVAILABLE:
            return "Barkod oluşturucu yüklü değil!", 500
            
        id = int(id)  # ID'yi int'e çevir
        size = request.args.get("size", "40x15")

        # 80 DPI için doğru ölçüler (piksel cinsinden)
        valid_sizes = {"40x15": (126, 44), "40x20": (126, 60), "40x30": (126, 90)}

        if size not in valid_sizes:
            size = "40x15"
        
        # Font dosyalarını güvenli şekilde yükle
        try:
            if pdfmetrics and TTFont:
                pdfmetrics.registerFont(TTFont("Roboto", resource_path("fonts/Roboto-Regular.ttf")))
                pdfmetrics.registerFont(TTFont("Robotom", resource_path("fonts/Roboto-Bold.ttf")))
                pdfmetrics.registerFont(TTFont("Oswald", resource_path("fonts/Oswald-Bold.ttf")))
                font_available = True
            else:
                font_available = False
        except Exception as font_error:
            print(f"Font yükleme hatası: {font_error}")
            font_available = False

        width, height = valid_sizes[size]

        conn = get_db_connection()
        item = conn.execute("SELECT * FROM inventory WHERE id = ?", (id,)).fetchone()
        conn.close()

        if not item:
            return "Ürün bulunamadı!", 404

        item = {key: item[key] for key in item.keys()}
        item_number = item["item_number"]
        depot_info = item["depot_info"] or ""
        title = item["title"] or ""
        variation_details = item["variation_details"] if item["variation_details"] else "N/A"

        # Ürün adını satırlara böl
        wrapped_title = wrap(title, width=24)[:2]

        # PDF oluşturma (geçici dizinde)
        pdf_path = os.path.join(tempfile.gettempdir(), f"label_{item['item_number']}.pdf")
        c = canvas.Canvas(pdf_path, pagesize=(width, height))

        # 1D Barkod
        barcode = code128.Code128(item["item_number"], barHeight=9, barWidth=0.7)
        barcode.drawOn(c, -13, height - 9)

        # Font seçimi
        font_name = "Oswald" if font_available else "Helvetica"
        
        # Barkod altı yazı
        c.setFont(font_name, 5)
        text_x_position = -24 + (barcode.width / 2) - (len(item_number) + len(depot_info))
        c.drawString(text_x_position, height - 14, f"{item_number} | {depot_info}")

        # Ürün Adı
        c.setFont(font_name, 7)
        y_position = height - 22
        for line in wrapped_title:
            c.drawString(5, y_position, line)
            y_position -= 9

        # Fiyat
        c.setFont(font_name, 10)
        c.drawString(15, y_position - 1, f"{item['start_price']} {item['currency']}")

        # QR Kodu ekle (eğer mevcut ise)
        if QR_AVAILABLE and qrcode:
            try:
                qr = qrcode.QRCode(box_size=2, border=1)
                qr.add_data(f"{item_number} | {title} | {variation_details}| {item['start_price']} {item['currency']} | {depot_info}")
                qr_img = qr.make_image(fill="black", back_color="white")
                
                # Geçici QR dosyası
                qr_path = os.path.join(tempfile.gettempdir(), f"temp_qr_{item_number}.png")
                qr_img.save(qr_path)

                c.drawImage(qr_path, width - 44, 2, width=44, height=43)
                
                # Geçici dosyayı temizle
                try:
                    os.remove(qr_path)
                except:
                    pass
            except Exception as qr_error:
                print(f"QR kod oluşturma hatası: {qr_error}")
        else:
            print("QR kod modülü mevcut değil, QR kod atlanıyor")

        c.save()

        return send_file(pdf_path, as_attachment=True)

    except Exception as e:
        print(f"PDF oluşturma hatası: {e}")
        return f"PDF oluşturulamadı: {str(e)}", 500


# Ana sayfa (Ürün listeleme)
@app.route("/", methods=["GET"])
def index():
    try:
        conn = get_db_connection()
        search_query = request.args.get("search", "").strip()  # Arama için sorgu al
        group_mode = request.args.get("group", "0") == "1"  # Gruplama modu

        page = request.args.get("page", 1, type=int)  # Sayfa numarasını al
        per_page = 50  # Her sayfada 50 ürün gösterilecek

        if group_mode:
            # Gruplamada farklı SQL sorgusu - aynı item_number'a sahip ürünleri grupla
            if search_query:
                sql_query = """
                    SELECT 
                        MIN(id) as id,
                        item_number,
                        title,
                        GROUP_CONCAT(DISTINCT variation_details) as variation_details,
                        SUM(available_quantity) as available_quantity,
                        currency,
                        AVG(start_price) as start_price,
                        depot_info,
                        (SELECT image_path FROM inventory i2 WHERE i2.item_number = inventory.item_number AND i2.image_path IS NOT NULL LIMIT 1) as image_path,
                        COUNT(*) as variant_count
                    FROM inventory
                    WHERE item_number LIKE ? OR title LIKE ? OR variation_details LIKE ?
                    GROUP BY item_number, title, currency, depot_info
                    ORDER BY MIN(id) DESC
                """
                params = (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%")
            else:
                sql_query = """
                    SELECT 
                        MIN(id) as id,
                        item_number,
                        title,
                        GROUP_CONCAT(DISTINCT variation_details) as variation_details,
                        SUM(available_quantity) as available_quantity,
                        currency,
                        AVG(start_price) as start_price,
                        depot_info,
                        (SELECT image_path FROM inventory i2 WHERE i2.item_number = inventory.item_number AND i2.image_path IS NOT NULL LIMIT 1) as image_path,
                        COUNT(*) as variant_count
                    FROM inventory
                    GROUP BY item_number, title, currency, depot_info
                    ORDER BY MIN(id) DESC
                    LIMIT ? OFFSET ?
                """
                params = (per_page, (page - 1) * per_page)
        else:
            # Normal listeleme - eski kod
            sql_query = """
                SELECT id, item_number, title, variation_details, available_quantity, 
                       currency, start_price, depot_info, image_path 
                FROM inventory
                {}
                ORDER BY id DESC
                {}
            """

            if search_query:
                # Eğer arama yapılmışsa sadece eşleşen ürünleri getir
                filter_condition = "WHERE item_number LIKE ? OR title LIKE ? OR variation_details LIKE ?"
                limit_clause = ""
                params = (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%")
            else:
                # Eğer arama yoksa, normal listele ve sayfalama uygula
                filter_condition = ""
                limit_clause = "LIMIT ? OFFSET ?"
                params = (per_page, (page - 1) * per_page)

            # SQL sorgusunu oluştur
            sql_query = sql_query.format(filter_condition, limit_clause)

        # SQL sorgusunu çalıştır
        rows = conn.execute(sql_query, params).fetchall()

        # Her ürün için düzgün bir sözlük oluştur
        inventory_list = []
        for row in rows:
            # Sütun isimlerini al - gruplama modunda variant_count da var
            if group_mode:
                columns = ['id', 'item_number', 'title', 'variation_details', 'available_quantity',
                           'currency', 'start_price', 'depot_info', 'image_path', 'variant_count']
            else:
                columns = ['id', 'item_number', 'title', 'variation_details', 'available_quantity',
                           'currency', 'start_price', 'depot_info', 'image_path']

            # Yeni bir sözlük oluştur
            item = {}
            for i, col in enumerate(columns):
                # ID değeri için özel kontrol - Her zaman tam sayı olarak işle
                if col == 'id' and i < len(row):
                    try:
                        item[col] = int(float(row[i])) if row[i] is not None else None
                    except (ValueError, TypeError):
                        # Eğer dönüştürülemeyen bir değer olursa, None ata
                        item[col] = None
                # image_path değeri
                elif col == 'image_path' and i < len(row):
                    # Resim yolu verinin kontrolü
                    if row[i] and os.path.exists(row[i]):
                        item[col] = row[i]
                    else:
                        item[col] = None
                elif i < len(row):
                    item[col] = row[i] if row[i] is not None else ""
                else:
                    # Eğer değer yoksa varsayılan değerler ata
                    if col == 'available_quantity':
                        item[col] = 0
                    elif col == 'currency':
                        item[col] = "$"
                    elif col == 'start_price':
                        item[col] = 0.0
                    elif col in ['item_number', 'title', 'variation_details', 'depot_info']:
                        item[col] = ""
                    else:
                        item[col] = None

            inventory_list.append(item)

        # İlk ürünü debug için yazdır
        if inventory_list and len(inventory_list) > 0:
            print("DEBUG: İlk ürün:", inventory_list[0])
            print("DEBUG: ID değeri:", inventory_list[0]['id'], "türü:", type(inventory_list[0]['id']))
            print("DEBUG: image_path:", inventory_list[0].get('image_path'))
            print("DEBUG: Toplam ürün sayısı:", len(inventory_list))

        # Sayfalama için toplam ürün sayısını al
        if group_mode:
            # Gruplama modunda: Benzersiz ürün numarası sayısını al
            if search_query:
                total_items = conn.execute("""
                    SELECT COUNT(DISTINCT item_number) 
                    FROM inventory 
                    WHERE item_number LIKE ? OR title LIKE ? OR variation_details LIKE ?
                """, (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%")).fetchone()[0]
            else:
                total_items = conn.execute("SELECT COUNT(DISTINCT item_number) FROM inventory").fetchone()[0]
        else:
            # Normal modda: Toplam ürün sayısını al
            if search_query:
                total_items = conn.execute("""
                    SELECT COUNT(*) 
                    FROM inventory 
                    WHERE item_number LIKE ? OR title LIKE ? OR variation_details LIKE ?
                """, (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%")).fetchone()[0]
            else:
                total_items = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        
        total_pages = (total_items + per_page - 1) // per_page  # Toplam sayfa sayısını hesapla

        conn.close()

        return render_template("index.html", inventory=inventory_list, page=page, total_pages=total_pages,
                               search_query=search_query, group_mode=group_mode)

    except Exception as e:
        print(f"Indeks rotasında hata: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Bir hata oluştu: {str(e)}", 500


# Yeni ürün ekleme
@app.route("/add-new-item", methods=["GET", "POST"])
def add_new_item():
    if request.method == "POST":
        # Eğer item_number gönderilmişse ve boş değilse kullan, aksi halde yeni oluştur
        item_number = request.form.get("item_number")
        if not item_number or item_number.strip() == "":
            # 10 haneli benzersiz bir numara oluştur
            import random
            import time
            # Zaman damgası + rastgele sayılar kullanarak benzersiz bir numara oluştur
            timestamp = int(time.time())
            random_num = random.randint(1000, 9999)
            item_number = str(timestamp)[-6:] + str(random_num)
            # 10 haneye tamamla
            while len(item_number) < 10:
                item_number = "0" + item_number
            item_number = item_number[:10]  # Sadece ilk 10 haneyi al

        title = request.form.get("title")
        variation_details = request.form.get("variation_details")
        available_quantity = int(request.form.get("available_quantity"))

        # Para birimi kontrolü - boş ise $ kullan
        currency = request.form.get("currency")
        if not currency or currency.strip() == "":
            currency = "$"

        start_price = float(request.form.get("start_price"))
        depot_info = request.form.get("depot_info")

        # Veritabanına bağlan
        conn = get_db_connection()
        cursor = conn.cursor()

        # Mevcut en yüksek ID'yi bul
        cursor.execute("SELECT MAX(id) FROM inventory")
        result = cursor.fetchone()[0]

        # Bir sonraki ID'yi belirle
        if result is not None:
            # Ondalıklı değer olabilir, temizle
            try:
                next_id = int(float(result)) + 1
            except (ValueError, TypeError):
                # Hata durumunda 1'den başla
                next_id = 1
        else:
            next_id = 1

        print(f"DEBUG: Bir sonraki ID: {next_id}")

        # Veritabanına açıkça ID belirterek ekleyelim
        cursor.execute(
            """
            INSERT INTO inventory (id, item_number, title, variation_details, available_quantity, currency, start_price, depot_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (next_id, item_number, title, variation_details, available_quantity, currency, start_price, depot_info),
        )

        # Son eklenen kaydın ID'sini alalım
        new_item_id = cursor.lastrowid if cursor.lastrowid else next_id
        print(f"DEBUG: Yeni eklenen ürün ID: {new_item_id}, türü: {type(new_item_id)}")
        conn.commit()

        # Yeni eklenen ürünün ID'sini kontrol edelim
        check_item = conn.execute("SELECT id FROM inventory WHERE id = ?", (new_item_id,)).fetchone()
        if check_item:
            print(f"DEBUG: Ürün ID'si doğrulandı: {check_item[0]}")
        else:
            print(f"DEBUG: UYARI! Ürün ID'si doğrulanamadı: {new_item_id}")

        # Resim yükleme işlemi
        image_path = None
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_extension = filename.rsplit('.', 1)[1].lower()
                timestamp = str(int(datetime.now().timestamp()))
                safe_filename = f"product_{item_number}_{new_item_id}_{timestamp}.{file_extension}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)

                # Dosyayı kaydet
                file.save(file_path)
                image_path = file_path

                # Resim yolunu güncelle
                conn.execute("UPDATE inventory SET image_path = ? WHERE id = ?", (image_path, new_item_id))
                conn.commit()

        conn.close()

        flash("Yeni ürün başarıyla eklendi!", "success")
        return redirect(url_for("index"))

    return render_template("add_item.html")


# Ürün düzenleme
@app.route("/edit-item/<int:id>", methods=["GET", "POST"])
def edit_item(id):
    id = int(id)  # ID'yi int'e çevir
    conn = get_db_connection()
    item = conn.execute("SELECT * FROM inventory WHERE id = ?", (id,)).fetchone()

    # Ürün ID bulunamazsa hata vermesin
    if not item:
        flash(f"Ürün ID {id} bulunamadı.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        item_number = request.form.get("item_number")
        if not isinstance(item_number, str) or not item_number.isalnum():
            raise BadRequest("Hatalı giriş!")
        title = request.form.get("title")
        variation_details = request.form.get("variation_details")
        available_quantity = int(request.form.get("available_quantity"))
        currency = request.form.get("currency")
        start_price = float(request.form.get("start_price"))
        depot_info = request.form.get("depot_info")

        conn.execute(
            """
            UPDATE inventory
            SET item_number = ?, title = ?, variation_details = ?, available_quantity = ?, currency = ?, start_price = ?, depot_info = ?
            WHERE id = ?
            """,
            (item_number, title, variation_details, available_quantity, currency, start_price, depot_info, id),
        )
        conn.commit()
        conn.close()

        flash("Ürün başarıyla güncellendi!", "success")
        return redirect(url_for("index"))

    conn.close()

    # Dict dönüşümü yaparak HTML'e gönderelim - ID'yi int'e çevir
    item_dict = dict(item)
    item_dict['id'] = int(item_dict['id']) if item_dict['id'] is not None else None

    return render_template("edit_item.html", item=item_dict)


# Ürünü Silme
@app.route("/delete-item/<int:id>", methods=["POST"])
def delete_item(id):
    id = int(id)  # ID'yi int'e çevir
    conn = get_db_connection()
    item = conn.execute("SELECT * FROM inventory WHERE id = ?", (id,)).fetchone()

    if not item:
        flash(f"Ürün ID {id} bulunamadı.", "error")
        return redirect(url_for("index"))

    conn.execute("DELETE FROM inventory WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash(f"Ürün ID {id} başarıyla silindi!", "success")
    return redirect(url_for("index"))


# Resim yükleme
@app.route('/upload-image/<int:id>', methods=['GET', 'POST'])
def upload_image(id):
    id = int(id)  # ID'yi int'e çevir
    if request.method == 'POST':
        conn = get_db_connection()
        item = conn.execute("SELECT * FROM inventory WHERE id = ?", (id,)).fetchone()

        if not item:
            flash(f"Ürün ID {id} bulunamadı.", "error")
            return redirect(url_for("index"))

        # Dosya var mı kontrol et
        if 'file' not in request.files:
            flash('Resim dosyası bulunamadı', 'error')
            return redirect(request.url)

        file = request.files['file']

        # Dosya adı boş mu kontrol et
        if file.filename == '':
            flash('Resim seçilmedi', 'error')
            return redirect(request.url)

        # Geçerli bir dosya mı kontrol et
        if file and allowed_file(file.filename):
            # Eski resmi sil (varsa)
            old_image = item['image_path']
            if old_image and os.path.exists(old_image):
                try:
                    os.remove(old_image)
                except:
                    pass

            # Güvenli dosya adı oluştur - Standart format
            filename = secure_filename(file.filename)
            file_extension = filename.rsplit('.', 1)[1].lower()
            timestamp = str(int(datetime.now().timestamp()))
            safe_filename = f"product_{item['item_number']}_{id}_{timestamp}.{file_extension}"

            # Dosya yolunu oluştur
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)

            # Dosyayı kaydet
            file.save(file_path)

            # Veritabanını güncelle
            conn.execute("UPDATE inventory SET image_path = ? WHERE id = ?",
                         (file_path, id))
            conn.commit()
            conn.close()

            flash('Resim başarıyla yüklendi!', 'success')
            return redirect(url_for('edit_item', id=id))
        else:
            flash('İzin verilen dosya uzantıları: png, jpg, jpeg, gif', 'error')

    # GET isteği - form görüntüleme
    return render_template('upload_image.html', item_id=id)


# Resim görüntüleme
@app.route('/image/<int:id>')
def get_image(id):
    id = int(id)  # ID'yi int'e çevir
    conn = get_db_connection()
    item = conn.execute("SELECT image_path FROM inventory WHERE id = ?", (id,)).fetchone()
    conn.close()

    if not item or not item['image_path'] or not os.path.exists(item['image_path']):
        # Varsayılan resim döndür - exe uyumlu
        try:
            # Önce static klasöründe ara
            default_path = os.path.join('static', 'default-product.png')
            if os.path.exists(default_path):
                return send_from_directory('static', 'default-product.png')
            # Exe durumunda farklı path dene
            elif getattr(sys, 'frozen', False):
                static_path = os.path.join(os.path.dirname(sys.executable), 'static')
                if os.path.exists(os.path.join(static_path, 'default-product.png')):
                    return send_from_directory(static_path, 'default-product.png')
        except:
            pass
        # Varsayılan 1x1 pixel PNG döndür
        from flask import Response
        import base64
        # 1x1 şeffaf PNG data
        tiny_png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
        return Response(tiny_png, mimetype='image/png')

    # Resim dosyasını gönder - exe uyumlu
    try:
        # Exe durumunda UPLOAD_FOLDER ile relative path oluştur  
        if getattr(sys, 'frozen', False):
            # Exe'de çalışırken - upload klasörü exe'nin yanında
            exe_dir = os.path.dirname(sys.executable)
            upload_dir = os.path.join(exe_dir, 'static', 'uploads')
            filename = os.path.basename(item['image_path'])
            full_path = os.path.join(upload_dir, filename)
            
            if os.path.exists(full_path):
                return send_from_directory(upload_dir, filename)
        else:
            # Normal durumda orijinal path kullan
            directory = os.path.dirname(item['image_path'])
            filename = os.path.basename(item['image_path'])
            if os.path.exists(item['image_path']):
                return send_from_directory(directory, filename)
    except Exception as e:
        print(f"Resim gönderme hatası: {e}")
    
    # Hata durumunda varsayılan resim döndür
    from flask import Response
    import base64
    tiny_png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
    return Response(tiny_png, mimetype='image/png')


# Özel test sayfası
@app.route("/test", methods=["GET"])
def test_page():
    try:
        conn = get_db_connection()

        # Sadece tek bir ürün için ID değerine sahip olduğundan emin olalım
        sample_item = conn.execute("SELECT id FROM inventory LIMIT 1").fetchone()
        if sample_item:
            item_id = sample_item[0]

            # Test verisi
            test_data = {
                'id': item_id,
                'item_number': 'TEST123',
                'title': 'Test Item'
            }

            # ID değerini bakalım:
            print(f"Test route, item_id: {item_id}, type: {type(item_id)}")

            # Minimalist bir template render edelim
            conn.close()
            return render_template("test.html", test_item=test_data)
        else:
            return "Veri bulunamadı", 404
    except Exception as e:
        print(f"Test sayfasında hata: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Test sayfasında hata: {str(e)}", 500


@app.route("/ip-monitor", methods=["GET"])
def ip_monitor_dashboard():
    """IP Monitor Dashboard for real-time IP tracking and dynamic IP management"""
    return render_template("ip_dashboard.html")


# Excel'e aktarma fonksiyonu
@app.route("/export-excel", methods=["GET"])
def export_excel():
    try:
        conn = get_db_connection()
        
        # Tüm envanter verilerini al (id ve image_path dahil)
        items = conn.execute("""
            SELECT id, item_number, title, variation_details, available_quantity, 
                   currency, start_price, depot_info, image_path 
            FROM inventory 
            ORDER BY id DESC
        """).fetchall()
        
        conn.close()
        
        # Pandas DataFrame oluştur
        df_data = []
        for item in items:
            df_data.append({
                'id': item['id'],
                'item_number': item['item_number'],
                'title': item['title'],
                'variation_details': item['variation_details'] or '',
                'available_quantity': item['available_quantity'],
                'currency': item['currency'],
                'start_price': item['start_price'],
                'depot_info': item['depot_info'] or '',
                'image_path': item['image_path'] or ''
            })
        
        df = pd.DataFrame(df_data)
        
        # Excel dosyasını geçici dizine kaydet
        excel_filename = f"envanter_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        excel_path = os.path.join(tempfile.gettempdir(), excel_filename)
        
        # Excel dosyasını oluştur
        df.to_excel(excel_path, index=False, sheet_name='Envanter')
        
        # Dosyayı kullanıcıya gönder
        return send_file(excel_path, as_attachment=True, download_name=excel_filename)
        
    except Exception as e:
        print(f"Excel export hatası: {e}")
        import traceback
        traceback.print_exc()
        flash(f"Excel dosyası oluşturulamadı: {str(e)}", "error")
        return redirect(url_for("index"))


# Uygulama başlatma
if __name__ == "__main__":
    print("🚀 Envanter Yönetim Sistemi")
    
    # Template ve static klasörlerin varlığını kontrol et (PyInstaller için)
    templates_path = resource_path('templates')
    static_path = resource_path('static')
    
    if not os.path.exists(templates_path):
        print("❌ 'templates' klasörü bulunamadı!")
        print(f"Çalışma dizini: {os.getcwd()}")
        print(f"Aranan templates path: {templates_path}")
        print(f"PyInstaller frozen: {getattr(sys, 'frozen', False)}")
        if hasattr(sys, '_MEIPASS'):
            print(f"_MEIPASS: {sys._MEIPASS}")
            print(f"_MEIPASS içeriği: {os.listdir(sys._MEIPASS)}")
        input("Çıkmak için Enter tuşuna basın...")
        sys.exit(1)
    
    if not os.path.exists(static_path):
        print("❌ 'static' klasörü bulunamadı!")
        print(f"Çalışma dizini: {os.getcwd()}")
        print(f"Aranan static path: {static_path}")
        input("Çıkmak için Enter tuşuna basın...")
        sys.exit(1)
    
    print("📊 Veritabanı hazırlanıyor...")
    try:
        initialize_database()
        print("✅ Sistem hazır!")
    except Exception as e:
        print(f"❌ Veritabanı hatası: {e}")
        input("Çıkmak için Enter tuşuna basın...")
        sys.exit(1)
    
    print("🌐 Web arayüzü: http://localhost:5000")
    print("📱 Mobil erişim: http://0.0.0.0:5000")
    print("⚡ Kapatmak için Ctrl+C")
    print("-" * 40)
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 Sunucu kullanıcı tarafından durduruldu")
    except Exception as e:
        print(f"❌ Sunucu hatası: {e}")
        print(f"Hata detayı: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        input("Çıkmak için Enter tuşuna basın...")
    finally:
        print("👋 Uygulama kapatıldı")

