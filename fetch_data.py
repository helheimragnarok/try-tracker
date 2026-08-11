"""
fetch_data.py
--------------
TRY (Turk Lirasi) icin USD/TRY, EUR/TRY, gram altin, gram gumus, Brent
petrol ve (varsa) TCMB bankalar arasi TL mevduat agirlikli ortalama faiz
oranini ucretsiz kaynaklardan ceker ve data/prices.csv dosyasina tarih
damgasiyla ekler (append).

Kaynaklar:
  - Doviz kurlari   : frankfurter.app       (yedek: open.er-api.com)      - key gerekmez
  - Kiymetli maden  : gold-api.com          (XAU/XAG, USD/ons spot fiyat) - key gerekmez
  - Brent petrol    : Yahoo Finance chart API (sembol BZ=F, USD/varil)    - key gerekmez
                       (RESMI OLMAYAN/unofficial bir endpoint; Yahoo
                       onceden haber vermeden degistirebilir/kisitlayabilir.
                       Basarisiz olursa bu alan bos birakilir, script durmaz.)
  - Mevduat faizi   : TCMB EVDS (Elektronik Veri Dagitim Sistemi, evds3.tcmb.gov.tr) - UCRETSIZ
                       ama API ANAHTARI GEREKTIRIR (siteden kayit olup edinilir).
                       config.py icine yazilir. Kuruldu ve gercek anahtarla dogrulandi
                       (seri TP.TRY.MT01 - bkz. fetch_deposit_rate() ve README.md).
                       Anahtar girilmemisse bu alan sessizce bos birakilir.

Gram fiyati hesaplama:
  1 troy ons = 31.1034768 gram
  gram_altin_try = (XAU_usd_per_oz / 31.1034768) * USD_TRY
  gram_gumus_try = (XAG_usd_per_oz / 31.1034768) * USD_TRY

Not: gold-api.com ve Yahoo Finance uluslararasi spot/vadeli fiyatlari verir;
Turkiye'deki fiziksel "gram altin" veya akaryakit fiyatlarindan (kuyumcu
marji, ÖTV/vergi vb. nedenlerle) farklilik gosterebilir. Bu script
referans/spot bazli bir yaklasim sunar.
"""

import csv
import os
import sys
from datetime import datetime, timedelta, timezone

# Kurumsal / bazi Windows aglarinda Python'un kendi CA paketi (certifi)
# yerel SSL sertifikalarini tanimayabiliyor. truststore, Windows'un kendi
# sertifika deposunu kullanmasini saglar (PowerShell / tarayici gibi).
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass  # truststore kurulu degilse veya bu ortamda desteklenmiyorsa normal certifi ile devam edilir

import requests

# config.py opsiyoneldir (ozellikle EVDS_API_KEY icin). Yoksa/eksikse
# script yine calisir, sadece mevduat faiz alani bos kalir.
try:
    import config
except ImportError:
    config = None

# Oncelik sirasi: config.py -> ortam degiskeni (GitHub Actions secret'i icin,
# repo'ya girmeyen config.py yerine EVDS_API_KEY/EVDS_SERIES env var'lari
# kullanilabilir) -> bos.
EVDS_API_KEY = getattr(config, "EVDS_API_KEY", "") if config else ""
EVDS_API_KEY = EVDS_API_KEY or os.environ.get("EVDS_API_KEY", "")
EVDS_SERIES = getattr(config, "EVDS_SERIES", "") if config else ""
EVDS_SERIES = EVDS_SERIES or os.environ.get("EVDS_SERIES", "TP.TRY.MT01")

TROY_OUNCE_TO_GRAM = 31.1034768

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
CSV_PATH = os.path.join(DATA_DIR, "prices.csv")
LOG_PATH = os.path.join(SCRIPT_DIR, "fetch_log.txt")

CSV_HEADERS = [
    "timestamp_utc",
    "timestamp_local",
    "usd_try",
    "eur_try",
    "xau_usd_oz",
    "xag_usd_oz",
    "gram_altin_try",
    "gram_gumus_try",
    "brent_usd_bbl",
    "brent_try_bbl",
    "mevduat_faiz_pct",
]

REQUEST_TIMEOUT = 15
YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def log(message: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def fetch_exchange_rates() -> dict:
    """USD/TRY ve EUR/TRY kurlarini dondurur. Once frankfurter.app, o
    calismazsa open.er-api.com denenir. Ikisi de basarisiz olursa
    RuntimeError firlatir (bu veri zorunlu, cunku gram/Brent TRY
    cevrimleri buna bagli)."""

    # 1) Birincil kaynak: frankfurter.app
    try:
        r = requests.get(
            "https://api.frankfurter.app/latest",
            params={"from": "USD", "to": "TRY,EUR"},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        rates = r.json()["rates"]
        usd_try = float(rates["TRY"])
        usd_eur = float(rates["EUR"])
        eur_try = usd_try / usd_eur
        log("Doviz kurlari frankfurter.app kaynagindan alindi.")
        return {"usd_try": usd_try, "eur_try": eur_try}
    except Exception as exc:
        log(f"UYARI: frankfurter.app basarisiz ({exc}). Yedek kaynaga geciliyor.")

    # 2) Yedek kaynak: open.er-api.com
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        rates = data["rates"]
        usd_try = float(rates["TRY"])
        usd_eur = float(rates["EUR"])
        eur_try = usd_try / usd_eur
        log("Doviz kurlari open.er-api.com (yedek) kaynagindan alindi.")
        return {"usd_try": usd_try, "eur_try": eur_try}
    except Exception as exc:
        log(f"HATA: Yedek doviz kaynagi da basarisiz ({exc}).")
        raise RuntimeError("Doviz kurlari hicbir kaynaktan alinamadi.") from exc


def fetch_metal_prices() -> dict:
    """XAU (altin) ve XAG (gumus) spot fiyatlarini USD/ons olarak dondurur.
    Bu veri zorunlu kabul edilir; basarisiz olursa RuntimeError firlatir."""
    prices = {}
    for symbol, key in (("XAU", "xau_usd_oz"), ("XAG", "xag_usd_oz")):
        try:
            r = requests.get(f"https://api.gold-api.com/price/{symbol}", timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            prices[key] = float(r.json()["price"])
        except Exception as exc:
            log(f"HATA: {symbol} fiyati gold-api.com kaynagindan alinamadi ({exc}).")
            raise RuntimeError(f"{symbol} fiyati alinamadi.") from exc
    log("Kiymetli maden fiyatlari gold-api.com kaynagindan alindi.")
    return prices


def fetch_brent_price() -> float | None:
    """Brent petrol fiyatini USD/varil olarak dondurur (Yahoo Finance,
    sembol BZ=F). Resmi olmayan bir endpoint oldugu icin basarisiz olursa
    script'i durdurmaz, None doner ve o gun bu alan bos birakilir."""
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            r = requests.get(
                f"https://{host}/v8/finance/chart/BZ=F",
                params={"interval": "1d", "range": "5d"},
                headers=YAHOO_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            r.raise_for_status()
            price = r.json()["chart"]["result"][0]["meta"]["regularMarketPrice"]
            log(f"Brent petrol fiyati Yahoo Finance ({host}) kaynagindan alindi.")
            return float(price)
        except Exception as exc:
            log(f"UYARI: Brent fiyati {host} kaynagindan alinamadi ({exc}).")
    log("UYARI: Brent petrol fiyati hicbir kaynaktan alinamadi, bu alan bos birakilacak.")
    return None


def fetch_deposit_rate() -> float | None:
    """TCMB EVDS'den '1 Aya Kadar Vadeli TL Mevduat' agirlikli ortalama
    faiz oranini (%, haftalik/Cuma) dondurur. API anahtari yoksa veya
    istek basarisiz olursa None doner (script durmaz, alan bos birakilir).

    NOT (Agustos 2026): TCMB, EVDS'i eski 'evds2.tcmb.gov.tr' sisteminden
    yeni 'evds3.tcmb.gov.tr' sistemine tasidi - eski /service/evds/
    adresi artik calismiyor (evds3 anasayfasina yonlendiriyor). Guncel
    format dogrulandi:
      - Endpoint: https://evds3.tcmb.gov.tr/igmevdsms-dis/series=...&startDate=...&endDate=...&type=json
        (parametreler '?' OLMADAN dogrudan path'e eklenir - EVDS'e ozgu bir kural)
      - 'key' HTTP header olarak gonderilir (query parametresi olarak DEGIL;
        Nisan 2024'ten beri boyle - eskiden query param yeterliydi)
      - Seri kodu TP.TRY.MT01 = "1 Aya Kadar Vadeli (TL Mevduat, Akim, %)"
        (kaynak: Mevduat Bankalari, haftalik/Cuma) - gercek anahtarla
        canli test edilip dogrulandi.
    Farkli bir vade (orn. 3 ay = TP.TRY.MT02 gibi) isterseniz config.py
    icindeki EVDS_SERIES degiskenini evds3.tcmb.gov.tr/tumSeriler
    sayfasindan bulacaginiz baska bir kodla degistirebilirsiniz."""
    if not EVDS_API_KEY:
        log("BILGI: EVDS_API_KEY ayarlanmamis (config.py), mevduat faiz orani atlaniyor.")
        return None

    try:
        end = datetime.now()
        start = end - timedelta(days=21)
        query = (
            f"series={EVDS_SERIES}"
            f"&startDate={start.strftime('%d-%m-%Y')}"
            f"&endDate={end.strftime('%d-%m-%Y')}"
            f"&type=json"
        )
        url = f"https://evds3.tcmb.gov.tr/igmevdsms-dis/{query}"
        r = requests.get(url, headers={"key": EVDS_API_KEY}, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        items = r.json().get("items", [])
        if not items:
            log(f"UYARI: EVDS serisi '{EVDS_SERIES}' bos sonuc dondurdu. Seri kodunu dogrulayin (bkz. README).")
            return None

        field = EVDS_SERIES.replace(".", "_")
        for item in reversed(items):  # en guncel (son) dolu degeri al
            val = item.get(field)
            if val not in (None, ""):
                log(f"Mevduat faiz orani TCMB EVDS ({EVDS_SERIES}) kaynagindan alindi.")
                return float(val)
        log(f"UYARI: EVDS serisi '{EVDS_SERIES}' icin dolu deger bulunamadi.")
        return None
    except Exception as exc:
        log(f"UYARI: TCMB EVDS mevduat faiz orani alinamadi ({exc}). Bu alan bos birakilacak.")
        return None


def migrate_csv_if_needed() -> None:
    """Eski surumden kalma bir prices.csv (daha az sutunlu) varsa, yeni
    sutunlari sonuna ekleyerek (eski satirlarda bos deger ile) yeniden
    yazar. Eski veri asla silinmez."""
    if not os.path.exists(CSV_PATH):
        return

    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        existing_header = reader.fieldnames or []
        rows = list(reader)

    if existing_header == CSV_HEADERS:
        return  # zaten guncel

    log(f"CSV semasi guncelleniyor ({len(existing_header)} -> {len(CSV_HEADERS)} sutun), eski veri korunuyor.")
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in CSV_HEADERS})


def ensure_csv_exists() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
        log(f"Yeni CSV dosyasi olusturuldu: {CSV_PATH}")
    else:
        migrate_csv_if_needed()


def append_row(row: dict) -> None:
    ensure_csv_exists()
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([row[h] for h in CSV_HEADERS])
    log(f"Satir eklendi: {CSV_PATH}")


def main() -> int:
    try:
        fx = fetch_exchange_rates()
        metals = fetch_metal_prices()
        brent_usd = fetch_brent_price()          # basarisizsa None (opsiyonel)
        deposit_rate = fetch_deposit_rate()       # basarisizsa None (opsiyonel)

        usd_try = fx["usd_try"]
        gram_altin_try = (metals["xau_usd_oz"] / TROY_OUNCE_TO_GRAM) * usd_try
        gram_gumus_try = (metals["xag_usd_oz"] / TROY_OUNCE_TO_GRAM) * usd_try
        brent_try = brent_usd * usd_try if brent_usd is not None else None

        now_utc = datetime.now(timezone.utc)
        # Turkiye sabit UTC+3 kullanir (2016'dan beri yaz saati uygulamasi
        # yok), bu yuzden calistigi makinenin (Windows yerel saati veya
        # GitHub Actions'in UTC'si) saat dilimine bagli kalmadan sabit bir
        # ofsetle hesaplanir - boylece yerel ve Actions kaynakli satirlar
        # ayni saat dilimini kullanir.
        now_local = now_utc.astimezone(timezone(timedelta(hours=3)))

        row = {
            "timestamp_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp_local": now_local.strftime("%Y-%m-%d %H:%M:%S"),
            "usd_try": round(usd_try, 4),
            "eur_try": round(fx["eur_try"], 4),
            "xau_usd_oz": round(metals["xau_usd_oz"], 2),
            "xag_usd_oz": round(metals["xag_usd_oz"], 2),
            "gram_altin_try": round(gram_altin_try, 2),
            "gram_gumus_try": round(gram_gumus_try, 2),
            "brent_usd_bbl": round(brent_usd, 2) if brent_usd is not None else "",
            "brent_try_bbl": round(brent_try, 2) if brent_try is not None else "",
            "mevduat_faiz_pct": round(deposit_rate, 2) if deposit_rate is not None else "",
        }

        append_row(row)

        log(
            "OK  USD/TRY={usd_try}  EUR/TRY={eur_try}  GramAltin={gram_altin_try} TRY  "
            "GramGumus={gram_gumus_try} TRY  Brent={brent_usd_bbl} USD/varil  "
            "MevduatFaiz={mevduat_faiz_pct}%".format(**row)
        )
        return 0
    except Exception as exc:
        log(f"BASARISIZ: Veri cekme islemi tamamlanamadi: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
