@echo off
REM ================================================================
REM run_daily.bat
REM TRY piyasa takip projesi icin gunluk calisan toplu is dosyasi.
REM Windows Gorev Zamanlayicisi bu dosyayi calistirir.
REM   1) fetch_data.py      -> guncel kurlari/fiyatlari ceker, CSV'ye ekler
REM   2) generate_dashboard.py -> dashboard.html'i CSV'deki en guncel
REM                                veriyle yeniden uretir
REM ================================================================

REM %~dp0 bu .bat dosyasinin bulundugu klasordur; Gorev Zamanlayici
REM farkli bir "Start in" klasorunden calistirsa bile dogru yeri bulur.
cd /d "%~dp0"

echo [%date% %time%] fetch_data.py calistiriliyor... >> run_daily.log
python fetch_data.py >> run_daily.log 2>&1

echo [%date% %time%] generate_dashboard.py calistiriliyor... >> run_daily.log
python generate_dashboard.py >> run_daily.log 2>&1

echo [%date% %time%] Tamamlandi. >> run_daily.log
