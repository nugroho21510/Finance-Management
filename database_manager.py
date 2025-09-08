import sqlite3
from datetime import datetime

DATABASE = 'finance.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Create accounts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            balance REAL NOT NULL DEFAULT 0,
            is_virtual BOOLEAN NOT NULL DEFAULT 0
        )
    ''')
    
    # Create transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            type TEXT NOT NULL, -- 'Pemasukan', 'Pengeluaran', 'Transfer'
            account_id INTEGER,
            amount REAL NOT NULL,
            category TEXT,
            description TEXT,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    ''')
    
    # Check if accounts exist, if not, populate them
    cursor.execute("SELECT COUNT(*) FROM accounts")
    if cursor.fetchone()[0] == 0:
        initial_accounts = [
            ('BRI', 0, 0), ('BTN', 0, 0), ('Dana', 0, 0), 
            ('GoPay', 0, 0), ('Tunai', 0, 0),
            ('Sedekah', 0, 1), ('Tabungan', 0, 1)
        ]
        cursor.executemany("INSERT INTO accounts (name, balance, is_virtual) VALUES (?, ?, ?)", initial_accounts)
        
    conn.commit()
    conn.close()

def get_accounts():
    conn = get_db()
    accounts = conn.execute("SELECT * FROM accounts ORDER BY is_virtual, id").fetchall()
    conn.close()
    return accounts

def add_transaction(trans_type, account_id, amount, category, description):
    conn = get_db()
    cursor = conn.cursor()
    
    # Add transaction record
    cursor.execute(
        "INSERT INTO transactions (type, account_id, amount, category, description) VALUES (?, ?, ?, ?, ?)",
        (trans_type, account_id, amount, category, description)
    )
    
    # Update account balance
    if trans_type == 'Pemasukan':
        cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
    elif trans_type == 'Pengeluaran':
        cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
        
    conn.commit()
    conn.close()

def add_transfer(from_account_id, to_account_id, amount, category, description):
    conn = get_db()
    cursor = conn.cursor()
    
    # Add transfer record as two transactions
    desc_from = f"Transfer ke {dict(cursor.execute('SELECT name FROM accounts WHERE id = ?', (to_account_id,)).fetchone())['name']}: {description}"
    cursor.execute(
        "INSERT INTO transactions (type, account_id, amount, category, description) VALUES (?, ?, ?, ?, ?)",
        ('Pengeluaran', from_account_id, amount, category, desc_from)
    )
    
    desc_to = f"Transfer dari {dict(cursor.execute('SELECT name FROM accounts WHERE id = ?', (from_account_id,)).fetchone())['name']}: {description}"
    cursor.execute(
        "INSERT INTO transactions (type, account_id, amount, category, description) VALUES (?, ?, ?, ?, ?)",
        ('Pemasukan', to_account_id, amount, category, desc_to)
    )
    
    # Update balances
    cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_account_id))
    cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account_id))

    conn.commit()
    conn.close()

def get_all_transactions(limit=20):
    conn = get_db()
    transactions = conn.execute('''
        SELECT t.timestamp, t.type, a.name as account_name, t.amount, t.category, t.description
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        ORDER BY t.timestamp DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    return transactions

def get_daily_summary(month, year):
    conn = get_db()
    summary = conn.execute('''
        SELECT 
            strftime('%d', timestamp) as day,
            SUM(CASE WHEN type = 'Pemasukan' THEN amount ELSE 0 END) as total_pemasukan,
            SUM(CASE WHEN type = 'Pengeluaran' THEN amount ELSE 0 END) as total_pengeluaran
        FROM transactions
        WHERE strftime('%Y-%m', timestamp) = ?
        GROUP BY day
        ORDER BY day
    ''', (f"{year}-{month:02}",)).fetchall()
    conn.close()
    return summary

def get_activity_for_date(date_str):
    conn = get_db()
    # Check for transfer to Sedekah (id=6)
    sedekah_done = conn.execute('''
        SELECT 1 FROM transactions 
        WHERE date(timestamp) = ? AND category = 'Sedekah' AND type = 'Pemasukan' AND account_id = 6
        LIMIT 1
    ''', (date_str,)).fetchone()

    # Check for transfer to Tabungan (id=7)
    tabungan_done = conn.execute('''
        SELECT 1 FROM transactions 
        WHERE date(timestamp) = ? AND category = 'Menabung' AND type = 'Pemasukan' AND account_id = 7
        LIMIT 1
    ''', (date_str,)).fetchone()
    
    # Check for any other transaction
    other_transaction = conn.execute('''
        SELECT 1 FROM transactions 
        WHERE date(timestamp) = ?
        LIMIT 1
    ''', (date_str,)).fetchone()

    conn.close()
    
    return bool(sedekah_done), bool(tabungan_done), bool(other_transaction)
