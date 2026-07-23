<h1 align="center">
  <br>
    ETL Project - AI Companies Market Cap
  <br>
  <br>
</h1>

## Author
**Nama:** Sherry Eunike
**NIM:** 18224075

## Project Description
Project ini melakukan proses ETL (Extract, Transform, Load) untuk mengumpulkan dan menyimpan data ranking perusahaan AI berdasarkan market cap dari website companiesmarketcap.com. Selain data ranking, project ini juga mengambil data kategori industri tiap perusahaan dan histori market cap tahunan dari halaman masing-masing perusahaan.

Topik ini dipilih dengan beberapa pertimbangan:
1. Industri AI saat ini menjadi salah satu sektor dengan pertumbuhan market cap tercepat dalam beberapa tahun terakhir sehingga data ini relevan untuk melihat bagaimana valuasi perusahaan di sektor ini berubah dari waktu ke waktu.
2. Data yang tersedia punya 2 dimensi sekaligus: cross-sectional (perbandingan antar perusahaan di satu waktu) dan time-series (histori market cap tahunan tiap perusahaan) sehingga bisa juga dipakai untuk analisis pertumbuhan (growth rate).
3. Satu perusahaan bisa masuk ke lebih dari satu kategori industri sehingga membuka peluang analisis lintas-sektor, seperti melihat sektor mana yang paling banyak overlap dengan AI.
4. Selain company, source ini juga mengklasifikasikan aset finansial lain (ETF, cryptocurrency, precious metals) dengan market cap sehingga desain database bisa dibuat lebih general jika ke depannya akan diperluas ke kategori aset lain selain companies.

**DBMS yang digunakan:** PostgreSQL

**Alasan:** mendukung constraint dan trigger yang cukup lengkap untuk implementasi generalization/specialization pada desain ERD project ini

## Step 1: Data Scraping

### How to use Scraper

1. Instalasi dependencies:
```bash
pip install requests beautifulsoup4
```

2. Menjalankan scraper:
```bash
cd "Data Scraping/src"
python scraper.py
```
Scraper akan mengambil data dari halaman AI Companies, lalu mengunjungi halaman detail tiap perusahaan untuk mengambil data kategori industri dan histori market cap tahunan.

Sebelumnya, sempat dipertimbangkan penggunaan Selenium untuk proses scraping tetapi karena struktur HTML halaman sudah server-side rendered, maka requests dan BeautifulSoup sudah cukup tanpa perlu browser automation.

3. Output: 5 file JSON akan tersimpan di folder `Data Scraping/data/`

### Target Website
- **URL Utama:** https://companiesmarketcap.com/artificial-intelligence/largest-ai-companies-by-marketcap/
- **Halaman yang di-scrape:**
  - Halaman ranking AI companies (nama company, ticker, market cap, price, negara)
  - Halaman detail tiap company (kategori industri, histori market cap per tahun)

### File JSON Format

#### 1. `companies.json`
```json
{
  "name": "NVIDIA",
  "ticker": "NVDA",
  "country": "USA",
  "detail_url": "https://companiesmarketcap.com/nvidia/marketcap/"
}
```
* `name` (String): nama perusahaan
* `ticker` (String): kode saham perusahaan
* `country` (String): negara asal perusahaan
* `detail_url` (String): URL halaman detail perusahaan pada source

#### 2. `industries.json`
```json
{
  "name": "Semiconductors",
  "url": "https://companiesmarketcap.com/semiconductors/largest-semiconductor-companies-by-market-cap/"
}
```
* `name` (String): nama kategori industri
* `url` (String): URL halaman ranking industri tersebut pada source

#### 3. `company_industries.json`
```json
{
  "ticker": "NVDA",
  "industry_name": "Semiconductors"
}
```
* `ticker` (String): reference ke `companies.json`
* `industry_name` (String): reference ke `industries.json`

#### 4. `market_cap_snapshots.json`
```json
{
  "ticker": "NVDA",
  "market_cap": 5109000000000.0,
  "price": 210.96,
  "today_change_pct": 4.03,
  "extracted_at": "2026-07-12T11:06:33.290692+00:00"
}
```
* `ticker` (String): reference ke `companies.json`
* `market_cap` (Float): nilai market cap perusahaan pada saat scraping dilakukan (dalam USD)
* `price` (Float): harga saham perusahaan pada saat scraping dilakukan
* `today_change_pct` (Float): persentase perubahan harga saham dibanding hari sebelumnya
* `extracted_at` (String, ISO 8601 datetime): tanggal dan waktu data diambil melalui proses scraping

#### 5. `market_cap_yearly_history.json`
```json
{
  "ticker": "NVDA",
  "year": 2026,
  "market_cap": 5109000000000.0,
  "change_pct_raw": "10.15%"
}
```
* `ticker` (String): reference ke `companies.json`
* `year` (Integer): tahun data market cap (end-of-year value)
* `market_cap` (Float): nilai market cap perusahaan pada tahun tersebut (dalam USD)
* `change_pct_raw` (String): persentase perubahan market cap dibanding tahun sebelumnya

## Step 2: Data Modeling & Data Storing

### ERD (Entity Relationship Diagram)
![ERD](Data%20Storing/design/ERD%20Diagram.png)

**Entitas Utama:**
- **market_assets**: superclass, menyimpan atribut umum tiap aset finansial
- **companies, etfs, cryptocurrencies, precious_metals**: subclass dari market_assets, hanya companies yang diisi data hasil scraping
- **countries**: daftar negara asal aset
- **industries**: daftar kategori industri
- **market_cap_snapshots**: data market cap company pada saat scraping dilakukan
- **market_cap_yearly_history**: histori market cap tahunan tiap company

**Relationship:**
- market_assets ISA companies, etfs, cryptocurrencies, precious_metals (disjoint, total)
- market_assets N:1 countries
- market_assets M:N industries
- companies 1:N market_cap_snapshots
- companies 1:N market_cap_yearly_history (weak entity)

### Relational Diagram
![Diagram Relasional](Data%20Storing/design/Relational%20Diagram.png)

### ERD to Relational Diagram Translation

1. **Generalization/Specialization:** superclass market_assets menjadi tabel tersendiri dan tiap subclass (companies, etfs, cryptocurrencies, precious_metals) juga menjadi tabel tersendiri dengan primary key sendiri dan foreign key unique ke market_assets. Constraint disjoint (satu asset hanya boleh masuk 1 subclass) diimplementasikan menggunakan trigger karena tidak bisa dijamin hanya dengan foreign key biasa.
2. **Multivalued attribute:** atribut market cap tahunan pada company (bisa punya banyak nilai tapi jadinya satu per tahun) ditranslasikan menjadi tabel market_cap_yearly_history sebagai weak entity, dengan primary key composite (company_id, year).
3. **Composite attribute:** ticker yang berisi 2 informasi didekomposisi menjadi 2 kolom terpisah (ticker_code dan exchange_suffix) pada tabel market_assets.
4. **Many-to-many:** relasi market_assets dengan industries ditranslasikan menjadi tabel baru asset_industries, berisi foreign key ke kedua tabel yang digabung menjadi primary key composite.
5. **One-to-many:** relasi companies dengan market_cap_snapshots dan market_cap_yearly_history ditranslasikan dengan menambahkan foreign key company_id pada tabel di sisi many.

### How to use Storing

1. Setup database:
```bash
psql -U postgres
CREATE DATABASE ai_companies_marketcap;
```

2. Sesuaikan konfigurasi koneksi database pada `storing.py`:
```python
hostname = 'localhost'
database = 'ai_companies_marketcap'
username = 'postgres'
pwd = 'your_password'
port_id = 5432
```

3. Jalankan script:
```bash
cd "Data Storing/src"
python storing.py
```

4. Proses yang dilakukan:
   - Membuat semua tabel beserta constraint dan trigger
   - Membaca 5 file JSON hasil scraping
   - Insert data dengan urutan sesuai dependency antar tabel

5. Lakukan dumping database:
```bash
pg_dump -U postgres -h localhost -p 5432 ai_companies_marketcap > ai_companies_marketcap.sql
```

### Final Database Tables

**Query menampilkan seluruh company dari negara tertentu:**
```sql
SELECT ma.name, ma.ticker_code, co.country_name
FROM market_assets ma JOIN companies c ON ma.asset_id = c.asset_id
JOIN countries co ON ma.country_id = co.country_id
WHERE co.country_name = 'China';
```

![Query Countries](Data%20Storing/screenshot/Query%20countries.png)

**Query menampilkan company yang termasuk kategori industri tertentu:**
```sql
SELECT ma.name, ma.ticker_code
FROM market_assets ma JOIN asset_industries ai ON ma.asset_id = ai.asset_id
JOIN industries i ON ai.industry_id = i.industry_id
WHERE i.industry_name = 'Software';
```

![Query Industries](Data%20Storing/screenshot/Query%20industries.png)

**Query menampilkan data market cap snapshot tertinggi:**
```sql
SELECT ma.name, mc.market_cap
FROM market_assets ma JOIN companies c ON ma.asset_id = c.asset_id
JOIN market_cap_snapshots mc ON c.company_id = mc.company_id
WHERE mc.market_cap > 1000000000000
ORDER BY mc.market_cap DESC;
```

![Query Market Cap Snapshots](Data%20Storing/screenshot/Query%20marketcapsnapshots.png)

**Query menampilkan histori market cap tahunan salah satu company:**
```sql
SELECT ma.name, mc.year, mc.market_cap, mc.change_pct
FROM market_cap_yearly_history mc JOIN companies c ON mc.company_id = c.company_id
JOIN market_assets ma ON c.asset_id = ma.asset_id
WHERE ma.name = 'IBM'
ORDER BY mc.year DESC;
```

![Query Market Cap Yearly History](Data%20Storing/screenshot/Query%20marketcapyearlyhistory.png)
```
```

## Bonus: Data Warehouse

### Skema Data Warehouse
Data warehouse dirancang menggunakan galaxy schema karena ada 2 fact table (`fact_yearly_marketcap` dan `fact_snapshot_marketcap`) yang berbagi dimension table yang sama (`dim_company`). Kedua fact table dipisah karena memiliki grain waktu yang berbeda: data histori tahunan dan data snapshot pada saat scraping dilakukan.

### ERD (Entity Relationship Diagram)
![ERD Data Warehouse](Data%20Warehouse/design/ERD%20Diagram.png)

### Relational Diagram
![Relational Diagram Data Warehouse](Data%20Warehouse/design/Relational%20Diagram.png)

**Fact table:**
- `fact_yearly_marketcap`: market cap dan persentase perubahan per company per tahun, primary key composite (company_id, year)
- `fact_snapshot_marketcap`: market cap, price, dan persentase perubahan per company pada saat scraping dilakukan, primary key composite (company_id, extracted_at)

**Dimension table:**
- `dim_company`: hasil denormalisasi dari companies, market_assets, dan countries di database
- `dim_industry`: daftar kategori industri
- `dim_date_year`: daftar tahun yang tersedia pada data histori

**Bridge table:**
- `bridge_company_industry`: menghubungkan `dim_company` dengan `dim_industry` karena relasinya many-to-many (satu company bisa masuk lebih dari satu kategori industri, jadi kalau industry_id langsung ditaruh di fact table, satu baris measurement bisa terhitung berkali-kali)

### Cara menggunakan Data Warehouse

1. Setup database:
```bash
psql -U postgres
CREATE DATABASE ai_companies_warehouse;
```

2. Sesuaikan konfigurasi koneksi database OLTP dan warehouse pada `warehousing.py`:
```python
oltp_conn = psycopg2.connect(host='localhost', dbname='ai_companies_marketcap', user='postgres', password='your_password', port=5432)
wh_conn = psycopg2.connect(host='localhost', dbname='ai_companies_warehouse', user='postgres', password='your_password', port=5432)
```

3. Jalankan script:
```bash
cd "Data Warehouse/src"
python warehouse.py
```

4. Lakukan dumping database:
```bash
pg_dump -U postgres -h localhost -p 5432 ai_companies_warehouse > ai_companies_warehouse.sql
```

### Contoh Query Analitik

**Rata-rata pertumbuhan market cap per industri:**
```sql
SELECT di.industry_name, ROUND(AVG(fy.change_pct), 2) AS avg_growth_pct, COUNT(*) AS count_company
FROM fact_yearly_marketcap fy JOIN bridge_company_industry bci ON fy.company_id = bci.company_id
JOIN dim_industry di ON bci.industry_id = di.industry_id
WHERE fy.year = 2026
GROUP BY di.industry_name
ORDER BY avg_growth_pct DESC, di.industry_name DESC;
```

![Average Growth Market Cap per Industry](Data%20Warehouse/screenshot/Average%20growth%20market%20cap%20per%20industry.png)

**Top 10 company dengan pertumbuhan market cap tercepat:**
```sql
SELECT dc.company_name, fy.market_cap, fy.change_pct
FROM fact_yearly_marketcap fy JOIN dim_company dc ON fy.company_id = dc.company_id
WHERE fy.year = 2025 AND fy.change_pct IS NOT NULL
ORDER BY fy.change_pct DESC
LIMIT 10;
```

![Top 10 Company with Fastest Growth](Data%20Warehouse/screenshot/Top%2010%20company%20with%20fastest%20growth.png)

**Total market cap gabungan per negara:**
```sql
SELECT dc.country_name, SUM(fy.market_cap) AS total_market_cap
FROM fact_yearly_marketcap fy JOIN dim_company dc ON fy.company_id = dc.company_id
WHERE fy.year = 2026
GROUP BY dc.country_name
ORDER BY total_market_cap DESC;
```

![Total Market Cap per Country](Data%20Warehouse/screenshot/Total%20market%20cap%20per%20country.png)

## Bonus: Automated Scheduling

Proses ETL (scraping, storing, warehousing) dijadwalkan berjalan otomatis menggunakan Task Scheduler pada Windows, dengan file `run_all.bat` yang menjalankan ketiga script secara berurutan.

### Cara setup

1. File `run_all.bat` ada di root folder project akan menjalankan `scraper.py`, `storing.py`, dan `warehouse.py` secara berurutan sambil mencatat log ke `log.txt`
2. Buka Task Scheduler dan buat task baru dengan action menjalankan `run_all.bat`, dengan trigger daily dan repeat setiap 1 jam
3. Data yang dihasilkan tiap kali proses ETL berjalan akan otomatis masuk ke database tanpa perlu setup ulang

### Bukti scheduling berjalan

Query berikut menunjukkan ada lebih dari satu timestamp ekstraksi pada tabel market_cap_snapshots, sebagai bukti data berhasil di-update secara berkala melalui beberapa kali eksekusi:
```sql
SELECT DISTINCT extracted_at::date, extracted_at::time, COUNT(*)
FROM market_cap_snapshots
GROUP BY extracted_at::date, extracted_at::time
ORDER BY extracted_at::date, extracted_at::time;
```
![Automated Scheduling](screenshot%20automated%20scheduling.png)

## Penggunaan AI

Selama pengerjaan project ini, AI digunakan sebagai alat bantu untuk:
- Berdiskusi dalam mengeksplorasi website source sebelum menentukan topik dan metode scraping yang akan digunakan
- Membantu proses debugging pada scraper, storing dan warehouse saat menemukan error
- Membantu membuat file run_all.bat agar proses ETL dapat dijalankan secara berurutan sebagai bagian dari automated scheduling
- Memberikan masukan dalam penyusunan struktur README serta membantu merapikan penulisan

Yang dikerjakan sendiri:
- Menentukan topik project dan memilih website source yang digunakan
- Mendesain serta merevisi ERD, diagram relasional dan skema data warehouse
- Melakukan setup Task Scheduler serta memastikan proses scheduling berjalan dengan benar
- Meninjau, menyesuaikan, dan menguji seluruh kode serta memverifikasi data yang dimuat ke database dan data warehouse
- Menyusun isi README beserta penjelasan dan dokumentasi project

Refleksi: penggunaan AI cukup membantu, terutama untuk mempercepat proses eksplorasi website dan membantu saat debugging. Namun, setiap solusi yang diberikan tetap saya pelajari, sesuaikan dengan kebutuhan project dan uji kembali sebelum digunakan agar hasil akhirnya sesuai dengan yang diinginkan.

## Referensi

**1. Library**<br>
[Requests](https://pypi.org/project/requests/)<br>
[BeautifulSoup4](https://pypi.org/project/beautifulsoup4/)<br>
[psycopg2](https://pypi.org/project/psycopg2/)<br>
[Bridge Tables](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/multivalued-dimension-bridge-table/)

**2. Third-party Application**<br>
Task Scheduler (Windows)<br>
draw.io (desain ERD dan diagram relasional)

**3. Website Source**<br>
[AI Companies by Market Cap](https://companiesmarketcap.com/artificial-intelligence/largest-ai-companies-by-marketcap/)<br>
Tambahan: [CompaniesMarketCap](https://companiesmarketcap.com/)