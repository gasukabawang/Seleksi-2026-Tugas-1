import json
import os
from datetime import datetime
import psycopg2

path = 'C:/Users/sherr/Projects/Seleksi-2026-Tugas-1/Data Scraping/data'

def join_pathfile(path, file):
    return os.path.join(path, file)

# companies
companies_file = join_pathfile(path, 'companies.json')
with open(companies_file, 'r', encoding='utf-8') as f:
    companies_load = json.load(f)

# industries
industries_file = join_pathfile(path, 'industries.json')
with open(industries_file, 'r', encoding='utf-8') as f:
    industries_load = json.load(f)

# company_industries
company_industries_file = join_pathfile(path, 'company_industries.json')
with open(company_industries_file, 'r', encoding='utf-8') as f:
    company_industries_load = json.load(f)

# market_cap_snapshots
snapshots_file = join_pathfile(path, 'market_cap_snapshots.json')
with open(snapshots_file, 'r', encoding='utf-8') as f:
    snapshots_load = json.load(f)

# market_cap_yearly_history
history_file = join_pathfile(path, 'market_cap_yearly_history.json')
with open(history_file, 'r', encoding='utf-8') as f:
    history_load = json.load(f)

# connect to database
hostname = 'localhost'
database = 'ai_companies_marketcap'
username = 'postgres'
pwd = 'praktikum'
port_id = 5432
conn = None
cur = None

conn = psycopg2.connect(
    host=hostname,
    dbname=database,
    user=username,
    password=pwd,
    port=port_id,
)

cur = conn.cursor()

# create table + trigger
scheme = '''
    DROP TABLE IF EXISTS market_cap_yearly_history CASCADE;
    DROP TABLE IF EXISTS market_cap_snapshots CASCADE;
    DROP TABLE IF EXISTS asset_industries CASCADE;
    DROP TABLE IF EXISTS industries CASCADE;
    DROP TABLE IF EXISTS precious_metals CASCADE;
    DROP TABLE IF EXISTS cryptocurrencies CASCADE;
    DROP TABLE IF EXISTS etfs CASCADE;
    DROP TABLE IF EXISTS companies CASCADE;
    DROP TABLE IF EXISTS market_assets CASCADE;
    DROP TABLE IF EXISTS countries CASCADE;

    CREATE TABLE countries(
        country_id SERIAL PRIMARY KEY,
        country_name VARCHAR(100) NOT NULL UNIQUE
    );

    CREATE TABLE market_assets(
        asset_id SERIAL PRIMARY KEY,
        name VARCHAR(250) NOT NULL,
        detail_url TEXT NOT NULL UNIQUE,
        ticker_code VARCHAR(50),
        exchange_suffix VARCHAR(20),
        country_id INT NOT NULL,
        FOREIGN KEY (country_id) REFERENCES countries(country_id)
    );

    CREATE TABLE companies(
        company_id SERIAL PRIMARY KEY,
        asset_id INT NOT NULL UNIQUE,
        FOREIGN KEY (asset_id) REFERENCES market_assets(asset_id) ON DELETE CASCADE
    );

    CREATE TABLE etfs(
        etf_id SERIAL PRIMARY KEY,
        asset_id INT NOT NULL UNIQUE,
        expense_ratio NUMERIC(6,4),
        FOREIGN KEY (asset_id) REFERENCES market_assets(asset_id) ON DELETE CASCADE
    );

    CREATE TABLE cryptocurrencies(
        crypto_id SERIAL PRIMARY KEY,
        asset_id INT NOT NULL UNIQUE,
        FOREIGN KEY (asset_id) REFERENCES market_assets(asset_id) ON DELETE CASCADE
    );

    CREATE TABLE precious_metals(
        metal_id SERIAL PRIMARY KEY,
        asset_id INT NOT NULL UNIQUE,
        estimated_mined_quantity NUMERIC(20,2),
        FOREIGN KEY (asset_id) REFERENCES market_assets(asset_id) ON DELETE CASCADE
    );

    CREATE TABLE industries(
        industry_id SERIAL PRIMARY KEY,
        industry_name VARCHAR(100) NOT NULL UNIQUE,
        industry_url TEXT
    );

    CREATE TABLE asset_industries(
        asset_id INT,
        industry_id INT,
        PRIMARY KEY (asset_id, industry_id),
        FOREIGN KEY (asset_id) REFERENCES market_assets(asset_id) ON DELETE CASCADE,
        FOREIGN KEY (industry_id) REFERENCES industries(industry_id) ON DELETE CASCADE
    );

    CREATE TABLE market_cap_snapshots(
        snapshot_id SERIAL PRIMARY KEY,
        company_id INT NOT NULL,
        market_cap NUMERIC(20,2),
        price NUMERIC(12,4),
        today_change_pct NUMERIC(10,3),
        extracted_at TIMESTAMPTZ NOT NULL,
        FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
    );

    CREATE TABLE market_cap_yearly_history(
        company_id INT,
        year INT CHECK (year BETWEEN 1990 AND 2050),
        market_cap NUMERIC(20,2),
        change_pct NUMERIC(10,3),
        PRIMARY KEY (company_id, year),
        FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
    );

    CREATE OR REPLACE FUNCTION check_disjoint_subclass()
    RETURNS TRIGGER AS $$
    DECLARE
        found BOOLEAN;
    BEGIN
        SELECT (
            EXISTS (SELECT 1 FROM companies WHERE asset_id = NEW.asset_id)
            OR EXISTS (SELECT 1 FROM etfs WHERE asset_id = NEW.asset_id)
            OR EXISTS (SELECT 1 FROM cryptocurrencies WHERE asset_id = NEW.asset_id)
            OR EXISTS (SELECT 1 FROM precious_metals WHERE asset_id = NEW.asset_id)) 
        INTO found;

        IF found THEN
            RAISE EXCEPTION 'asset_id % already exist', NEW.asset_id;
        END IF;

        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trigger_companies
    BEFORE INSERT ON companies
    FOR EACH ROW
    EXECUTE FUNCTION check_disjoint_subclass();
    
    CREATE TRIGGER trigger_etfs
    BEFORE INSERT ON etfs
    FOR EACH ROW
    EXECUTE FUNCTION check_disjoint_subclass();

    CREATE TRIGGER trigger_crypto
    BEFORE INSERT ON cryptocurrencies
    FOR EACH ROW
    EXECUTE FUNCTION check_disjoint_subclass();

    CREATE TRIGGER trigger_metals
    BEFORE INSERT ON precious_metals
    FOR EACH ROW
    EXECUTE FUNCTION check_disjoint_subclass();
'''
cur.execute(scheme)
conn.commit()
print("Create successful")

# insert countries first, then take unique name from companies_load
country_ids = {}
insert_country = 'INSERT INTO countries(country_name) VALUES (%s) RETURNING country_id'
for c in companies_load:
    if c['country'] not in country_ids:
        cur.execute(insert_country, (c['country'],))
        new_id = cur.fetchone()[0]
        country_ids[c['country']] = new_id
print("countries added")

# insert market_assets and companies
ticker_company_ids = {}
insert_asset = 'INSERT INTO market_assets(name, detail_url, ticker_code, exchange_suffix, country_id) VALUES (%s, %s, %s, %s, %s) RETURNING asset_id'
insert_company = 'INSERT INTO companies(asset_id) VALUES (%s) RETURNING company_id'

for c in companies_load:
    ticker = c['ticker']
    if '.' in ticker:
        ticker_code = ticker.split('.')[0]
        exchange_suffix = ticker.split('.')[1]
    else:
        ticker_code = ticker
        exchange_suffix = None

    country_id = country_ids[c['country']]
    cur.execute(insert_asset, (c['name'], c['detail_url'], ticker_code, exchange_suffix, country_id))
    asset_id = cur.fetchone()[0]

    cur.execute(insert_company, (asset_id,))
    company_id = cur.fetchone()[0]

    ticker_company_ids[ticker] = company_id

print("market_assets dan companies added")

# insert industries
industry_ids = {}
insert_industry = 'INSERT INTO industries(industry_name, industry_url) VALUES (%s, %s) RETURNING industry_id'
for ind in industries_load:
    cur.execute(insert_industry, (ind['name'], ind.get('url')))
    industry_ids[ind['name']] = cur.fetchone()[0]
print("industries added")

# insert asset_industries
cur.execute('SELECT company_id, asset_id FROM companies')
rows = cur.fetchall()
company_to_asset = {}
for row in rows:
    company_to_asset[row[0]] = row[1]

insert_asset_industry = 'INSERT INTO asset_industries(asset_id, industry_id) VALUES (%s, %s)'
for ci in company_industries_load:
    ticker = ci['ticker']
    industry_name = ci['industry_name']
    if ticker not in ticker_company_ids or industry_name not in industry_ids:
        continue
    company_id = ticker_company_ids[ticker]
    asset_id = company_to_asset[company_id]
    industry_id = industry_ids[industry_name]
    cur.execute(insert_asset_industry, (asset_id, industry_id))
print("asset_industries added")

# insert market_cap_snapshots
insert_snapshot = 'INSERT INTO market_cap_snapshots(company_id, market_cap, price, today_change_pct, extracted_at) VALUES (%s, %s, %s, %s, %s)'
for s in snapshots_load:
    ticker = s['ticker']
    if ticker not in ticker_company_ids:
        continue
    company_id = ticker_company_ids[ticker]
    extracted_at = datetime.fromisoformat(s['extracted_at'])
    cur.execute(insert_snapshot, (company_id, s['market_cap'], s['price'], s['today_change_pct'], extracted_at))
print("market_cap_snapshots added")

# insert market_cap_yearly_history
insert_history = 'INSERT INTO market_cap_yearly_history(company_id, year, market_cap, change_pct) VALUES (%s, %s, %s, %s) ON CONFLICT (company_id, year) DO NOTHING'
for h in history_load:
    ticker = h['ticker']
    if ticker not in ticker_company_ids:
        continue
    company_id = ticker_company_ids[ticker]

    change_pct = None
    if h.get('change_pct_raw'):
        try:
            change_pct = float(h['change_pct_raw'].replace('%', ''))
        except ValueError:
            change_pct = None

    cur.execute(insert_history, (company_id, h['year'], h['market_cap'], change_pct))
print("market_cap_yearly_history added")

# commit semua transaction
conn.commit()
print("Data loaded succesfully to database ai_companies_marketcap")

if cur is not None:
    cur.close()
if conn is not None:
    conn.close()