import csv
import os.path
import sqlite3
from functools import wraps
from sqlite3 import Cursor
from textwrap import dedent

cur: Cursor
state = 'main'

def set_state(to_state: str):
    global state
    state = to_state

def back_to_main(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        ret = func(*args, **kwargs)
        set_state('main')
        return ret
    return wrapper

@back_to_main
def not_implemented():
    print('Not implemented!')

def get_cols_from_table(table_name: str):
    cur.execute(f'PRAGMA table_info({table_name})')
    return [info[1] for info in cur.fetchall()]

def get_from_user_ticker_name():
    entered_name = input('Enter company name: \n')
    cur.execute("""SELECT ticker, name FROM companies WHERE lower(name) LIKE ?""", (f"%{entered_name.lower()}%",))
    rows = {idx: (ticker, name) for idx, (ticker, name) in enumerate(cur.fetchall())}
    if len(rows) == 0:
        print('Company not found!')
        return None, None
    for idx, (ticker, name) in rows.items():
        print(f"{idx} {name}")
    target = input('Enter company number: \n')
    ticker, name = rows[int(target)]
    return ticker, name

def insert_company_row(row):
    cur.execute("""
        INSERT INTO companies (ticker, name, sector)
        VALUES (:ticker, :name, :sector)
    """, row)

def insert_financial_row(row):
    cur.execute("""
        INSERT INTO financial (ticker, ebitda, sales, net_profit, market_price, net_debt, assets, equity, cash_equivalents, liabilities)
        VALUES (:ticker, :ebitda, :sales, :net_profit, :market_price, :net_debt, :assets, :equity, :cash_equivalents, :liabilities)
    """, row)

def update_financial_row(row):
    cur.execute("""
        UPDATE financial SET
        ebitda = :ebitda,
        sales = :sales,
        net_profit = :net_profit,
        market_price = :market_price,
        net_debt = :net_debt,
        assets = :assets,
        equity = :equity,
        cash_equivalents = :cash_equivalents,
        liabilities = :liabilities
        WHERE ticker = :ticker
    """, row)

@back_to_main
def create_company():
    company_cols = get_cols_from_table('companies')
    financial_cols = get_cols_from_table('financial')
    company_row:dict[str, str|None] = {col: None for col in company_cols}
    financial_row:dict[str, float|None] = {col: None for col in financial_cols}
    for field, display, example in zip(company_cols, ['ticker', 'company', 'industries'], ['MOON', 'Moon Corp', 'Technology']):
        print(f"Enter {display} (in the format '{example}'):")
        company_row[field] = input()
    financial_row['ticker'] = company_row['ticker']
    for field in financial_cols[1:]:
        print(f"Enter {field.replace('_', ' ')} (in the format '987654321'):")
        financial_row[field] = float(input())
    insert_company_row(company_row)
    insert_financial_row(financial_row)
    print('Company created successfully!')

@back_to_main
def read_company():
    ticker, name = get_from_user_ticker_name()
    if ticker is None and name is None:
        return
    cur.execute("""SELECT * FROM financial WHERE ticker == ?""", (ticker,))
    ticker,ebitda,sales,net_profit,market_price,net_debt,assets,equity,cash_equivalents,liabilities = cur.fetchone()
    print(dedent(f"""\
        {ticker} {name}
        P/E = {f'{market_price/net_profit:.2f}' if net_profit not in (0, None) and market_price is not None else None}
        P/S = {f'{market_price/sales:.2f}' if sales not in (0, None) and market_price is not None else None}
        P/B = {f'{market_price/assets:.2f}' if assets not in (0, None) and market_price is not None else None}
        ND/EBITDA = {f'{net_debt / ebitda:.2f}' if ebitda not in (0, None) and net_debt is not None else None}
        ROE = {f'{net_profit / equity:.2f}' if equity not in (0, None) and net_profit is not None else None}
        ROA = {f'{net_profit / assets:.2f}' if assets not in (0, None) and net_profit is not None else None}
        L/A = {f'{liabilities / assets:.2f}' if assets not in (0, None) and liabilities is not None else None}
    """))

@back_to_main
def update_company():
    ticker, _ = get_from_user_ticker_name()
    if ticker is None:
        return
    financial_cols = get_cols_from_table('financial')
    financial_row:dict[str, float|None] = {col: None for col in financial_cols}
    financial_row['ticker'] = ticker
    for field in financial_cols[1:]:
        print(f"Enter {field.replace('_', ' ')} (in the format '987654321'):")
        financial_row[field] = float(input())
    update_financial_row(financial_row)
    print('Company updated successfully!')

@back_to_main
def delete_company():
    ticker, _ = get_from_user_ticker_name()
    if ticker is None:
        return
    cur.execute("""DELETE FROM companies WHERE ticker == ?""", (ticker,))
    cur.execute("""DELETE FROM financial WHERE ticker == ?""", (ticker,))
    print('Company deleted successfully!')

@back_to_main
def list_company():
    print('COMPANY LIST')
    for row in cur.execute("""SELECT * FROM companies ORDER BY ticker"""):
        print(f'{row["ticker"]} {row["name"]} {row["sector"]}')

@back_to_main
def list_top10_by(kind: str):
    top10s = {
        'nde': ('ND/EBITDA', 'net_debt/ebitda'),
        'roe': ('ROE', 'net_profit/equity'),
        'roa': ('ROA', 'net_profit/assets')
    }
    display, eq = top10s[kind]
    print(f'TICKER {display}')
    for row in cur.execute(f"""SELECT ticker, ROUND({eq}, 2) AS val FROM financial ORDER BY {eq} DESC LIMIT 10"""):
        print(f'{row["ticker"]} {row["val"]}')

menus = {
    'main': (
        (
            dedent("""
                MAIN MENU
                0 Exit
                1 CRUD operations
                2 Show top ten companies by criteria
            """)
        ),
        {
            '0': lambda: set_state('exit'),
            '1': lambda: set_state('crud'),
            '2': lambda: set_state('top-ten'),
        }
    ),
    'crud': (
        (
            dedent("""
                CRUD MENU
                0 Back
                1 Create a company
                2 Read a company
                3 Update a company
                4 Delete a company
                5 List all companies
            """)
        ),
        {
            '0': lambda: set_state('main'),
            '1': create_company,
            '2': read_company,
            '3': update_company,
            '4': delete_company,
            '5': list_company,
        }
    ),
    'top-ten': (
        (
            dedent("""
                TOP TEN MENU
                0 Back
                1 List by ND/EBITDA
                2 List by ROE
                3 List by ROA
            """)
        ),
        {
            '0': lambda: set_state('main'),
            '1': lambda: list_top10_by('nde'),
            '2': lambda: list_top10_by('roe'),
            '3': lambda: list_top10_by('roa'),
        }
    )
}

def do_init():
    cur.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                ticker TEXT primary_key,
                name TEXT,
                sector TEXT
            )
        """)
    cur.execute("""
            CREATE TABLE IF NOT EXISTS financial (
                ticker TEXT primary_key,
                ebitda REAL,
                sales REAL,
                net_profit REAL,
                market_price REAL,
                net_debt REAL,
                assets REAL,
                equity REAL,
                cash_equivalents REAL,
                liabilities REAL
            )
        """)

    with open('companies.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            insert_company_row(row)
    with open('financial.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row = {key: (value if value != '' else None) for key, value in row.items()}
            insert_financial_row(row)

    # print('Database created successfully!')

@back_to_main
def invalid_option():
    print('Invalid option!')

def main():
    init = os.path.isfile('investor.db')
    con = sqlite3.connect('investor.db')
    con.row_factory = sqlite3.Row
    con.autocommit = True
    global cur
    cur = con.cursor()

    if not init:
        do_init()

    print('Welcome to the Investor Program!')
    while state != 'exit':
        menu_text, menu = menus[state]
        print(menu_text)
        menu.get(input('Enter an option:\n'), invalid_option)()

    print('Have a nice day!')
    # os.remove('investor.db')

if __name__ == '__main__':
    main()