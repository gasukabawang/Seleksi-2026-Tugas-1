@echo off
echo ===== Mulai proses ETL =====
echo Waktu mulai: %date% %time%

echo ===== Mulai proses ETL ===== >> "C:\Users\sherr\Projects\Seleksi-2026-Tugas-1\log.txt"
echo Waktu mulai: %date% %time% >> "C:\Users\sherr\Projects\Seleksi-2026-Tugas-1\log.txt"

cd /d "C:\Users\sherr\Projects\Seleksi-2026-Tugas-1\Data Scraping\src"
echo Menjalankan scraper.py...
python scraper.py >> "C:\Users\sherr\Projects\Seleksi-2026-Tugas-1\log.txt" 2>&1
echo scraper.py selesai

cd /d "C:\Users\sherr\Projects\Seleksi-2026-Tugas-1\Data Storing\src"
echo Menjalankan storing.py...
python storing.py >> "C:\Users\sherr\Projects\Seleksi-2026-Tugas-1\log.txt" 2>&1
echo storing.py selesai

cd /d "C:\Users\sherr\Projects\Seleksi-2026-Tugas-1\Data Warehouse\src"
echo Menjalankan warehouse.py...
python warehouse.py >> "C:\Users\sherr\Projects\Seleksi-2026-Tugas-1\log.txt" 2>&1
echo warehouse.py selesai

echo ===== Proses ETL selesai =====
echo Waktu selesai: %date% %time%
echo Waktu selesai: %date% %time% >> "C:\Users\sherr\Projects\Seleksi-2026-Tugas-1\log.txt"