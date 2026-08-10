"""
config.example.py
------------------
config.py icin sablon dosya. Bu dosyayi 'config.py' olarak kopyalayip
kendi TCMB EVDS API anahtarinizi girin. config.py .gitignore'da oldugu
icin depoya (git) eklenmez.

Kurulum icin README.md > "TCMB EVDS kurulumu" bolumune bakin.
"""

EVDS_API_KEY = ""  # <-- evds3.tcmb.gov.tr'den aldiginiz ucretsiz anahtari buraya yapistirin

# "TP.TRY.MT01" -> "1 Aya Kadar Vadeli (TL Mevduat, Akim, %)"
EVDS_SERIES = "TP.TRY.MT01"
