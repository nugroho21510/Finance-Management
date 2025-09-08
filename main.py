from flask import Flask, render_template, request, redirect, url_for, flash
import database_manager as db
from datetime import datetime
import calendar

app = Flask(__name__)
app.secret_key = 'supersecretkey' # Needed for flash messages

# Initialize database on startup
db.init_db()

@app.route('/')
def index():
    accounts = db.get_accounts()
    transactions = db.get_all_transactions()
    
    # Data for Chart
    now = datetime.now()
    daily_summary = db.get_daily_summary(now.month, now.year)
    chart_labels = [f"{item['day']}" for item in daily_summary]
    pemasukan_data = [item['total_pemasukan'] for item in daily_summary]
    pengeluaran_data = [item['total_pengeluaran'] for item in daily_summary]
    
    chart_data = {
        'labels': chart_labels,
        'pemasukan': pemasukan_data,
        'pengeluaran': pengeluaran_data
    }
    
    # Data for Calendar
    cal = calendar.Calendar()
    month_days = cal.itermonthdates(now.year, now.month)
    calendar_data = []
    for day in month_days:
        color = 'none'
        if day.month == now.month:
            date_str = day.strftime("%Y-%m-%d")
            sedekah, tabungan, other = db.get_activity_for_date(date_str)
            if sedekah and tabungan:
                color = 'green'
            elif sedekah:
                color = 'blue'
            elif tabungan:
                color = 'yellow'
            elif other:
                color = 'red'
        calendar_data.append({'day': day, 'color': color})
        
    return render_template('index.html', accounts=accounts, transactions=transactions, chart_data=chart_data, calendar_data=calendar_data, today=now)

@app.route('/quick_action', methods=['POST'])
def quick_action():
    action = request.form.get('action')
    source_account_id = request.form.get('source_account')
    
    if action == 'kip':
        # BTN account ID is 2
        db.add_transaction('Pemasukan', 2, 5700000, 'Pencairan KIP', 'Pencairan dana KIP otomatis')
        flash('Pencairan KIP Rp 5.700.000 ke BTN berhasil!')
    elif action == 'sedekah':
        # Sedekah virtual account ID is 6
        db.add_transfer(source_account_id, 6, 1000, 'Sedekah', 'Sedekah via Aksi Cepat')
        flash('Sedekah Rp 1.000 berhasil!')
    elif action == 'menabung':
        # Tabungan virtual account ID is 7
        db.add_transfer(source_account_id, 7, 5000, 'Menabung', 'Menabung via Aksi Cepat')
        flash('Menabung Rp 5.000 berhasil!')
        
    return redirect(url_for('index'))

@app.route('/add_transaction', methods=['POST'])
def add_transaction_route():
    trans_type = request.form.get('type')
    account_id = request.form.get('account')
    amount = float(request.form.get('amount'))
    category = request.form.get('category')
    description = request.form.get('description')
    
    # Handle transfers to virtual accounts
    if category.lower() in ['sedekah', 'menabung']:
        to_account_map = {'sedekah': 6, 'menabung': 7}
        to_account_id = to_account_map[category.lower()]
        db.add_transfer(account_id, to_account_id, amount, category.capitalize(), description)
        flash(f'Transfer untuk {category.capitalize()} sebesar Rp {amount:,.0f} berhasil!')
    else:
        db.add_transaction(trans_type, account_id, amount, category, description)
        flash(f'{trans_type} sebesar Rp {amount:,.0f} berhasil ditambahkan!')
        
    return redirect(url_for('index'))
