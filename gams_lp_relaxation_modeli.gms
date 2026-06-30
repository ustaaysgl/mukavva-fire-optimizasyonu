* =============================================================
* KESIM PLANLAMA - LP MODELI
*
* Is akisi:
* Python -> aday desen havuzu ve veriler.inc
* GAMS LP -> kesirli uretim plani
* Python -> uretim adetlerini yuvarlama
* Python -> talep toleransi kontrolu
* Python -> gerekirse kucuk duzeltme
* Sonuc -> yuvarlanmis uretim plani ve fire orani
*
* Gerekli veriler.inc icerigi:
* d(i)   : i urununun talep adedi
* b(i)   : i urununun alani, m2/adet
* w(j)   : j deseninde kullanilan bobin eni, metre
* a(i,j) : j deseni 1 metre calisinca i urununden cikan adet
* =============================================================

$include veriler.inc

* =============================================================
* PARAMETRELER
* =============================================================

Scalar
    o        'Talep tolerans orani' / 0.10 /
    pozEsik 'Pozitif kabul esigi'  / 0.000001 /
;

* =============================================================
* KARAR DEGISKENLERI
* =============================================================

Variables
    Z 'Toplam fire alani'
;

Positive Variables
    y(j)   'j deseninin calisma uzunlugu, metre'
    x(i,j) 'j deseninden uretilen i urunu adedi, LP oldugu icin kesirli gelebilir'
;

* =============================================================
* DENKLEMLER
* =============================================================

Equations
    Amac
    Kapasite(i,j)
    TalepAlt(i)
    TalepUst(i)
;

* -------------------------------------------------------------
* AMAC FONKSIYONU
* Kullanilan bobin alani ile uretilen urun alani arasindaki
* fark minimize edilir. Bu fark toplam fire alanidir.
* -------------------------------------------------------------

Amac..
    Z =e=
        sum(j, w(j) * y(j))
        - sum((i,j), b(i) * x(i,j));

* -------------------------------------------------------------
* KAPASITE KISITI
* Bir desen y(j) metre calistirildiginda, o desenden uretilen
* urun adedi a(i,j) * y(j) kapasitesini asamaz.
* -------------------------------------------------------------

Kapasite(i,j)..
    x(i,j) =l= a(i,j) * y(j);

* -------------------------------------------------------------
* TALEP ALT SINIRI
* Her urun en az talebin %90'i kadar uretilmelidir.
* -------------------------------------------------------------

TalepAlt(i)..
    sum(j, x(i,j)) =g= d(i) * (1 - o);

* -------------------------------------------------------------
* TALEP UST SINIRI
* Her urun en fazla talebin %110'u kadar uretilmelidir.
* -------------------------------------------------------------

TalepUst(i)..
    sum(j, x(i,j)) =l= d(i) * (1 + o);

* =============================================================
* SOLVER AYARLARI
* =============================================================

* CPLEX lisans sinirina takildigi icin LP cozumunde HIGHS kullaniliyor.
option lp = highs;
option reslim = 3600;

Model KesimLP /all/;

Solve KesimLP using LP minimizing Z;

* =============================================================
* SONUC HESAPLARI
* =============================================================

Scalar
    kull_alan     'Toplam kullanilan bobin alani, m2'
    urun_alan     'Toplam uretilen urun alani, m2'
    fire_alan     'Toplam fire alani, m2'
    fire_oran     'Genel fire orani, yuzde'
    secilen_desen 'LP cozumunde pozitif metrajla secilen desen sayisi'
;

Parameter
    topUret(i)        'Urun bazli toplam LP uretim adedi'
    talepSapma(i)     'LP uretim miktari ile talep arasindaki fark'
    sapmaYuzde(i)     'Talebe gore sapma yuzdesi'
    altSinir(i)       'Talep alt siniri'
    ustSinir(i)       'Talep ust siniri'
    desenKullAlan(j)  'Desen bazli kullanilan bobin alani, m2'
    desenUrunAlan(j)  'Desen bazli uretilen urun alani, m2'
    desenFireAlan(j)  'Desen bazli fire alani, m2'
    desenFireOran(j)  'Desen bazli fire orani, yuzde'
;

* Urun bazli toplam LP uretim miktari
topUret(i) = sum(j, x.l(i,j));

* Talep sapmalari
talepSapma(i) = topUret(i) - d(i);

sapmaYuzde(i) = 0;
sapmaYuzde(i)$(d(i) > 0) = talepSapma(i) / d(i) * 100;

* Talep tolerans sinirlari
altSinir(i) = d(i) * (1 - o);
ustSinir(i) = d(i) * (1 + o);

* Desen bazli alan hesaplari
desenKullAlan(j) = w(j) * y.l(j);
desenUrunAlan(j) = sum(i, b(i) * x.l(i,j));
desenFireAlan(j) = desenKullAlan(j) - desenUrunAlan(j);

desenFireOran(j) = 0;
desenFireOran(j)$(desenKullAlan(j) > 0) =
    desenFireAlan(j) / desenKullAlan(j) * 100;

* Genel alan hesaplari
kull_alan = sum(j$(y.l(j) > pozEsik), w(j) * y.l(j));
urun_alan = sum((i,j), b(i) * x.l(i,j));
fire_alan = kull_alan - urun_alan;

fire_oran = 0;
fire_oran$(kull_alan > 0) = fire_alan / kull_alan * 100;

secilen_desen = sum(j$(y.l(j) > pozEsik), 1);

* =============================================================
* GAMS EKRAN / LST CIKTILARI
* =============================================================

Display KesimLP.modelstat;
Display KesimLP.solvestat;
Display KesimLP.objval;

Display kull_alan;
Display urun_alan;
Display fire_alan;
Display fire_oran;
Display secilen_desen;

* Hangi desen kac metre calisiyor?
Display y.l;

* Hangi urun hangi desenden kac adet uretiliyor?
* LP oldugu icin x.l degerleri kesirli gelebilir.
Display x.l;

* Urun bazli talep, uretim ve tolerans kontrolu
Display d;
Display altSinir;
Display ustSinir;
Display topUret;
Display talepSapma;
Display sapmaYuzde;

* Desen bazli fire degerleri
Display desenKullAlan;
Display desenUrunAlan;
Display desenFireAlan;
Display desenFireOran;