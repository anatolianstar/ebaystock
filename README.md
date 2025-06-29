# 📦 Depostok - Envanter Yönetim Sistemi

Modern ve kullanıcı dostu web tabanlı envanter yönetim sistemi. Flask ile geliştirilmiş, QR kod desteği olan tam özellikli bir stok takip uygulaması.

## ✨ Özellikler

### 🌐 Web Arayüzü
- **Modern ve responsive tasarım**
- **Mobil uyumlu arayüz**
- **Kolay kullanım** - Sürükle-bırak destekli

### 📊 Envanter Yönetimi
- ✅ Ürün ekleme, düzenleme ve silme
- ✅ Detaylı ürün bilgileri (başlık, varyasyon, miktar, fiyat)
- ✅ Resim yükleme ve görüntüleme
- ✅ Stok durumu takibi
- ✅ Depo bilgileri yönetimi

### 🔍 Arama ve Filtreleme
- **Anlık arama** - Ürün başlığı ve detaylarında
- **Kategori filtreleme**
- **Stok durumuna göre filtreleme**

### 📱 QR Kod Sistemi
- **Otomatik QR kod oluşturma**
- **Ürün bilgilerini içeren QR kodlar**
- **Mobil erişim desteği**

### 📈 Raporlama
- **Excel aktarma** - Tüm envanter verilerini Excel'e aktarma
- **CSV desteği** - Veri içe/dışa aktarma
- **Tarihli raporlar**

### 🗄️ Veritabanı Desteği
- **SQLite** - Varsayılan, kurulum gerektirmez
- **MySQL** - İsteğe bağlı, gelişmiş kullanım için

## 🚀 Kurulum

### Gereksinimler
- Python 3.10+
- pip (Python paket yöneticisi)

### 1. Projeyi İndirin
```bash
git clone https://github.com/[kullanici-adi]/depostok.git
cd depostok
```

### 2. Sanal Ortam Oluşturun
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 4. Uygulamayı Başlatın
```bash
python app.py
```

Uygulama şu adreslerde erişilebilir:
- **Web Arayüzü:** http://localhost:5003
- **Mobil Erişim:** http://[ip-adresiniz]:5003

## 📱 Kullanım

### Ürün Ekleme
1. Ana sayfada **"Yeni Ürün Ekle"** butonuna tıklayın
2. Gerekli bilgileri doldurun:
   - Ürün numarası
   - Başlık
   - Varyasyon detayları
   - Miktar
   - Para birimi ve fiyat
   - Depo bilgileri
3. İsteğe bağlı resim yükleyin
4. **"Kaydet"** butonuna tıklayın

### Excel Aktarma
1. Ana sayfada **"Excel'e Aktar"** butonuna tıklayın
2. Dosya otomatik olarak indirilir
3. Tüm envanter verileri Excel formatında dışa aktarılır

### QR Kod Kullanımı
- Her ürün için otomatik QR kod oluşturulur
- QR kodu mobil cihazla taratarak ürün bilgilerine erişilebilir
- QR kod ürün URL'sini içerir

### Arama ve Filtreleme
- **Arama çubuğu:** Ürün başlığı ve detaylarında arama
- **Stok filtreleri:** Stokta var/yok durumuna göre filtreleme
- **Sıralama:** Tarih, isim, fiyat bazında sıralama

## 🔧 Yapılandırma

### MySQL Veritabanı (İsteğe Bağlı)
```python
# app.py dosyasında MySQL ayarları
MYSQL_HOST = 'localhost'
MYSQL_USER = 'kullanici_adi'
MYSQL_PASSWORD = 'sifre'
MYSQL_DB = 'envanter_db'
```

### Port Değişikliği
```python
# app.py dosyasında
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=False)
```

## 📦 Exe Dosyası Oluşturma

Projeyi tek bir exe dosyası haline getirmek için:

```bash
# Sanal ortamı aktifleştirin
venv\Scripts\activate

# Gerekli paketleri yükleyin
pip install PyInstaller

# Exe oluşturun
pyinstaller app.spec
```

Exe dosyası `dist/` klasöründe oluşturulur.

## 🗂️ Proje Yapısı

```
depostok/
│
├── app.py                 # Ana Flask uygulaması
├── requirements.txt       # Python bağımlılıkları
├── app.spec              # PyInstaller yapılandırması
│
├── templates/            # HTML şablonları
│   ├── index.html
│   ├── add_item.html
│   └── edit_item.html
│
├── static/               # Statik dosyalar
│   ├── uploads/          # Yüklenen resimler
│   ├── thumbnails/       # Küçük resimler
│   └── icons/            # İkonlar
│
├── fonts/                # Font dosyaları
└── database.db           # SQLite veritabanı
```

## 🛠️ Geliştirme

### Debug Modu
```bash
# app.py dosyasında debug=True yapın
app.run(host="0.0.0.0", port=5003, debug=True)
```

### Yeni Özellik Ekleme
1. `app.py` dosyasında route ekleyin
2. `templates/` klasöründe HTML şablonu oluşturun
3. Gerekiyorsa CSS/JS ekleyin

## 🐛 Sorun Giderme

### Yaygın Sorunlar

**Port zaten kullanımda:**
```bash
# Farklı port kullanın
python app.py --port 5004
```

**Veritabanı hatası:**
```bash
# Veritabanını sıfırlayın
rm database.db
python app.py
```

**Resim yükleme sorunu:**
```bash
# Yetkileri kontrol edin
chmod 755 static/uploads/
```

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 🤝 Katkıda Bulunma

1. Projeyi fork edin
2. Feature branch oluşturun (`git checkout -b yeni-ozellik`)
3. Değişikliklerinizi commit edin (`git commit -am 'Yeni özellik eklendi'`)
4. Branch'i push edin (`git push origin yeni-ozellik`)
5. Pull Request oluşturun

## 📞 İletişim

Sorularınız için [issues](../../issues) sayfasını kullanabilirsiniz.

---

**⭐ Bu projeyi beğendiyseniz yıldız vermeyi unutmayın!** 