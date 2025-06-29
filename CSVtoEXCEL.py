import os
import pandas as pd
from tkinter import Tk
from tkinter.filedialog import askopenfilename
from pathlib import Path

# Tkinter'i görünmez bir pencereyle başlat
Tk().withdraw()

# 1. Kullanıcıdan dosya seçmesini isteyin
print("Lütfen işlenecek CSV dosyasını seçin:")
input_file_path = askopenfilename(
    title="CSV Dosyasını Seçin",
    filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
)

# Dosya seçilmezse çıkış yap
if not input_file_path:
    print("Hiçbir dosya seçilmedi. İşlem iptal edildi.")
    exit()

# Çıktı dosyasını İndirilenler klasörüne kaydet
output_file_path = os.path.join(str(Path.home() / "Downloads"), "cleaned_inventory.xlsx")

# 2. CSV dosyasını yükle
data = pd.read_csv(input_file_path)

# 3. Sadece gerekli sütunları sakla - id ve image_path sütunları da dahil edildi
columns_to_keep = ["id", "Item number", "Title", "Variation details", "Available quantity", "Currency", "Start price", "image_path"]

# CSV'de bu sütunlar yoksa boş sütunlar olarak ekle
for col in columns_to_keep:
    if col not in data.columns:
        data[col] = ""

data_filtered = data[columns_to_keep]

# 4. Varyasyonsuz ve varyasyonlu satırları ayır
no_variation_rows = data_filtered[data_filtered["Variation details"].isna()]
variation_rows = data_filtered[data_filtered["Variation details"].notna()]

# 5. Varyasyonlu satırlar için gereksiz olanları temizle
cleaned_variation_rows = []
for item_number, group in variation_rows.groupby("Item number"):
    if len(group) > 1:
        first_row = group.iloc[0]
        remaining_rows = group.iloc[1:]

        # Kontrol: İlk satırdaki miktar alt satırların toplamına eşit mi
        quantity_match = first_row["Available quantity"] == remaining_rows["Available quantity"].sum()

        # Eğer kontrol doğruysa, ilk satırı sil
        if quantity_match:
            group = remaining_rows  # İlk satırı silerek grubu güncelle

    # Temizlenmiş grup sonuçlarına ekle
    cleaned_variation_rows.append(group)

cleaned_variation_rows = pd.concat(cleaned_variation_rows)

# 6. Varyasyonsuz ve temizlenmiş varyasyonlu satırları birleştir
final_data = pd.concat([no_variation_rows, cleaned_variation_rows])

# 7. 'depot_info' başlıklı sütunu ekle (satırlar boş bırakılır)
final_data["depot_info"] = ""

# 8. Item number'ı büyükten küçüğe sırala ve text formatında yaz
final_data = final_data.sort_values(by="Item number", ascending=False)
final_data["Item number"] = final_data["Item number"].astype(str)

# 9. Start price sütununu 0.00 formatına getir
final_data["Start price"] = final_data["Start price"].map("{:.2f}".format)

# 10. Sonuçları kaydet
final_data.to_excel(output_file_path, index=False)
print(f"Temizlenmiş dosya şu konuma kaydedildi: {output_file_path}")
