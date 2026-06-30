# Mukavva Ambalaj Üretiminde Kesim Süreçlerinin İncelenmesi ve Fire Optimizasyonu

Bu repository, bitirme projesi kapsamında geliştirilen kesim planlama ve fire optimizasyonu modeline ait kod dosyalarını içermektedir.

## Proje Amacı

Bu çalışmanın amacı, oluklu mukavva ambalaj üretiminde farklı en, boy ve talep miktarlarına sahip müşteri siparişlerini uygun kesim desenleriyle karşılayarak toplam fire alanını azaltmaktır.

## Kullanılan Yöntem

Çalışmada iki aşamalı bir yapı kullanılmıştır:

1. Python ile sipariş verileri işlenmiş ve üretim kısıtlarına uygun aday kesim desenleri oluşturulmuştur.
2. Oluşturulan aday desenler GAMS ortamına aktarılmış ve LP relaxation modeli ile değerlendirilmiştir.

## Dosyalar

- `siparis_excelinden_veriler_inc_uret.py`: Excel sipariş verilerinden GAMS için gerekli veri dosyasını oluşturan Python kodu
- `veriler.inc`: GAMS modelinde kullanılan veri dosyası
- `gams_lp_relaxation_modeli.gms`: LP relaxation optimizasyon modelini içeren GAMS dosyası

## Proje Ekibi

- Ayşegül Usta
- Dilay Görür
- Zeynep Erken

Danışman: Prof. Dr. Yusuf Sait Türkan
