import pandas as pd
from itertools import combinations, product
from pathlib import Path

# ============================================================
# SIPARIS EXCEL -> GAMS veriler.inc URETICI
# ============================================================
# Bu kod:
# 1) Excel dosyasını okur
# 2) Varsayılan olarak Siparis_Dokumu.xlsx dosyasını ve sip_dok sayfasını kullanır
# 3) Excel'deki tüm siparişleri alır
# 4) Aynı Boy-En ölçüsüne sahip siparişleri birleştirir
# 5) Bobin eninin en fazla %3.5'i kadar en firesine izin veren aday desenleri üretir
# 6) GAMS modelinin kullanacağı veriler.inc dosyasını oluşturur
#
# Beklenen Excel sütunları:
# Boy
# En
# Sipariş Miktarı
#
# Üretilen veriler.inc 1 METRE bazlıdır:
# d(i)   = talep adedi
# b(i)   = ürün alanı, m2/adet
# w(j)   = bobin eni, metre
# a(i,j) = j deseni 1 metre çalışınca i ürününden çıkan adet
# ============================================================

DEFAULT_EXCEL_FILE = "Siparis_Dokumu.xlsx"
DEFAULT_SHEET_NAME = "sip_dok"

OUTPUT_INC = "veriler.inc"
OUTPUT_URUN_LISTESI = "urun_listesi.xlsx"
OUTPUT_DESEN_KONTROL = "desen_havuzu_kontrol.xlsx"

BOBINLER_MM = [2400, 2450, 2500, 2650, 2800]
MAX_SERIT = 8
MAX_FARKLI_URUN = 2

# Eski 80 mm sabit sınır kaldırıldı.
# Yeni kural: en firesi / bobin eni <= %3.5
MAX_FIRE_ORANI = 0.035

# Firmanın sipariş dökümü dosyasındaki sütun adları
BOY_COL = "Boy"
EN_COL = "En"
TALEP_COL = "Sipariş Miktarı"


def kullanicidan_excel_adi_al():
    print("\nExcel dosya adı örnekleri:")
    print("  - Siparis_Dokumu.xlsx")
    print("  - siparisler.xlsx")

    excel_adi = input(f"\nExcel dosya adını girin [{DEFAULT_EXCEL_FILE}]: ").strip()

    if excel_adi == "":
        excel_adi = DEFAULT_EXCEL_FILE

    excel_path = Path(excel_adi)

    if not excel_path.exists():
        raise FileNotFoundError(
            f"\nExcel dosyası bulunamadı: {excel_path}\n"
            f"Python dosyası ile Excel dosyasının aynı klasörde olduğundan emin olun."
        )

    return excel_path


def sheet_sec(excel_path):
    xls = pd.ExcelFile(excel_path)

    print("\nExcel içindeki sayfalar:")
    for no, sheet in enumerate(xls.sheet_names, start=1):
        print(f"{no}. {sheet}")

    secim = input(f"\nSayfa adını veya numarasını girin [{DEFAULT_SHEET_NAME}]: ").strip()

    if secim == "":
        if DEFAULT_SHEET_NAME in xls.sheet_names:
            secilen_sheet = DEFAULT_SHEET_NAME
        else:
            print(
                f"\nUyarı: Varsayılan sayfa '{DEFAULT_SHEET_NAME}' bulunamadı. "
                f"İlk sayfa seçildi: {xls.sheet_names[0]}"
            )
            secilen_sheet = xls.sheet_names[0]

    elif secim.isdigit():
        secim_no = int(secim)
        if secim_no < 1 or secim_no > len(xls.sheet_names):
            raise ValueError("Geçersiz sayfa numarası.")
        secilen_sheet = xls.sheet_names[secim_no - 1]

    else:
        secilen_sheet = secim

    if secilen_sheet not in xls.sheet_names:
        raise ValueError(f"'{secilen_sheet}' isimli sayfa bulunamadı.")

    return secilen_sheet


def siparisleri_oku(excel_path, sheet_name):
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    df.columns = df.columns.astype(str).str.strip()

    gerekli_sutunlar = [BOY_COL, EN_COL, TALEP_COL]

    for col in gerekli_sutunlar:
        if col not in df.columns:
            raise ValueError(
                f"\nExcel içinde '{col}' sütunu bulunamadı.\n"
                f"Mevcut sütunlar: {list(df.columns)}\n\n"
                f"Beklenen sütunlar: {gerekli_sutunlar}"
            )

    df = df.dropna(subset=gerekli_sutunlar).copy()

    df[BOY_COL] = pd.to_numeric(df[BOY_COL], errors="coerce")
    df[EN_COL] = pd.to_numeric(df[EN_COL], errors="coerce")
    df[TALEP_COL] = pd.to_numeric(df[TALEP_COL], errors="coerce")

    df = df.dropna(subset=gerekli_sutunlar).copy()

    df[BOY_COL] = df[BOY_COL].astype(int)
    df[EN_COL] = df[EN_COL].astype(int)
    df[TALEP_COL] = df[TALEP_COL].astype(int)

    if len(df) == 0:
        raise ValueError("Excel'de okunabilir sipariş satırı bulunamadı.")

    urunler = (
        df.groupby([BOY_COL, EN_COL], as_index=False)
        .agg(talep_adet=(TALEP_COL, "sum"))
        .reset_index(drop=True)
    )

    urunler.insert(0, "id", [f"L{i + 1}" for i in range(len(urunler))])

    urunler = urunler.rename(
        columns={
            BOY_COL: "boy_mm",
            EN_COL: "en_mm",
        }
    )

    urunler["alan_m2"] = (urunler["boy_mm"] / 1000) * (urunler["en_mm"] / 1000)

    print("\nExcel'den okunan toplam sipariş satırı:", len(df))
    print("Aynı Boy-En ölçüleri birleştirildikten sonra ürün tipi sayısı:", len(urunler))

    urunler.to_excel(OUTPUT_URUN_LISTESI, index=False)

    print("\nÜrün listesi oluşturuldu:", OUTPUT_URUN_LISTESI)
    print("\nÜrünler:")
    print(urunler[["id", "boy_mm", "en_mm", "talep_adet"]].to_string(index=False))

    return urunler


def desen_havuzu_uret(urunler):
    urun_listesi = urunler.to_dict("records")
    desenler = []
    desen_no = 1

    for k in range(1, MAX_FARKLI_URUN + 1):
        for secilen_idxler in combinations(range(len(urun_listesi)), k):
            secilen_urunler = [urun_listesi[idx] for idx in secilen_idxler]
            serit_araliklari = []

            for urun in secilen_urunler:
                max_serit = max(BOBINLER_MM) // urun["en_mm"]
                max_serit = min(max_serit, MAX_SERIT)

                if max_serit < 1:
                    serit_araliklari.append(range(0))
                else:
                    serit_araliklari.append(range(1, max_serit + 1))

            if any(len(aralik) == 0 for aralik in serit_araliklari):
                continue

            for serit_adetleri in product(*serit_araliklari):
                toplam_serit = sum(serit_adetleri)

                if toplam_serit > MAX_SERIT:
                    continue

                kullanilan_en_mm = sum(
                    serit * urun["en_mm"]
                    for serit, urun in zip(serit_adetleri, secilen_urunler)
                )

                for bobin_mm in BOBINLER_MM:
                    if kullanilan_en_mm > bobin_mm:
                        continue

                    fire_mm = bobin_mm - kullanilan_en_mm
                    fire_orani = fire_mm / bobin_mm

                    # Yeni kural:
                    # En firesi, seçilen bobin eninin en fazla %3.5'i olabilir.
                    if fire_orani > MAX_FIRE_ORANI:
                        continue

                    desen = {
                        "desen_id": f"P{desen_no}",
                        "bobin_mm": bobin_mm,
                        "bobin_m": bobin_mm / 1000,
                        "kullanilan_en_mm": kullanilan_en_mm,
                        "fire_mm": fire_mm,
                        "fire_orani": fire_orani,
                        "fire_orani_yuzde": fire_orani * 100,
                        "toplam_serit": toplam_serit,
                        "farkli_urun_sayisi": k,
                    }

                    for urun in urun_listesi:
                        uid = urun["id"]
                        desen[f"s_{uid}"] = 0
                        desen[f"a_{uid}"] = 0.0

                    for idx, serit_sayisi in zip(secilen_idxler, serit_adetleri):
                        urun = urun_listesi[idx]
                        uid = urun["id"]

                        desen[f"s_{uid}"] = serit_sayisi
                        desen[f"a_{uid}"] = serit_sayisi * (1000 / urun["boy_mm"])

                    desenler.append(desen)
                    desen_no += 1

    if not desenler:
        raise ValueError(
            "\nUygun aday desen bulunamadı.\n"
            "%3.5 en firesi oranı sınırı çok dar olabilir veya ürün enleri bobinlerle uyumsuz olabilir."
        )

    desenler_df = pd.DataFrame(desenler)

    for _, urun in urunler.iterrows():
        uid = urun["id"]
        aktif_desen_sayisi = (desenler_df[f"a_{uid}"] > 0).sum()

        if aktif_desen_sayisi == 0:
            raise ValueError(
                f"\n{uid} ürünü için hiçbir uygun desen bulunamadı.\n"
                f"Ürün ölçüsü: boy={urun['boy_mm']} mm, en={urun['en_mm']} mm\n"
                f"Bu ürün %3.5 en firesi oranı sınırı altında hiçbir bobinle uygun desen oluşturmuyor olabilir."
            )

    desenler_df.to_excel(OUTPUT_DESEN_KONTROL, index=False)

    print("\nAday desen sayısı:", len(desenler_df))
    print("Maksimum fire_mm:", desenler_df["fire_mm"].max())
    print("Maksimum fire oranı (%):", desenler_df["fire_orani_yuzde"].max())
    print("Desen kontrol dosyası oluşturuldu:", OUTPUT_DESEN_KONTROL)

    return desenler_df


def gams_liste_yaz(f, elemanlar, satir_basina=10):
    for i in range(0, len(elemanlar), satir_basina):
        f.write(", ".join(elemanlar[i:i + satir_basina]))
        f.write("\n")


def veriler_inc_yaz(urunler, desenler):
    urun_idleri = urunler["id"].tolist()
    desen_idleri = desenler["desen_id"].tolist()

    with open(OUTPUT_INC, "w", encoding="utf-8") as f:
        f.write("Set i 'Siparis urun kumesi' /\n")
        gams_liste_yaz(f, urun_idleri)
        f.write("/;\n\n")

        f.write("Set j 'Aday desen kumesi' /\n")
        gams_liste_yaz(f, desen_idleri)
        f.write("/;\n\n")

        f.write("Parameter d(i) 'Her urunun talep miktari (adet)' /\n")
        for _, row in urunler.iterrows():
            f.write(f"    {row['id']}  {int(row['talep_adet'])}\n")
        f.write("/;\n\n")

        f.write("Parameter b(i) 'Urun alani (m2 per adet)' /\n")
        for _, row in urunler.iterrows():
            f.write(f"    {row['id']}  {row['alan_m2']:.8f}\n")
        f.write("/;\n\n")

        f.write("Parameter w(j) 'Bobin eni (m)' /\n")
        for _, row in desenler.iterrows():
            f.write(f"    {row['desen_id']}  {row['bobin_m']:.4f}\n")
        f.write("/;\n\n")

        f.write("Parameter a(i,j) '1 metre calisinca i urununden uretilen adet' /\n")
        for _, desen in desenler.iterrows():
            j = desen["desen_id"]

            for _, urun in urunler.iterrows():
                i = urun["id"]
                a_degeri = float(desen[f"a_{i}"])

                if a_degeri > 0:
                    f.write(f"    {i}.{j}  {a_degeri:.8f}\n")

        f.write("/;\n")

    print("\nGAMS veriler dosyası oluşturuldu:", OUTPUT_INC)


def main():
    excel_path = kullanicidan_excel_adi_al()
    sheet_name = sheet_sec(excel_path)

    print("\nOkunan Excel:", excel_path)
    print("Okunan sayfa:", sheet_name)

    urunler = siparisleri_oku(excel_path, sheet_name)
    desenler = desen_havuzu_uret(urunler)
    veriler_inc_yaz(urunler, desenler)

    print("\nTAMAMLANDI.")
    print("GAMS'te kullanacağın dosya:", OUTPUT_INC)
    print("Bu dosya 1 metre bazlıdır.")
    print("GAMS üretim kısıtı şu olmalı:")
    print("    x(i,j) =l= a(i,j) * y(j);")
    print("Eski /100 içeren üretim kısıtını bu verilerle kullanma.")


if __name__ == "__main__":
    main()