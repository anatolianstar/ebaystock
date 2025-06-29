import qrcode
import tkinter as tk
from tkinter import Toplevel, Label, Button, ttk, filedialog, messagebox
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib.pagesizes import letter
import sqlite3
import os
import pandas as pd
from PIL import Image, ImageTk, ImageDraw, ExifTags
from shutil import copyfile
import uuid
import re
import random
import string
import time


class InventoryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Manager")
        
        # Resim yükleme klasörünü oluştur
        self.upload_folder = 'static/uploads'
        os.makedirs(self.upload_folder, exist_ok=True)
        
        # Thumbnail klasörü oluştur
        self.thumbnail_folder = 'static/thumbnails'
        os.makedirs(self.thumbnail_folder, exist_ok=True)
        
        self.allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        
        # İkon resimleri için değişkenler
        self.image_icon = None
        self.no_image_icon = None
        self.load_icons()
        
        # TreeView için ikonları saklayacak dictionary
        self.tree_icons = {}
        
        # Resim önizleme penceresi için değişken
        self.preview_window = None
        
        # Modern stil oluştur
        self.setup_styles()

        self.create_database()
        self.setup_ui()

    def load_icons(self):
        """İkon resimlerini yükler"""
        try:
            # Resim ikonu klasörünü kontrol et
            icon_folder = "static/icons"
            os.makedirs(icon_folder, exist_ok=True)
            
            icon_path = os.path.join(icon_folder, "image_icon.png")
            
            # Eğer ikon dosyası yoksa, oluştur ve kaydet
            if not os.path.exists(icon_path):
                # Mavi bir resim ikonu oluştur
                img = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
                # Dikdörtgen çiz
                draw = ImageDraw.Draw(img)
                draw.rectangle([2, 2, 21, 21], outline=(0, 120, 215), width=2, fill=(173, 216, 230))
                # Küçük kare çiz (resim ikonunu temsil etmek için)
                draw.rectangle([6, 6, 18, 14], outline=(0, 80, 180), width=1, fill=(135, 206, 250))
                img.save(icon_path)
                print(f"Resim ikonu oluşturuldu: {icon_path}")
            else:
                img = Image.open(icon_path)
                print(f"Mevcut resim ikonu kullanıldı: {icon_path}")
            
            # İkonu yükle ve tkinter PhotoImage'e dönüştür
            img = img.resize((24, 24), Image.LANCZOS)
            self.image_icon = ImageTk.PhotoImage(img)
            print("Resim ikonu başarıyla yüklendi")
            
            # Resim olmayan ikon (boş saydam ikon)
            img = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
            self.no_image_icon = ImageTk.PhotoImage(img)
            
        except Exception as e:
            print(f"İkon yükleme hatası: {e}")
            # Hata durumunda basit ikonlar oluştur
            try:
                img = Image.new('RGBA', (24, 24), (255, 0, 0, 128))  # Kırmızı yarı saydam
                self.image_icon = ImageTk.PhotoImage(img)
                print("Hata durumu için kırmızı ikon oluşturuldu")
                
                img = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
                self.no_image_icon = ImageTk.PhotoImage(img)
            except Exception as ex:
                print(f"Basit ikon oluşturma hatası: {ex}")

    def setup_styles(self):
        # Modern buton stilleri oluştur
        self.style = ttk.Style()
        
        # Ana tema
        if os.name == 'nt':  # Windows
            self.style.theme_use('vista')
        else:
            self.style.theme_use('clam')
            
        # Modern buton stili
        self.style.configure('Modern.TButton', 
                             font=('Arial', 10),
                             background='#4CAF50',
                             foreground='black',
                             padding=6,
                             relief='flat')
        
        self.style.map('Modern.TButton',
                       background=[('active', '#45a049'), ('pressed', '#3e8e41')],
                       relief=[('pressed', 'sunken')])
                       
        # TreeView stili
        self.style.configure('Treeview',
                             rowheight=25,
                             font=('Arial', 10))
                             
        self.style.configure('Treeview.Heading',
                             font=('Arial', 10, 'bold'))

    def create_database(self):
        self.conn = sqlite3.connect("database.db")
        self.cursor = self.conn.cursor()
        
        # Kontrol et - "id" sütunu var mı?
        self.cursor.execute("PRAGMA table_info(inventory)")
        columns = self.cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        # Eğer tablo yoksa oluştur
        if not columns:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER,
                    item_number TEXT PRIMARY KEY,
                    title TEXT,
                    variation_details TEXT,
                    available_quantity INTEGER,
                    currency TEXT,
                    start_price REAL,
                    depot_info TEXT,
                    image_path TEXT
                )
            ''')
            print("Tablo oluşturuldu")
        # Eğer tablo var ama id sütunu yoksa ekle
        elif 'id' not in column_names:
            self.cursor.execute("ALTER TABLE inventory ADD COLUMN id INTEGER")
            print("id sütunu eklendi")
            
        # Eğer image_path sütunu yoksa, ekleyelim
        if 'image_path' not in column_names:
            try:
                self.cursor.execute("ALTER TABLE inventory ADD COLUMN image_path TEXT")
                self.conn.commit()
                print("image_path sütunu eklendi")
            except sqlite3.OperationalError:
                # Sütun zaten varsa hata vermez
                pass
            
        self.conn.commit()

    def setup_ui(self):
        # Ana çerçeve - tüm içeriği içerecek
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Pencerenin başlangıç boyutu ve ekranın ortasında konumlandırma
        window_width = 1200
        window_height = 800
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Pencereyi ekranın ortasına konumlandır
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        
        # Butonlar için ana bir çerçeve oluştur (ortalamak için)
        button_container = ttk.Frame(main_frame)
        button_container.pack(pady=10, fill=tk.X)
        
        # Butonlar için iç çerçeveyi oluştur ve ortala
        button_frame = ttk.Frame(button_container)
        button_frame.pack(anchor=tk.CENTER)
        
        # Butonları yan yana ekle
        ttk.Button(button_frame, text="Load Excel", command=self.load_excel, style='Modern.TButton').grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="Export to Excel", command=self.export_to_excel, style='Modern.TButton').grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="Add New Item", command=self.add_new_item, style='Modern.TButton').grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(button_frame, text="Load Inventory", command=self.load_inventory, style='Modern.TButton').grid(row=0, column=3, padx=5, pady=5)
        ttk.Button(button_frame, text="Edit Selected Item", command=self.edit_item, style='Modern.TButton').grid(row=0, column=4, padx=5, pady=5)
        ttk.Button(button_frame, text="Print Selected Item", command=self.print_selected_item, style='Modern.TButton').grid(row=0, column=5, padx=5, pady=5)
        ttk.Button(button_frame, text="Delete Selected Item", command=self.delete_selected_item, style='Modern.TButton').grid(row=0, column=6, padx=5, pady=5)
        ttk.Button(button_frame, text="Remove Zero Items", command=self.remove_zero_quantity_items, style='Modern.TButton').grid(row=0, column=7, padx=5, pady=5)

        # Arama bölümü için ana çerçeve
        search_container = ttk.Frame(main_frame)
        search_container.pack(fill=tk.X, pady=5)
        
        # Arama bölümü için iç çerçeve (ortalamak için)
        search_frame = ttk.Frame(search_container)
        search_frame.pack(anchor=tk.CENTER)
        
        ttk.Label(search_frame, text="Search (Item Number, Title, Variation):", font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(search_frame, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Search", command=self.search, style='Modern.TButton').pack(side=tk.LEFT, padx=5)

        # TreeView çerçevesi ve scrollbar
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Scrollbar'lar
        y_scrollbar = ttk.Scrollbar(tree_frame)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        x_scrollbar = ttk.Scrollbar(tree_frame, orient='horizontal')
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # TreeView ve diğer bileşenler
        columns = (
            "ID", "Item Number", "Title", "Variation Details", "Available Quantity", "Currency", "Start Price", "depot info", "Image"
        )
        
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=30,
                                 yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        y_scrollbar.config(command=self.tree.yview)
        x_scrollbar.config(command=self.tree.xview)
        
        for col in columns:
            self.tree.heading(col, text=col if col != "Image" else "", anchor=tk.CENTER)
            if col == "Image":
                self.tree.column(col, width=40, minwidth=40, anchor=tk.CENTER, stretch=False)
            elif col == "ID":
                self.tree.column(col, width=50, minwidth=50, anchor=tk.CENTER, stretch=False)
            elif col == "Item Number":
                self.tree.column(col, width=120, minwidth=100, anchor=tk.CENTER, stretch=False)
            elif col in ["Available Quantity", "Currency", "Start Price"]:
                self.tree.column(col, width=100, minwidth=80, anchor=tk.CENTER, stretch=False)
            elif col in ["Title", "Variation Details", "depot info"]:
                self.tree.column(col, width=200, minwidth=150, anchor=tk.CENTER, stretch=True)
            else:
                self.tree.column(col, width=100, minwidth=80, anchor=tk.CENTER, stretch=True)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Klavye olayları için bağlayıcılar
        self.tree.bind("<Key>", self.on_key_press)
        self.tree.bind("<Up>", self.on_arrow_key)
        self.tree.bind("<Down>", self.on_arrow_key)
        self.tree.bind("<Next>", self.on_page_key)  # Page Down
        self.tree.bind("<Prior>", self.on_page_key)  # Page Up
        self.tree.bind("<Home>", self.on_home_end_key)
        self.tree.bind("<End>", self.on_home_end_key)
        
        # Seçim değişikliğinde otomatik ortalama
        self.tree.bind("<<TreeviewSelect>>", self.center_selected_item)
        
        # Fare olayları
        self.tree.bind("<Motion>", self.on_mouse_move)  # Fare hareketi
        self.tree.bind("<Leave>", self.on_mouse_leave)  # Fare pencereden çıktığında

        # Depo bilgisi güncelleme bölümü için ana çerçeve
        depot_container = ttk.Frame(main_frame)
        depot_container.pack(fill=tk.X, pady=10)
        
        # Depo bilgisi güncelleme bölümü için iç çerçeve (ortalamak için)
        depot_frame = ttk.Frame(depot_container)
        depot_frame.pack(anchor=tk.CENTER)
        
        ttk.Label(depot_frame, text="Enter depot Info:", font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        self.depot_entry = ttk.Entry(depot_frame, width=40)
        self.depot_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(depot_frame, text="Update Depot", command=self.update_depot, style='Modern.TButton').pack(side=tk.LEFT, padx=5)

        # Toplam değer etiketi için çerçeve
        total_frame = ttk.Frame(main_frame)
        total_frame.pack(fill=tk.X, pady=10)
        
        # Toplam değer etiketi
        self.total_label = ttk.Label(total_frame, text="Total Inventory Value: $0", font=('Arial', 12, 'bold'))
        self.total_label.pack(anchor=tk.CENTER)

        # Çift tıklama olayını edit_item metoduna bağla
        self.tree.bind("<Double-1>", self.on_double_click)

        # Başlangıçta envanteri yükle
        self.load_inventory()

    def on_mouse_move(self, event):
        """Fare hareketi olayını işler"""
        # Farenin olduğu öğeyi ve sütunu al
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        
        # İşlemi image sütunu için sınırla
        if column == "#1" and item:  # #1 = "Image" sütunu
            try:
                # Öğenin resim yolunu al
                image_path = self.get_image_path_for_item(item)
                if image_path and os.path.exists(image_path):
                    # İmlecin ekran konumunu al
                    x, y = event.x_root, event.y_root
                    # Resmi görüntüle
                    self.show_image_preview(image_path, x, y)
                    return
            except Exception as e:
                print(f"Resim önizleme hatası: {e}")
        
        # Diğer durumlar için önizleme penceresini kapat
        self.hide_image_preview()

    def on_mouse_leave(self, event):
        """Fare pencereden ayrıldığında önizleme penceresini kapatır"""
        self.hide_image_preview()

    def get_image_path_for_item(self, item_id):
        """TreeView öğe ID'sine göre resim yolunu döndürür"""
        item_values = self.tree.item(item_id, "values")
        item_number = item_values[1]  # Item Number - daha güvenilir bir tanımlayıcı
        
        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute("SELECT image_path FROM inventory WHERE item_number = ?", (item_number,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                return result[0]
            return None
        except Exception as e:
            print(f"Resim yolu sorgulama hatası: {e}")
            return None

    def show_image_preview(self, image_path, x, y):
        """Resmin önizlemesini gösterir"""
        try:
            # Eğer önizleme penceresi zaten açıksa, kapat
            if self.preview_window and self.preview_window.winfo_exists():
                self.preview_window.destroy()
            
            # Yeni önizleme penceresi oluştur
            self.preview_window = tk.Toplevel(self.root)
            self.preview_window.overrideredirect(True)  # Başlık çubuğunu kaldır
            self.preview_window.wm_attributes("-topmost", True)  # Her zaman üstte
            
            # Önizleme boyutu
            preview_width = 400
            preview_height = 400
            
            # Ekran boyutlarını al
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Ekranın ortasında konumlandır
            x_position = (screen_width - preview_width) // 2
            y_position = (screen_height - preview_height) // 2
            
            # Pencereyi ekranın ortasına konumlandır
            self.preview_window.geometry(f"{preview_width}x{preview_height}+{x_position}+{y_position}")
            
            # Kenarlık ekle - daha belirgin olması için
            frame = ttk.Frame(self.preview_window, relief='solid', borderwidth=2)
            frame.pack(fill="both", expand=True, padx=2, pady=2)
            
            # Resmi yükle ve göster
            img = Image.open(image_path)
            img = self.fix_image_rotation(img)
            img = img.resize((preview_width-10, preview_height-10), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            # Resmi içerecek etiket
            label = Label(frame, image=photo, bg="white")
            label.image = photo  # Referansı tut
            label.pack(fill="both", expand=True)
            
            # Kapatma butonu ekle
            close_btn = ttk.Button(frame, text="Kapat", command=self.hide_image_preview)
            close_btn.pack(side="bottom", pady=5)
            
            # Escape tuşu ile kapatma
            self.preview_window.bind("<Escape>", lambda e: self.hide_image_preview())
            # Tıklama ile kapatma 
            self.preview_window.bind("<Button-1>", lambda e: self.hide_image_preview())
            
        except Exception as e:
            print(f"Önizleme penceresi oluşturma hatası: {e}")
            if self.preview_window and self.preview_window.winfo_exists():
                self.preview_window.destroy()
                self.preview_window = None

    def hide_image_preview(self):
        """Resim önizleme penceresini kapatır"""
        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_window.destroy()
            self.preview_window = None

    def on_double_click(self, event):
        """Çift tıklama gerçekleştiğinde edit_item metodunu çağırır"""
        self.edit_item()

    def print_selected_item(self):
        """Seçili öğe için print penceresi açar"""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select an item to print.")
            return
        
        item_values = self.tree.item(selected_item, "values")
        if not item_values:
            return
            
        self.open_print_options(item_values)

    def create_thumbnail(self, image_path, item_number, force_recreate=False):
        """
        Resim için küçük bir thumbnail oluşturur ve thumbnail klasöründe saklar.
        Eğer thumbnail zaten varsa, yeniden oluşturmaz (force_recreate=True olmadıkça).
        
        :param image_path: Orijinal resmin tam yolu
        :param item_number: Ürün numarası
        :param force_recreate: Thumbnail'i zorla yeniden oluşturma bayrağı
        :return: Thumbnail'in tam dosya yolu
        """
        # Resim dosyası yoksa None döndür
        if not image_path or not os.path.exists(image_path):
            return None
            
        # Uzantıyı al
        _, file_extension = os.path.splitext(image_path.lower())
        if not file_extension:
            file_extension = ".jpg"  # Varsayılan uzantı
            
        # Thumbnail dosya adı oluştur (ürün numarası ile)
        thumbnail_filename = f"thumb_{item_number}{file_extension}"
        thumbnail_path = os.path.join(self.thumbnail_folder, thumbnail_filename)
        
        # Eğer thumbnail varsa ve zorunlu yeniden oluşturma istenmediyse, mevcut dosyayı döndür
        if os.path.exists(thumbnail_path) and not force_recreate:
            return thumbnail_path
            
        try:
            # Resmi yükle ve küçük boyuta getir
            img = Image.open(image_path)
            img = self.fix_image_rotation(img)
            img = img.resize((24, 24), Image.LANCZOS)
            
            # Thumbnail'i kaydet
            img.save(thumbnail_path)
            print(f"Thumbnail oluşturuldu: {thumbnail_path}")
            
            return thumbnail_path
        except Exception as e:
            print(f"Thumbnail oluşturma hatası: {e}")
            return None

    def load_inventory(self):
        try:
            # İkon sözlüğünü temizle
            self.tree_icons.clear()
            
            start_time = time.time()  # Yükleme süresini ölçmek için
            
            conn = sqlite3.connect("database.db")
            
            # ID değerlerini düzelt - önce mevcut ID'leri kontrol et
            cursor = conn.cursor()
            cursor.execute("SELECT rowid, id FROM inventory")
            rows = cursor.fetchall()
            
            # NaN veya hatalı ID'leri düzelt
            for row in rows:
                rowid, id_val = row
                # ID boş, NaN veya geçersiz mi?
                fix_needed = False
                
                if id_val is None:
                    fix_needed = True
                else:
                    try:
                        # Ondalıklı sayı kontrolü
                        float_id = float(id_val)
                        if float_id != int(float_id):  # '304.0' gibi ondalıklı bir değer
                            fix_needed = True
                            id_val = int(float_id)
                    except (ValueError, TypeError):
                        fix_needed = True
                        id_val = rowid  # rowid'yi ID olarak kullan
                
                # ID'yi düzeltmek gerekiyorsa
                if fix_needed:
                    try:
                        cursor.execute("UPDATE inventory SET id = ? WHERE rowid = ?", (rowid, rowid))
                        print(f"ID düzeltildi: rowid={rowid}, yeni id={rowid}")
                    except Exception as e:
                        print(f"ID düzeltme hatası: {e}")
            
            conn.commit()
            
            # Sorguyu güncelle, id sütununu kullan
            df = pd.read_sql_query("SELECT id as ID, item_number, title, variation_details, available_quantity, currency, start_price, depot_info, image_path FROM inventory ORDER BY id DESC", conn)
            conn.close()

            # TreeView'i temizle
            for row in self.tree.get_children():
                self.tree.delete(row)

            # Verileri TreeView'e ekle
            for idx, row in df.iterrows():
                values = list(row)
                # ID değerini düzgün formatla
                try:
                    if pd.isna(values[0]):
                        values[0] = idx + 1
                    else:
                        values[0] = int(float(values[0]))
                except (ValueError, TypeError):
                    values[0] = idx + 1
                # Formatlamalar
                values[5] = str(values[5])  # Currency
                try:
                    values[6] = f"{float(values[6]):.2f}"  # Start price
                except ValueError:
                    values[6] = str(values[6])
                # Resim ikonu için emoji kullan
                image_path = values[8]  # image_path
                image_icon = "📷" if image_path and os.path.exists(image_path) else ""
                item_values = values[:8] + [image_icon]  # Image sütunu en sağda
                self.tree.insert("", "end", values=item_values)

            self.calculate_total_value()
            
            end_time = time.time()
            print(f"Envanter yükleme süresi: {end_time - start_time:.2f} saniye")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load inventory: {e}")
            print(f"Load inventory error: {e}")

    def calculate_total_value(self):
        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(CASE WHEN typeof(start_price) = 'text' THEN 0 ELSE available_quantity * start_price END) FROM inventory")
            total_value = cursor.fetchone()[0] or 0
            conn.close()
            self.total_label.config(
                text=f"Total Inventory Value: ${total_value:.2f}" if total_value else "Total Inventory Value: $0"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to calculate total inventory value: {e}")

    def load_excel(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
        if not file_path:
            return
        action = messagebox.askquestion("Load Excel",
                                        "Do you want to append to the existing data? (Yes: Append, No: Replace)")
        if action == "yes":
            confirmation = messagebox.askyesno(
                "Confirmation",
                "You are about to append the data from the selected Excel file to the current inventory. Do you want to continue?",
            )
            if confirmation:
                self.load_excel_to_db(file_path, append=True)
        elif action == "no":
            confirmation = messagebox.askyesno(
                "Confirmation",
                "This action will replace the current inventory with data from the selected Excel file. Do you want to continue?",
            )
            if confirmation:
                self.load_excel_to_db(file_path, append=False)

    def load_excel_to_db(self, file_path, append=False):
        # Excel'den yüklemeden önce boş değerleri düzenle
        def clean_data(value):
            if pd.isna(value) or value == "":
                return ""
            return value

        try:
            df = pd.read_excel(file_path)

            # Boş değerleri temizle
            if "variation_details" in df.columns:
                df["variation_details"] = df["variation_details"].apply(clean_data)
            if "depot_info" in df.columns:
                df["depot_info"] = df["depot_info"].apply(clean_data)

            # start_price değerlerini 0.00 formatına çevir
            if "start_price" in df.columns:
                # Güvenli dönüşüm için try-except kullan
                def safe_float_convert(x):
                    try:
                        return f"{float(x):.2f}"
                    except (ValueError, TypeError):
                        return str(x)
                
                df["start_price"] = df["start_price"].map(safe_float_convert)
                
            # Ensure currency is a string
            if "currency" in df.columns:
                df["currency"] = df["currency"].astype(str)

            df.rename(
                columns={
                    "Item number": "item_number",
                    "Title": "title",
                    "Variation details": "variation_details",
                    "Available quantity": "available_quantity",
                    "Currency": "currency",
                    "Start price": "start_price",
                },
                inplace=True,
            )
            required_columns = [
                "item_number",
                "title",
                "variation_details",
                "available_quantity",
                "currency",
                "start_price",
            ]
            if not all((col in df.columns for col in required_columns)):
                messagebox.showerror("Error", "Excel file headers do not match the expected format.")
                return
            with sqlite3.connect("database.db") as conn:
                if append:
                    df.to_sql("inventory", conn, if_exists="append", index=False)
                else:
                    df.to_sql("inventory", conn, if_exists="replace", index=False)
            messagebox.showinfo("Success", "Data successfully loaded into the database.")
            self.load_inventory()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")

    def export_to_excel(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if not file_path:
            return
        conn = sqlite3.connect("database.db")
        df = pd.read_sql_query("SELECT * FROM inventory", conn)
        conn.close()

        # start_price sütununu 0.00 formatına çevir
        df["item_number"] = df["item_number"].astype(str)
        # Güvenli dönüşüm için try-except kullan
        def safe_float_convert(x):
            try:
                return f"{float(x):.2f}"
            except (ValueError, TypeError):
                return str(x)
        
        df["start_price"] = df["start_price"].map(safe_float_convert)
        df["currency"] = df["currency"].astype(str)  # Ensure currency is a string


        try:
            df.to_excel(file_path, index=False)
            messagebox.showinfo("Success", "Data successfully exported to Excel.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export data: {e}")

    def get_next_id(self):
        """Bir sonraki ID numarasını döndürür"""
        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            
            # Mevcut en yüksek ID'yi bul
            cursor.execute("SELECT MAX(id) FROM inventory")
            result = cursor.fetchone()[0]
            conn.close()
            
            if result is not None:
                # Ondalıklı değer olabilir, önce float'a çevirip sonra int'e çevirelim
                try:
                    # None olmayan ama '304.0' gibi ondalıklı gözüken bir string olabilir
                    if isinstance(result, str):
                        result = float(result)
                    # Float ise int'e çevir
                    next_id = int(float(result)) + 1
                    print(f"Mevcut max ID: {result}, sonraki ID: {next_id}")
                    return next_id
                except (ValueError, TypeError) as e:
                    print(f"ID dönüşüm hatası: {e}, ID: {result}")
                    # Hata durumunda veritabanını tarayarak en yüksek ID'yi bulmaya çalışalım
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM inventory")
                    all_ids = cursor.fetchall()
                    max_id = 0
                    for id_val in all_ids:
                        if id_val[0] is not None:
                            try:
                                id_int = int(float(id_val[0]))
                                if id_int > max_id:
                                    max_id = id_int
                            except (ValueError, TypeError):
                                pass
                    return max_id + 1
            
            # Hiç ID yoksa veya hepsi None ise 1'den başla
            return 1
                
        except Exception as e:
            print(f"ID alınırken hata: {e}")
            return 1  # Hata durumunda 1 döndür

    def generate_next_item_number(self, last_item_number=None):
        """Rastgele benzersiz 10 haneli alfanumerik kod oluşturur"""
        try:
            # UUID kullanarak benzersiz bir kod oluştur
            random_id = str(uuid.uuid4())
            
            # UUID'den sadece alfanumerik karakterleri al (tire ve noktaları çıkar)
            clean_id = random_id.replace('-', '').replace('.', '')
            
            # 10 haneli olacak şekilde kes (ilk 10 karakter)
            item_number = clean_id[:10].upper()
            
            print(f"Oluşturulan yeni benzersiz item number: {item_number}")
            return item_number
                
        except Exception as e:
            print(f"Item number oluşturulurken hata: {e}")
            # Hata durumunda alternatif yöntem
            
            # 10 haneli rastgele kod
            item_number = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
            print(f"Alternatif yöntemle oluşturulan item number: {item_number}")
            return item_number

    def add_new_item(self):
        try:
            add_window = tk.Toplevel(self.root)
            add_window.title("Add New Item")
            
            # Rastgele benzersiz item_number oluştur (önceki numaradan bağımsız)
            next_item_number = self.generate_next_item_number()
            print(f"Yeni ürün için benzersiz item number: {next_item_number}")
            
            # Bir sonraki ID'yi belirle - integer olduğundan emin ol
            next_id = self.get_next_id()
            print(f"Yeni ürün için ID: {next_id}")
            
            # Tüm alanlar için frame
            fields_frame = ttk.Frame(add_window, padding=10)
            fields_frame.pack(fill="both", expand=True)
            
            # ID göster (salt okunur)
            ttk.Label(fields_frame, text="ID:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
            id_entry = ttk.Entry(fields_frame, width=10)
            id_entry.insert(0, str(next_id))
            id_entry.config(state="readonly")
            id_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
            
            # Alanları oluştur
            fields = ["Item Number", "Title", "Variation Details", "Available Quantity", "Currency", "Start Price",
                    "depot info"]
            entries = {}
                
            # Her alan için etiket ve giriş alanı
            for i, field in enumerate(fields):
                # Etiket oluştur
                ttk.Label(fields_frame, text=f"{field}:").grid(row=i+1, column=0, sticky=tk.W, pady=5, padx=5)
                
                # Giriş alanı oluştur
                entry = ttk.Entry(fields_frame, width=40)
                entry.grid(row=i+1, column=1, sticky=tk.W, pady=5, padx=5)
                
                # Item Number için varsayılan değer
                if field == "Item Number":
                    entry.insert(0, next_item_number)
                    # Bu artık salt okunur olmasın, kullanıcı düzenleyebilsin
                    # entry.config(state="readonly")
                
                # Currency için varsayılan değer
                if field == "Currency":
                    entry.insert(0, "$")  # USD yerine $ kullan
                
                entries[field] = entry

            # Resim yükleme kısmı
            image_frame = ttk.LabelFrame(add_window, text="Product Image", padding=10)
            image_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Resim gösterme alanı
            image_display = ttk.Label(image_frame, text="No Image Selected", width=40, background="lightgray")
            image_display.pack(pady=10)
            
            # Seçilen resim dosyası için değişken
            selected_image_path = None
            
            def select_image():
                nonlocal selected_image_path
                file_path = filedialog.askopenfilename(
                    filetypes=[
                        ("Image files", "*.png *.jpg *.jpeg *.gif"),
                        ("All files", "*.*")
                    ]
                )
                if not file_path:
                    return
                    
                if not self.allowed_file(file_path):
                    messagebox.showerror("Error", "Only PNG, JPG, JPEG and GIF files are allowed.")
                    return
                    
                # Resmi görüntüle
                try:
                    img = Image.open(file_path)
                    img = self.fix_image_rotation(img)
                    img = img.resize((150, 150), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    image_display.config(image=photo, text="")
                    image_display.image = photo
                    
                    # Dosya yolunu kaydet
                    selected_image_path = file_path
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load image: {e}")
            
            # Resim seçme butonu
            ttk.Button(image_frame, text="Select Image", command=select_image).pack(pady=5)
            
            def save_new_item():
                try:
                    new_item = {field: entry.get() for field, entry in entries.items()}
                        
                    # Boş alan kontrolü
                    if not new_item["Item Number"] or not new_item["Title"]:
                        messagebox.showerror("Error", "Item Number and Title are required fields.")
                        return
                        
                    # Sayısal alan kontrolü
                    try:
                        quantity = int(new_item["Available Quantity"]) if new_item["Available Quantity"] else 0
                    except ValueError:
                        messagebox.showerror("Error", "Available Quantity must be a number.")
                        return
                        
                    try:
                        price = float(new_item["Start Price"]) if new_item["Start Price"] else 0.0
                    except ValueError:
                        messagebox.showerror("Error", "Start Price must be a number.")
                        return
                    
                    # Resim dosyasını kopyala (eğer seçilmişse)
                    image_path = None
                    if selected_image_path:
                        try:
                            # Dosya uzantısını al
                            file_extension = os.path.splitext(selected_image_path)[1].lower()
                            
                            # Benzersiz dosya adı oluştur
                            safe_filename = f"product_{new_item['Item Number']}_{str(uuid.uuid4())[:8]}{file_extension}"
                            destination = os.path.join(self.upload_folder, safe_filename)
                            
                            # Klasörü kontrol et, yoksa oluştur
                            os.makedirs(os.path.dirname(destination), exist_ok=True)
                            
                            # Dosyayı kopyala
                            copyfile(selected_image_path, destination)
                            
                            # Thumbnail oluştur (küçük resim ikonları için)
                            self.create_thumbnail(destination, new_item["Item Number"], force_recreate=True)
                            
                            # Resim yolunu kaydet
                            image_path = destination
                        except Exception as e:
                            messagebox.showerror("Error", f"Failed to save image: {e}")
                            return
                    
                    # Veritabanına kaydet (ID dahil) - ID değerinin kesinlikle integer olduğundan emin ol
                    conn = sqlite3.connect("database.db")
                    cursor = conn.cursor()
                    
                    # next_id'nin integer olduğundan emin ol
                    safe_id = int(next_id)
                    
                    cursor.execute(
                        '''
                            INSERT INTO inventory (id, item_number, title, variation_details, available_quantity, currency, start_price, depot_info, image_path)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''',
                        (
                            safe_id,
                            new_item["Item Number"],
                            new_item["Title"],
                            new_item["Variation Details"],
                            quantity,
                            new_item["Currency"],
                            price,
                            new_item["depot info"],
                            image_path,
                        ),
                    )
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("Success", "New item added successfully.")
                    add_window.destroy()
                    self.load_inventory()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add item: {e}")
                    print(f"Ürün ekleme hatası: {e}")
            
            # Butonlar için frame
            button_frame = ttk.Frame(add_window)
            button_frame.pack(pady=10)
            
            # Kaydet ve İptal butonları
            ttk.Button(button_frame, text="Save", command=save_new_item).grid(row=0, column=0, padx=10)
            ttk.Button(button_frame, text="Cancel", command=add_window.destroy).grid(row=0, column=1, padx=10)
            
            # Pencereyi ortala
            add_window.update_idletasks()
            width = add_window.winfo_width()
            height = add_window.winfo_height()
            x = (add_window.winfo_screenwidth() // 2) - (width // 2)
            y = (add_window.winfo_screenheight() // 2) - (height // 2)
            add_window.geometry(f"{width}x{height}+{x}+{y}")
            
            # Modal pencere olarak göster
            add_window.transient(self.root)
            add_window.grab_set()
            self.root.wait_window(add_window)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open Add New Item window: {e}")
            print(f"add_new_item fonksiyonunda hata: {e}")
            # Hata durumunda bile ana verileri yükle
            self.load_inventory()

    def edit_item(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select an item to edit.")
            return
        item_values = self.tree.item(selected_item, "values")
        
        # Debug info
        print("Selected item values:", item_values)
        
        # Düzeltilmiş indeksler - Image sütunu artık values'ta değil, ayrı olarak eklendiği için
        item_id = int(item_values[0])      # ID
        item_number = item_values[1]       # Item Number
        title = item_values[2]             # Title
        variation = item_values[3]         # Variation Details
        
        # Güvenli dönüşümler
        try:
            current_quantity = int(float(item_values[4]))  # Available Quantity
        except ValueError:
            current_quantity = 0 
            
        currency = item_values[5]          # Currency
            
        try:
            current_price = float(item_values[6])  # Start Price
        except ValueError:
            current_price = 0.0
            
        current_depot = item_values[7]     # Depot Info
        
        # Mevcut resim yolunu al - item_number ile sorgula (daha güvenilir)
        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute("SELECT image_path FROM inventory WHERE item_number = ?", (item_number,))
            result = cursor.fetchone()
            current_image_path = result[0] if result and result[0] else None
            conn.close()
            
            print(f"Düzenlenen ürün: {item_number}, Resim yolu: {current_image_path}")
        except Exception as e:
            print(f"Resim yolu alınırken hata: {e}")
            current_image_path = None

        # Düzenleme penceresini oluştur
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"Edit Item: {item_number}")
        edit_window.geometry("800x700")
        
        # Frame'leri oluştur
        main_frame = ttk.Frame(edit_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sol ve sağ panel için container
        panels_frame = ttk.Frame(main_frame)
        panels_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Sol panel - form alanları
        form_frame = ttk.Frame(panels_frame, padding=10)
        form_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Sağ panel - resim alanı
        image_frame = ttk.Frame(panels_frame, padding=10, relief="solid", borderwidth=1)
        image_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Resim alanı başlığı
        ttk.Label(image_frame, text="Product Image", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Resim görüntüleme alanı
        image_display_frame = ttk.Frame(image_frame, width=300, height=300)
        image_display_frame.pack(pady=10)
        
        # Varsayılan resim veya mevcut resim
        image_label = Label(image_display_frame, text="No Image", bg="lightgray", width=40, height=15)
        image_label.pack()
        
        # Resim varsa göster
        if current_image_path and os.path.exists(current_image_path):
            try:
                img = Image.open(current_image_path)
                img = self.fix_image_rotation(img)
                img = img.resize((300, 300), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                image_label.config(image=photo, width=300, height=300, text="")
                image_label.image = photo  # Referans tutma
            except Exception as e:
                print(f"Resim yüklenirken hata: {e}")
        
        # Resim yükleme butonu - ana upload_image metodunu kullan
        def upload_new_image():
            nonlocal current_image_path
            new_path = self.upload_image(item_number, image_label, current_image_path)
            if new_path:
                current_image_path = new_path
        
        ttk.Button(image_frame, text="Upload Image", command=upload_new_image).pack(pady=10)
        
        # Düzenlenemeyen bilgiler
        ttk.Label(form_frame, text="ID & Item Number (Cannot be edited):", font=("Arial", 10, "bold")).pack(pady=5, anchor=tk.W)
        ttk.Label(form_frame, text=f"ID: {item_id} | Item Number: {item_number}").pack(pady=5, anchor=tk.W)
        
        # Tüm düzenlenebilir alanlar için Entry widget'ları
        ttk.Label(form_frame, text="Title:").pack(pady=(10, 0), anchor=tk.W)
        title_entry = ttk.Entry(form_frame, width=50)
        title_entry.insert(0, title)
        title_entry.pack(pady=5, fill=tk.X)
        
        ttk.Label(form_frame, text="Variation Details:").pack(pady=(10, 0), anchor=tk.W)
        variation_entry = ttk.Entry(form_frame, width=50)
        variation_entry.insert(0, variation)
        variation_entry.pack(pady=5, fill=tk.X)
        
        ttk.Label(form_frame, text="Quantity:").pack(pady=(10, 0), anchor=tk.W)
        quantity_entry = ttk.Entry(form_frame)
        quantity_entry.insert(0, current_quantity)
        quantity_entry.pack(pady=5, fill=tk.X)
        
        ttk.Label(form_frame, text="Currency:").pack(pady=(10, 0), anchor=tk.W)
        currency_entry = ttk.Entry(form_frame)
        currency_entry.insert(0, currency)
        currency_entry.pack(pady=5, fill=tk.X)
        
        ttk.Label(form_frame, text="Price:").pack(pady=(10, 0), anchor=tk.W)
        price_entry = ttk.Entry(form_frame)
        price_entry.insert(0, current_price)
        price_entry.pack(pady=5, fill=tk.X)
        
        ttk.Label(form_frame, text="Depot Info:").pack(pady=(10, 0), anchor=tk.W)
        depot_entry = ttk.Entry(form_frame, width=50)
        depot_entry.insert(0, current_depot)
        depot_entry.pack(pady=5, fill=tk.X)

        def save_changes():
            try:
                # Değerleri al
                new_title = title_entry.get()
                new_variation = variation_entry.get()
                
                try:
                    new_quantity = int(quantity_entry.get())
                except ValueError:
                    new_quantity = 0
                    messagebox.showwarning("Input Warning", "Invalid quantity value. Setting to 0.")
                
                new_currency = currency_entry.get()
                
                try:
                    new_price = float(price_entry.get())
                except ValueError:
                    new_price = 0.0
                    messagebox.showwarning("Input Warning", "Invalid price value. Setting to 0.")
                
                new_depot = depot_entry.get()
                
                # Veritabanını güncelle
                conn = sqlite3.connect("database.db")
                cursor = conn.cursor()
                
                # Resim yolunu da güncelleyerek
                cursor.execute(
                    '''
                    UPDATE inventory
                    SET title = ?, variation_details = ?, available_quantity = ?, 
                        currency = ?, start_price = ?, depot_info = ?, image_path = ?
                    WHERE item_number = ?
                    ''',
                    (new_title, new_variation, new_quantity, new_currency, new_price, new_depot, current_image_path, item_number),
                )
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Item updated successfully.")
                edit_window.destroy()
                self.load_inventory()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update item: {e}")

        # Kaydet ve İptal düğmeleri
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=15)
        
        ttk.Button(button_frame, text="Save Changes", command=save_changes).grid(row=0, column=0, padx=10)
        ttk.Button(button_frame, text="Cancel", command=edit_window.destroy).grid(row=0, column=1, padx=10)

    def search(self):
        search_term = self.search_entry.get()
        if not search_term:
            messagebox.showwarning("Input Error", "Please enter a search term.")
            return
        try:
            # İkon sözlüğünü temizle
            self.tree_icons.clear()
            
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            # Item number, title ve variation_details alanlarında arama yap
            cursor.execute("""
                SELECT rowid as ID, item_number, title, variation_details, available_quantity, currency, start_price, depot_info, image_path 
                FROM inventory 
                WHERE item_number LIKE ? OR title LIKE ? OR variation_details LIKE ?
                ORDER BY CAST(item_number AS INTEGER) DESC
            """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                messagebox.showinfo("No Results", "No items found matching your search term.")
                return
                
            # TreeView'i temizle
            for row in self.tree.get_children():
                self.tree.delete(row)
                
            # Bulunan sonuçları göster
            for idx, result in enumerate(results):
                values = list(result)
                
                # Formatlamaları yap
                values[5] = str(values[5])  # Currency sütununu string'e dönüştür
                
                # start_price için güvenli dönüşüm
                try:
                    values[6] = f"{float(values[6]):.2f}"  # Start price sütununu formatla
                except ValueError:
                    values[6] = str(values[6])  # Dönüşüm başarısız olursa string olarak bırak
                
                # Resim varsa gerçek ikon oluştur, yoksa boş ikon
                image_path = values[8]  # image_path son sütunda
                item_number = values[1]  # item_number değerini al
                icon = None
                
                if image_path and os.path.exists(image_path):
                    # Thumbnail kullan
                    thumbnail_path = self.create_thumbnail(image_path, item_number)
                    
                    if thumbnail_path and os.path.exists(thumbnail_path):
                        try:
                            # Thumbnail'i yükle
                            img = Image.open(thumbnail_path)
                            img = self.fix_image_rotation(img)
                            img = img.resize((300, 300), Image.LANCZOS)
                            photo = ImageTk.PhotoImage(img)
                            
                            # İkonu sözlükte sakla
                            self.tree_icons[item_number] = photo
                            
                            print(f"Arama sonucu thumbnail kullanıldı: {item_number}")
                        except Exception as e:
                            print(f"Thumbnail yükleme hatası: {e}")
                            icon = self.no_image_icon
                    else:
                        icon = self.no_image_icon
                else:
                    icon = self.no_image_icon
                
                # İlk 8 değeri al (image_path hariç)
                item_values = values[:8]
                
                # Öğeyi TreeView'e ekle - item_number ile
                item_id = self.tree.insert("", "end", iid=str(item_number), image=icon, values=item_values)
                
            messagebox.showinfo("Search Results", f"Found {len(results)} matching items.")
            
        except Exception as e:
            messagebox.showerror("Search Error", str(e))
            print(f"Search error: {e}")

    def update_depot(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select an item to update depot info.")
            return
        item_id = int(self.tree.item(selected_item, "values")[0])
        depot_info = self.depot_entry.get()
        if not depot_info:
            messagebox.showwarning("Input Error", "Please enter depot information.")
            return
        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE inventory SET depot_info = ? WHERE rowid = ?", (depot_info, item_id)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Depot information updated successfully.")
            self.depot_entry.delete(0, tk.END)
            self.load_inventory()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update depot information: {e}")

    def remove_zero_quantity_items(self):
        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM inventory WHERE available_quantity = 0")
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Items with zero quantity removed successfully.")
            self.load_inventory()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove zero quantity items: {e}")

    def open_print_options(self, item_values):
        # Yeni bir pencere aç
        print_window = Toplevel(self.root)
        print_window.title("Print Options")

        Label(print_window, text="Select a printing option:").pack(pady=10)

        # 1. Seçenek: Ürün adedi kadar bas
        def print_quantity():
            quantity = int(item_values[4])  # Available quantity
            for _ in range(quantity):
                self.print_label(item_values)
            print_window.destroy()

        Button(print_window, text="Print Quantity", command=print_quantity).pack(pady=5)

        # 2. Seçenek: 1 adet bas
        def print_one():
            self.print_label(item_values)
            print_window.destroy()

        Button(print_window, text="Print One Label", command=print_one).pack(pady=5)

        # 3. Seçenek: Manuel giriş ile bas
        def manual_print():
            try:
                quantity = int(manual_entry.get())
                if 1 <= quantity <= 99:  # Maksimum 99 sınırı
                    for _ in range(quantity):
                        self.print_label(item_values)
                    print_window.destroy()
                else:
                    messagebox.showerror("Error", "Please enter a number between 1 and 99.")
            except ValueError:
                messagebox.showerror("Error", "Invalid input. Please enter a number.")

        Label(print_window, text="Enter manual quantity (1-99):").pack(pady=10)
        manual_entry = ttk.Entry(print_window)
        manual_entry.pack(pady=5)

        Button(print_window, text="Print Manual Quantity", command=manual_print).pack(pady=5)

    def print_label(self, item_values):
        # Etiket boyutu (40 mm x 15 mm)
        label_width = 113  # 40 mm
        label_height = 80  # 15 mm

        # Etiket verileri - Düzeltilmiş indeksler (Image sütunu artık values'ta değil)
        if len(item_values) >= 8:
            item_number = item_values[1]       # Item Number
            title = item_values[2]             # Title
            variation_details = item_values[3] # Variation Details
            available_quantity = item_values[4] # Available Quantity
            currency = item_values[5]          # Currency
            start_price = item_values[6]       # Start Price
            depot_info = item_values[7]        # Depot Info
        else:
            messagebox.showerror("Error", "Not enough data to print label")
            return

        # QR kod oluşturma
        qr = qrcode.QRCode(box_size=2, border=1)  # Küçük boyutlu QR kod
        qr.add_data(
            f"Item: {item_number}, Title: {title}, Variation: {variation_details}, Quantity: {available_quantity}, Price: {start_price} {currency}, Depot: {depot_info}")
        qr_img = qr.make_image(fill="black", back_color="white")
        qr_path = f"{item_number}_qr.png"
        qr_img.save(qr_path)

        # Etiket yazdırma
        output_file = f"{item_number}_label.pdf"
        c = canvas.Canvas(output_file, pagesize=(label_width, label_height))

        # 1D Barkod (Item Number)
        barcode = code128.Code128(item_number, barHeight=8, barWidth=0.6)  # Küçük boyutlu barkod
        barcode_width = barcode.width
        barcode_x = -12  # Barkodu sola hizala, soldan 5 birim boşluk
        barcode.drawOn(c, barcode_x, label_height - 9)  # Barkod pozisyonu
        c.setFont("Helvetica", 3)
        # Item Number (Barkodun tam altına ortalanmış)
        text_x_position = barcode_x + (barcode_width / 2) - (len(item_number) + len(depot_info) * 1 * 1)  # Ortala
        c.drawString(text_x_position, label_height - 12, f"{item_number} -- {depot_info}")

        # Title (Satırlara bölerek sığdır)
        y_position = label_height - 20
        c.setFont("Helvetica", 5)
        title_lines = []
        while len(title) > 20:  # Her satırda 20 karakter
            title_lines.append(title[:20])
            title = title[20:]
        title_lines.append(title)
        for line in title_lines:
            c.drawString(5, y_position, line)
            y_position -= 10

        # Variation Details
        if variation_details:
            c.drawString(5, y_position, variation_details)
            y_position -= 10

        # Price + Currency
        c.setFont("Helvetica", 6)
        c.drawString(15, y_position, f"{start_price} {currency}")

        # QR Kod (sağda yer alacak)
        c.drawImage(qr_path, label_width - 48, 3, width=45, height=45)

        c.save()

        os.remove(qr_path)  # QR kod geçici dosyasını sil
        print(f"Etiket oluşturuldu: {output_file}")

    def on_key_press(self, event):
        """Herhangi bir tuşa basıldığında çağrılır"""
        # TreeView'da bir öğe seçiliyse
        if self.tree.selection():
            self.center_selected_item(event)
    
    def on_arrow_key(self, event):
        """Yukarı/aşağı ok tuşları için çağrılır"""
        # TreeView'da bir öğe seçiliyse
        if self.tree.selection():
            self.center_selected_item(event)
    
    def on_page_key(self, event):
        """Page Up/Down tuşları için çağrılır"""
        # Kısa bir gecikme ile ortalama (sayfa kaydırma bittikten sonra)
        self.root.after(50, lambda: self.center_selected_item(event))
    
    def on_home_end_key(self, event):
        """Home/End tuşları için çağrılır"""
        # Kısa bir gecikme ile ortalama
        self.root.after(50, lambda: self.center_selected_item(event))
    
    def center_selected_item(self, event=None):
        """Seçili öğeyi TreeView'ın ortasına kaydırır"""
        # Seçili öğe yoksa bir şey yapma
        selection = self.tree.selection()
        if not selection:
            return
            
        # Seçili öğenin ID'sini al
        item_id = selection[0]
        
        try:
            # Öğeyi görüntüle
            self.tree.see(item_id)
            
            # Seçili öğenin y-koordinatını al (0-1 arasında bir değer olarak)
            bbox = self.tree.bbox(item_id)
            if not bbox:
                return
                
            # Görünür alanın yüksekliği
            tree_height = self.tree.winfo_height()
            
            # Öğeyi merkeze getirmek için kaydırma konumunu hesapla
            visible_rows = tree_height // 25  # 25 = satır yüksekliği
            middle_offset = visible_rows // 2
            
            # Seçili öğenin indeksini al
            items = self.tree.get_children()
            index = items.index(item_id)
            
            # Merkeze kaydır
            top_index = max(0, index - middle_offset)
            if top_index < len(items):
                self.tree.yview_moveto(top_index / len(items))
        except Exception as e:
            print(f"Center item error: {e}")

    def allowed_file(self, filename):
        """Dosyanın izin verilen bir uzantıya sahip olup olmadığını kontrol eder"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    def delete_selected_item(self):
        """Seçilen ürünü veritabanından siler"""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select an item to delete.")
            return
            
        item_values = self.tree.item(selected_item, "values")
        
        # Düzeltilmiş indeksler - Image sütunu artık values'ta değil
        try:
            item_id = int(item_values[0])    # ID (rowid)
            item_number = item_values[1]     # Item Number
            title = item_values[2]           # Title
        except (IndexError, ValueError) as e:
            messagebox.showerror("Error", f"Could not read item data: {e}")
            return
            
        # Ürünün görüntüsünü kontrol et - item_number ile sorgula
        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute("SELECT image_path FROM inventory WHERE item_number = ?", (item_number,))
            result = cursor.fetchone()
            image_path = result[0] if result and result[0] else None
            conn.close()
            
            has_image = image_path and os.path.exists(image_path)
        except Exception as e:
            print(f"Resim yolu alınırken hata: {e}")
            has_image = False
            image_path = None
            
        # Silme işlemini onaylatma
        msg = f"Bu ürünü silmek istediğinizden emin misiniz?\n\nÜrün No: {item_number}\nBaşlık: {title}"
        if has_image:
            msg += "\n\nNot: Bu ürüne ait bir resim de var."
            
        confirm = messagebox.askyesno("Confirm Delete", msg)
        if not confirm:
            return
            
        try:
            # Veritabanından sil - item_number ile sil (daha güvenilir)
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            
            # Ürünü sil
            cursor.execute("DELETE FROM inventory WHERE item_number = ?", (item_number,))
            conn.commit()
            conn.close()
            
            # Resmi de silmek ister misiniz?
            if has_image:
                delete_img = messagebox.askyesno("Delete Image", 
                                              "Do you also want to delete the product image file?")
                if delete_img:
                    try:
                        os.remove(image_path)
                        print(f"Resim silindi: {image_path}")
                    except Exception as e:
                        print(f"Resim silinirken hata: {e}")
            
            # TreeView'dan seçili öğeyi kaldır
            self.tree.delete(selected_item)
            
            # Toplam değeri güncelle
            self.calculate_total_value()
            
            messagebox.showinfo("Success", f"Item {item_number} has been deleted.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete item: {e}")
            print(f"Delete error: {e}")
            
        # Envanteri yenile
        self.load_inventory()

    def upload_image(self, item_number, image_label, current_image_path=None):
        """Resim yükleme fonksiyonu
        
        :param item_number: Ürün numarası
        :param image_label: Resmi göstermek için Label widget'ı
        :param current_image_path: Mevcut resim yolu (varsa)
        :return: Yeni resim yolu veya None (iptal edilirse)
        """
        # Resim seçme dialog'unu göster
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif"),
                ("All files", "*.*")
            ]
        )
        if not file_path:
            return None
            
        if not self.allowed_file(file_path):
            messagebox.showerror("Error", "Only PNG, JPG, JPEG and GIF files are allowed.")
            return None
                
        try:
            # Dosya uzantısını al
            file_extension = os.path.splitext(file_path)[1].lower()
            
            # Benzersiz dosya adı oluştur
            safe_filename = f"product_{item_number}_{str(uuid.uuid4())[:8]}{file_extension}"
            destination = os.path.join(self.upload_folder, safe_filename)
            
            # Klasörü kontrol et, yoksa oluştur
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            
            # Dosyayı kopyala
            copyfile(file_path, destination)
            
            # Thumbnail oluştur
            self.create_thumbnail(destination, item_number, force_recreate=True)
            
            # Resmi göster
            img = Image.open(destination)
            img = self.fix_image_rotation(img)
            img = img.resize((300, 300), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            image_label.config(image=photo, width=300, height=300, text="")
            image_label.image = photo  # Referans tutma
            
            messagebox.showinfo("Success", "Image uploaded successfully!")
            
            return destination
        except Exception as e:
            messagebox.showerror("Error", f"Failed to upload image: {e}")
            return None

    def fix_image_rotation(self, img):
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = img._getexif()
            if exif is not None:
                orientation = exif.get(orientation, None)
                if orientation == 3:
                    img = img.rotate(180, expand=True)
                elif orientation == 6:
                    img = img.rotate(270, expand=True)
                elif orientation == 8:
                    img = img.rotate(90, expand=True)
        except Exception as e:
            pass
        return img


if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryApp(root)
    root.mainloop()
