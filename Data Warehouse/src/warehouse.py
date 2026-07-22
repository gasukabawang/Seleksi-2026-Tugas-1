import psycopg2
from datetime import datetime

# connect to database OLTP (source)
oltp_conn = psycopg2.connect(
    host='localhost',
    dbname='ai_companies_marketcap',
    user='postgres',
    password='praktikum',
    port=5432,
)
oltp_cur = oltp_conn.cursor()

# connect database warehouse
wh_conn = psycopg2.connect(
    host='localhost',
    dbname='ai_companies_warehouse',
    user='postgres',
    password='praktikum',
    port=5432,
)
wh_cur = wh_conn.cursor()

# create warehouse
scheme = '''
    DROP TABLE IF EXISTS fact_snapshot_marketcap CASCADE;
    DROP TABLE IF EXISTS fact_yearly_marketcap CASCADE;
    DROP TABLE IF EXISTS bridge_company_industry CASCADE;
    DROP TABLE IF EXISTS dim_industry CASCADE;
    DROP TABLE IF EXISTS dim_company CASCADE;
    DROP TABLE IF EXISTS dim_date_year CASCADE;

    CREATE TABLE dim_date_year(
        year INT PRIMARY KEY
    );

    CREATE TABLE dim_company(
        company_id INT PRIMARY KEY,
        company_name VARCHAR(255) NOT NULL,
        ticker_code VARCHAR(50),
        country_name VARCHAR(100)
    );

    CREATE TABLE dim_industry(
        industry_id INT PRIMARY KEY,
        industry_name VARCHAR(100) NOT NULL
    );

    CREATE TABLE bridge_company_industry(
        company_id INT NOT NULL,
        industry_id INT NOT NULL,
        PRIMARY KEY (company_id, industry_id),
        FOREIGN KEY (company_id) REFERENCES dim_company(company_id),
        FOREIGN KEY (industry_id) REFERENCES dim_industry(industry_id)
    );

    CREATE TABLE fact_yearly_marketcap(
        company_id INT NOT NULL,
        year INT NOT NULL,
        market_cap NUMERIC(20,2),
        change_pct NUMERIC(10,3),
        PRIMARY KEY (company_id, year),
        FOREIGN KEY (company_id) REFERENCES dim_company(company_id),
        FOREIGN KEY (year) REFERENCES dim_date_year(year)
    );

    CREATE TABLE fact_snapshot_marketcap(
        company_id INT NOT NULL,
        extracted_at TIMESTAMPTZ NOT NULL,
        market_cap NUMERIC(20,2),
        price NUMERIC(12,4),
        change_pct NUMERIC(10,3),
        PRIMARY KEY (company_id, extracted_at),
        FOREIGN KEY (company_id) REFERENCES dim_company(company_id)
    );
'''
wh_cur.execute(scheme)
wh_conn.commit()
print("Create success")

# dim_company from companies + market_assets + countries
oltp_cur.execute('''
    SELECT c.company_id, ma.name, ma.ticker_code, co.country_name
    FROM companies c JOIN market_assets ma ON c.asset_id = ma.asset_id
    JOIN countries co ON ma.country_id = co.country_id
''')
companies_rows = oltp_cur.fetchall()

insert_company = 'INSERT INTO dim_company(company_id, company_name, ticker_code, country_name) VALUES (%s, %s, %s, %s)'
for row in companies_rows:
    wh_cur.execute(insert_company, row)
print("data dim_company added")

# dim_industry
oltp_cur.execute('SELECT industry_id, industry_name FROM industries')
industries_rows = oltp_cur.fetchall()

insert_industry = 'INSERT INTO dim_industry(industry_id, industry_name) VALUES (%s, %s)'
for row in industries_rows:
    wh_cur.execute(insert_industry, row)
print("data dim_industry added")

# bridge_company_industry
oltp_cur.execute('''
    SELECT c.company_id, ai.industry_id
    FROM asset_industries ai JOIN companies c ON ai.asset_id = c.asset_id
''')
bridge_rows = oltp_cur.fetchall()

insert_bridge = 'INSERT INTO bridge_company_industry(company_id, industry_id) VALUES (%s, %s)'
for row in bridge_rows:
    wh_cur.execute(insert_bridge, row)
print("data bridge_company_industry added")

# dim_date_year
oltp_cur.execute('SELECT DISTINCT year FROM market_cap_yearly_history ORDER BY year')
year_rows = oltp_cur.fetchall()

insert_year = 'INSERT INTO dim_date_year(year) VALUES (%s)'
for row in year_rows:
    wh_cur.execute(insert_year, row)
print("data dim_date_year added")

# fact_yearly_marketcap
oltp_cur.execute('SELECT company_id, year, market_cap, change_pct FROM market_cap_yearly_history')
yearly_rows = oltp_cur.fetchall()

insert_fact_yearly = 'INSERT INTO fact_yearly_marketcap(company_id, year, market_cap, change_pct) VALUES (%s, %s, %s, %s)'
for row in yearly_rows:
    wh_cur.execute(insert_fact_yearly, row)
print("data fact_yearly_marketcap added")

# fact_snapshot_marketcap
oltp_cur.execute('SELECT company_id, extracted_at, market_cap, price, today_change_pct FROM market_cap_snapshots')
snapshot_rows = oltp_cur.fetchall()

insert_fact_snapshot = 'INSERT INTO fact_snapshot_marketcap(company_id, extracted_at, market_cap, price, change_pct) VALUES (%s, %s, %s, %s, %s)'
for row in snapshot_rows:
    wh_cur.execute(insert_fact_snapshot, row)
print("data fact_snapshot_marketcap added")

wh_conn.commit()
print("Data loaded to database ai_companies_warehouse")

oltp_cur.close()
oltp_conn.close()
wh_cur.close()
wh_conn.close()