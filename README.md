# TRY Piyasa Takip Projesi

USD/TRY, EUR/TRY, gram altın, gram gümüş, Brent petrol ve (opsiyonel) TCMB TL
mevduat ortalama faiz oranını günlük olarak çeken, yerel bir CSV'de biriktiren
ve tarayıcıda açılabilen bir trend dashboard'u üreten basit bir Python
projesi.

## Klasör yapısı

```
try-tracker/
  fetch_data.py         -> Veriyi ceker, data/prices.csv'ye ekler (append)
  generate_dashboard.py -> data/prices.csv'yi okuyup dashboard.html uretir
  config.py               -> Kisisel ayarlar (TCMB EVDS API anahtari) - PAYLASMAYIN
  config.example.py      -> config.py icin sablon (repoya eklenir, anahtar icermez)
  run_daily.bat          -> Ikisini sirayla calistiran toplu is dosyasi (Gorev Zamanlayici bunu cagirir)
  requirements.txt       -> Python bagimliliklari
  data/
    prices.csv            -> Biriken tarihsel veri (tarih damgali)
  dashboard.html          -> Uretilen, cift tiklanip acilabilen HTML sayfasi
  index.html              -> GitHub Pages icin dashboard.html'e yonlendiren kok sayfa
  fetch_log.txt           -> fetch_data.py calisma gecmisi/hatalari (repoya eklenmez)
  run_daily.log           -> run_daily.bat calisma gecmisi (repoya eklenmez)
  .github/workflows/
    update-dashboard.yml  -> Her 5 dakikada bir veriyi ceken/yayinlayan GitHub Actions workflow'u
```

## Veri kaynakları

| Veri | Kaynak | Key gerekli mi? | Not |
|---|---|---|---|
| USD/TRY, EUR/TRY | [frankfurter.app](https://www.frankfurter.app) | Hayır | Avrupa Merkez Bankası referans kurları. Erişilemezse otomatik olarak `open.er-api.com` yedek kaynağına geçilir. |
| Gram altın / gram gümüş | [gold-api.com](https://gold-api.com) | Hayır | XAU/XAG için USD/ons spot fiyat döner. `gram_fiyatı_TRY = (ons_fiyatı_USD / 31.1034768) * USD/TRY` formülüyle grama ve TL'ye çevrilir. |
| Brent petrol (USD/varil, TRY/varil) | Yahoo Finance chart API (sembol `BZ=F`) | Hayır | **Resmi olmayan (unofficial) bir endpoint** — Yahoo'nun herkese açık ama desteklenmeyen bir servisi. Ücretsiz ve pratikte güvenilir çalışıyor, ama önceden haber vermeden değişebilir/kısıtlanabilir. Başarısız olursa script durmaz, o günün Brent alanı boş bırakılır. |
| TL Mevduat Faizi (1 aya kadar vadeli, ort.) | [TCMB EVDS](https://evds3.tcmb.gov.tr) (seri `TP.TRY.MT01`) | **Evet (ücretsiz)** | Resmi kaynak — "Mevduat Bankaları"nın 1 aya kadar vadeli TL mevduata uyguladığı ağırlıklı ortalama faiz oranı, haftalık (Cuma) güncellenir. Kayıt ücretsiz (kredi kartı istenmez). Canlı olarak test edildi ve doğrulandı. Anahtar girilmezse bu alan otomatik olarak boş bırakılır, script hata vermez. |

**Not:** gold-api.com ve Yahoo Finance uluslararası spot/vadeli fiyatları
verir; Türkiye'deki kuyumcu alış-satış fiyatlarından veya akaryakıt
pompa fiyatlarından (işçilik/kâr marjı, ÖTV/KDV gibi vergiler nedeniyle)
farklılık gösterebilir. Bunları bir referans/spot takip aracı olarak
düşünün, alım-satım kararı için tek başına kullanmayın.

## TCMB EVDS kurulumu (mevduat faiz oranı için, opsiyonel)

Bu adımı atlarsanız proje yine sorunsuz çalışır; sadece "TL Mevduat Faizi"
alanı dashboard'da boş görünür. **Bu proje için zaten kurulup gerçek bir
anahtarla canlı test edildi** — aşağıdaki adımlar, aynısını başka bir
makinede/hesapta tekrarlamak isterseniz içindir.

1. [evds3.tcmb.gov.tr](https://evds3.tcmb.gov.tr) adresine gidin, sağ üstten
   **Kayıt Ol** ile ücretsiz bir hesap açın (yalnızca e-posta ile kayıt +
   onay, ödeme istenmez).
2. Giriş yaptıktan sonra **Benim Sayfam > Profilim** sayfasından **API Key
   Kopyala** ile anahtarınızı alın.
3. Bu anahtarı `try-tracker\config.py` dosyasındaki `EVDS_API_KEY = ""`
   satırına tırnak içine yapıştırın.
4. `python fetch_data.py` çalıştırın; `data\prices.csv` dosyasının en son
   satırındaki `mevduat_faiz_pct` sütununa makul bir yüzde değeri
   (ör. `46.25`) düşer.

**Teknik detay (Ağustos 2026 itibarıyla):** TCMB, EVDS'i eski
`evds2.tcmb.gov.tr` adresinden yeni `evds3.tcmb.gov.tr` sistemine taşımış;
eski `/service/evds/` adresi artık çalışmıyor (siteye yönlendiriyor).
`fetch_data.py` güncel/doğrulanmış endpoint'i kullanıyor:
`https://evds3.tcmb.gov.tr/igmevdsms-dis/series=...&startDate=...&type=json`
(parametreler `?` olmadan doğrudan adrese eklenir — EVDS'e özgü bir kural)
ve `key`'i URL yerine HTTP header olarak gönderiyor (Nisan 2024'ten beri
zorunlu). Varsayılan seri `TP.TRY.MT01` — "1 Aya Kadar Vadeli (TL Mevduat,
Akım, %)", kaynağı Mevduat Bankaları, haftalık (Cuma) güncellenir; gerçek
anahtarla test edilip doğrulandı.

**Farklı bir vade isterseniz** (ör. 3 ay, 6 ay, 1 yıl): [evds3.tcmb.gov.tr/tumSeriler](https://evds3.tcmb.gov.tr/tumSeriler)
sayfasında "mevduat faiz" ile arama yapıp istediğiniz vadenin seri kodunu
bulun (`TP.TRY.MT02`, `MT03`... gibi devam ediyor olabilir — sırası
değişebileceğinden aramadan teyit edin), `config.py` içindeki
`EVDS_SERIES` değişkenine yazın, `fetch_data.py`'yi tekrar çalıştırıp
`fetch_log.txt`'te "Mevduat faiz orani ... kaynagindan alindi" satırını
görün.

## Kurulum

1. Python 3.9+ kurulu olmalı (bu makinede 3.12 test edildi).
2. Bağımlılıkları kurun:

```bash
pip install -r requirements.txt
```

> **Kurumsal ağ / SSL sertifika hatası alırsanız:** Bu makinede test
> sırasında `requests` kütüphanesi "certificate verify failed" hatası verdi
> çünkü şirket ağı SSL trafiğini kendi kök sertifikasıyla inceliyor ve bu
> sertifika Python'un kendi CA paketinde (certifi) yok. Çözüm olarak
> `truststore` paketi eklendi — bu paket Windows'un kendi sertifika deposunu
> kullanır (tarayıcı/PowerShell gibi) ve script'in başında otomatik devreye
> girer. `requirements.txt` içinde zaten var; ayrıca bir şey yapmanıza
> gerek yok.

## Manuel çalıştırma

```bash
python fetch_data.py
python generate_dashboard.py
```

`dashboard.html` dosyasına çift tıklayarak tarayıcıda açabilirsiniz. Veri
CSV'den HTML içine gömülü şekilde üretildiği için internete veya bir sunucuya
ihtiyaç duymaz (dosya `file://` ile doğrudan açılabilir). Sayfa üstteki tarih
aralığı filtreleri (7 gün / 30 gün / 90 gün / 6 ay / tümü), her grafikte
gezinerek (hover) tarih+değer gösteren bir tooltip, üstte KPI kutuları, ve alt
kısımda ham veriyi gösteren bir tablo görünümü içerir. Sağ üstteki "Tema"
butonuyla açık/koyu temayı değiştirebilirsiniz.

Her ikisini birden çalıştırmak isterseniz `run_daily.bat` dosyasına çift
tıklamanız yeterli (aynı zamanda Görev Zamanlayıcısı'nın kullanacağı dosya
budur).

## GitHub Pages ile yayınlama

Bu repo GitHub Pages üzerinde barındırılıyor; kök dizindeki `index.html`
otomatik olarak `dashboard.html`'e yönlendirir. `main` dalına her push
GitHub Pages'i otomatik olarak yeniden derler (Settings > Pages ayarında
"Deploy from a branch: main / (root)").

`config.py` (TCMB EVDS API anahtarınızı içerir) `.gitignore` ile hariç
tutulmuştur ve depoya yüklenmez. Başka bir makinede kurarken
`config.example.py` dosyasını `config.py` olarak kopyalayıp kendi
anahtarınızı girin.

## GitHub Actions ile otomatik güncelleme (her 5 dakikada bir)

`.github/workflows/update-dashboard.yml` GitHub'ın kendi sunucularında
(sizin bilgisayarınız kapalı/uykuda olsa bile) her ~5 dakikada bir
çalışır: `fetch_data.py` ile veri çeker, `generate_dashboard.py` ile
`dashboard.html`'i yeniden üretir, değişiklik varsa otomatik commit +
push yapar. Push, GitHub Pages'in otomatik yeniden derlenmesini tetikler,
yani site sürekli güncel kalır.

Notlar:

- **`*/5 * * * *`** GitHub'ın izin verdiği en kısa aralıktır; yoğun
  dönemlerde birkaç dakika gecikme olabilir, garanti bir SLA değildir.
- **TL Mevduat Faizi (TCMB EVDS)** alanının Actions'ta da çalışması için
  isteğe bağlı olarak bir repository secret eklemeniz gerekir: **Settings
  > Secrets and variables > Actions > New repository secret**, isim
  `EVDS_API_KEY`, değer kendi TCMB EVDS anahtarınız. Eklenmezse script
  hata vermez, sadece bu alan Actions çalıştırmalarında boş kalır.
- Workflow her çalıştığında `data/prices.csv`'ye bir satır eklendiği için
  CSV zamanla hızla büyür (günde ~288 satıra kadar); bu normaldir ama
  isterseniz cron aralığını (`*/5 * * * *` → örn. `0 * * * *` = saatte bir)
  gevşeterek büyümeyi yavaşlatabilirsiniz.
- **Yerel `run_daily.bat` / Task Scheduler'ı da aynı anda kullanıyorsanız**
  iki taraf da aynı dosyalara push yapmaya çalışabilir; push etmeden önce
  `git pull --rebase origin main` çalıştırmadan push ederseniz "rejected
  (fetch first)" hatası alabilirsiniz. En basit kurulum: veri çekmeyi
  sadece GitHub Actions'a bırakıp yerel zamanlayıcıyı kapatmaktır.

## Windows Görev Zamanlayıcısı (Task Scheduler) ile günde bir kez otomatik çalıştırma

Aşağıdaki adımlar `run_daily.bat` dosyasını her gün otomatik çalıştıracak
bir görev oluşturur (script hem veriyi çeker hem dashboard'u günceller).

1. **Başlat** menüsüne `Görev Zamanlayıcısı` (Task Scheduler) yazıp açın.
2. Sağdaki **İşlemler (Actions)** panelinden **Temel Görev Oluştur...**
   (*Create Basic Task...*) seçeneğine tıklayın.
3. **Ad (Name):** `TRY Piyasa Takip` gibi bir isim verin, **İleri**'ye
   tıklayın.
4. **Tetikleyici (Trigger):** `Günlük` (*Daily*) seçin, **İleri**.
5. **Başlangıç tarihi/saati:** Verinin çekilmesini istediğiniz saati seçin
   (örn. her sabah 09:00) ve **"Her" (Recur every): 1 gün** olarak bırakın,
   **İleri**.
6. **İşlem (Action):** `Bir programı başlat` (*Start a program*) seçin,
   **İleri**.
7. **Program/script** alanına şu yolu yazın (tam yol — tırnak içinde):

   ```
   "C:\Users\sd014539\Desktop\Claude\try-tracker\run_daily.bat"
   ```

   **Bağımsız değişkenleri ekle (Add arguments)** ve **Başlangıç yeri
   (Start in)** alanlarını **boş bırakın** — `.bat` dosyası kendi konumunu
   zaten otomatik buluyor.
8. **İleri**, ardından özet ekranında **"Bitirmeden önce bu görevin
   özelliklerini aç" (Open the properties dialog...)** kutucuğunu
   işaretleyip **Son (Finish)**'a tıklayın. Özellikler penceresi açılacak:
   - **Genel (General)** sekmesinde: *"Kullanıcı oturum açmış olsun ya da
     olmasın çalıştır"* (**Run whether user is logged on or not**)
     seçeneğini işaretlerseniz bilgisayar açıkken siz oturum açmamış olsanız
     bile çalışır (Windows parolanızı bir kere sorar). Daha basit tutmak
     isterseniz varsayılan olan *"Yalnızca kullanıcı oturum açtığında çalış"*
     (**Run only when user is logged on**) seçeneğini bırakabilirsiniz —
     bu durumda görev yalnızca siz o an oturum açmışsanız tetiklenir.
   - **Koşullar (Conditions)** sekmesinde, dizüstü bilgisayar kullanıyorsanız
     *"Yalnızca bilgisayar AC gücüyle çalışıyorsa görevi başlat"* kutusunun
     işaretini kaldırmanız önerilir (aksi halde pil ile çalışırken görev
     atlanabilir).
   - **Ayarlar (Settings)** sekmesinde *"Görev başarısız olursa yeniden
     başlat"* (**If the task fails, restart every: ...**) seçeneğini
     `1 saat`, `3 kez` gibi ayarlamak, geçici bir internet kesintisinde
     günün verisinin kaçırılmamasını sağlar (opsiyonel ama önerilir).
   - **Tamam**'a basıp kapatın.

9. Görevi hemen test etmek için Görev Zamanlayıcısı'nın orta panelindeki
   görev listesinden `TRY Piyasa Takip` görevine sağ tıklayıp **Çalıştır**
   (*Run*) deyin. Ardından `try-tracker` klasöründeki `run_daily.log`
   dosyasını açıp `Tamamlandi` satırını, `data\prices.csv` dosyasında yeni
   bir satır eklendiğini ve `dashboard.html`'in güncellendiğini kontrol
   edin (dosyanın "Son değiştirilme" zamanına bakabilirsiniz).

### Sorun giderme

- **Görev "0x1" gibi bir hata koduyla bitiyor / hiçbir şey olmuyor:**
  `run_daily.log` dosyasını kontrol edin. Genelde sebep, Görev
  Zamanlayıcısı'nın `python` komutunu bulamamasıdır (Windows Store
  üzerinden kurulu Python'larda PATH bazen görev bağlamında farklı
  çözümlenir). Çözüm: `run_daily.bat` içindeki iki `python ...` satırını,
  PowerShell'de `(Get-Command python).Source` komutuyla bulacağınız tam
  yolla değiştirin, örn.:
  ```bat
  "C:\Users\sd014539\AppData\Local\Microsoft\WindowsApps\python.exe" fetch_data.py >> run_daily.log 2>&1
  ```
- **Dashboard açılıyor ama grafik boş / "veri yok" diyor:** `data/prices.csv`
  dosyasının en az 2 satır (2 farklı gün) içerdiğinden emin olun; script ilk
  çalıştığında tek satır olacağı için trend çizgisi henüz çizilemez, bu
  normaldir.
- **SSL / "certificate verify failed" hatası:** Yukarıdaki *Kurulum*
  bölümüne bakın — `truststore` paketinin kurulu olduğundan emin olun.

## Notlar

- CSV her çalıştırmada yalnızca **eklenir** (append) — geçmiş satırlar asla
  silinmez veya üzerine yazılmaz, bu yüzden zamanla büyür (günde 1 satır ~
  yılda 365 satır, önemsiz boyut).
- `dashboard.html` her `generate_dashboard.py` çalıştığında **tamamen
  yeniden üretilir** (üzerine yazılır); elle düzenleme yapmayın, kaybolur.
- Varsayılan görünüm son 6 aylık veriyi gösterir; üstteki filtre
  butonlarından 7/30/90 gün veya tüm geçmişe geçebilirsiniz.
- Brent petrol ve TL mevduat faizi **opsiyonel** alanlardır: kaynak o gün
  erişilemezse (Yahoo) veya anahtar girilmemişse (TCMB EVDS) script
  durmaz, sadece o sütun o satırda boş kalır; dashboard bu durumu
  "Veri yok" / "—" olarak gösterir, diğer metrikleri etkilemez.
- Projeyi eski (Brent/faiz eklenmeden önceki) bir `data\prices.csv` ile
  çalıştırırsanız `fetch_data.py` ilk seferinde CSV'yi otomatik olarak yeni
  sütun düzenine geçirir (migration); eski satırlarınız kaybolmaz, sadece
  yeni sütunlar o satırlarda boş görünür.
- `config.py` içinde API anahtarınız bulunacağı için bu dosyayı
  başkalarıyla paylaşmayın / genel bir depoya (git) yüklemeyin.
