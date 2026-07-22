@echo off
echo ===== Mulai proses ETL =====
echo Waktu mulai: %date% %time%

cd /d "C:\Users\sherr\Projects\Seleksi-2026-Tugas-1\Data Scraping\src"
echo.
echo ===== Menjalankan scraper.py =====
python scraper.py

cd /d "C:\Users\sherr\Projects\Seleksi-2026-Tugas-1\Data Storing\src"
echo.
echo ===== Menjalankan storing.py =====
python storing.py

cd /d "C:\Users\sherr\Projects\Seleksi-2026-Tugas-1\Data Warehouse\src"
echo.
echo ===== Menjalankan warehouse.py =====
python warehouse.py

echo.
echo ===== Proses ETL selesai =====
echo Waktu selesai: %date% %time%
