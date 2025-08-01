from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import calendar
import json
import os

USERS_FILE = 'users.json'

def load_users():
    global users
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            users.update(json.load(f))

def save_users():
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

app = Flask(__name__)
app.secret_key = 'supersecretkey'

users = {}
users_cycle_data = {}

load_users()

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/home')
def home():
    if 'username' in session:
        username = session['username']
        return render_template('home.html', username=username)
    else:
        flash('Please log in first.')
        return redirect(url_for('welcome'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users:
            flash('Username already exists.')
            return redirect(url_for('register'))

        users[username] = generate_password_hash(password)
        save_users()
        session['username'] = username
        flash('Account created! Welcome, ' + username)
        return redirect(url_for('home'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_hash = users.get(username)
        if user_hash and check_password_hash(user_hash, password):
            session['username'] = username
            flash('Logged in successfully! Welcome, ' + username)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.')
    return redirect(url_for('welcome'))

@app.route('/log-date', methods=['GET', 'POST'])
def date_log():
    if 'username' not in session:
        flash('Please log in first.')
        return redirect(url_for('welcome'))

    username = session['username']
    user_data = users_cycle_data.get(username, [])

    if request.method == 'POST':
        #Add new logged date
        date_str = request.form['date']
        symptom = request.form.get('symptom', '').strip()

        try:
            datetime.strptime(date_str, '%m/%d/%Y')
        except ValueError:
            flash('Invalid date format. Use MM/DD/YYYY.')
            return redirect(url_for('date_log'))

        user_data.append({'date': date_str, 'symptom': symptom})
        users_cycle_data[username] = user_data
        flash('Date and symptom logged!')

        return redirect(url_for('date_log'))

    if user_data:
        dates = [datetime.strptime(entry['date'], '%m/%d/%Y') for entry in user_data]
        start_date = min(dates).strftime('%m/%d/%Y')
        end_date = max(dates).strftime('%m/%d/%Y')
    else:
        start_date = None
        end_date = None

    return render_template('log-date.html',
                           logs=user_data,
                           start_date=start_date,
                           end_date=end_date)


@app.route('/edit_log/<int:index>', methods=['GET', 'POST'])
def edit_log(index):
    if 'username' not in session:
        flash('Please log in first.')
        return redirect(url_for('welcome'))

    username = session['username']
    user_data = users_cycle_data.get(username, [])

    if index < 0 or index >= len(user_data):
        flash("Invalid log entry.")
        return redirect(url_for('date_log'))

    entry = user_data[index]

    if request.method == 'POST':
        date_str = request.form['date']
        symptom = request.form.get('symptom', '').strip()

        try:
            datetime.strptime(date_str, '%m/%d/%Y')
        except ValueError:
            flash('Invalid date format. Use MM/DD/YYYY.')
            return redirect(url_for('edit_log', index=index))

        entry['date'] = date_str
        entry['symptom'] = symptom
        users_cycle_data[username] = user_data
        flash('Log entry updated.')
        return redirect(url_for('date_log'))

    return render_template('edit-log.html', entry=entry)


@app.route('/remove_log/<int:index>', methods=['POST'])
def remove_log(index):
    if 'username' not in session:
        flash('Please log in first.')
        return redirect(url_for('welcome'))

    username = session['username']
    user_data = users_cycle_data.get(username, [])

    if 0 <= index < len(user_data):
        removed = user_data.pop(index)
        users_cycle_data[username] = user_data
        flash(f"Removed log for {removed['date']}.")
    else:
        flash("Invalid log entry.")

    return redirect(url_for('date_log'))


@app.route('/remove_logs', methods=['POST'])
def remove_logs():
    if 'username' not in session:
        flash('Please log in first.')
        return redirect(url_for('welcome'))

    username = session['username']
    users_cycle_data[username] = []
    flash('All logged dates for the current cycle have been removed.')
    return redirect(url_for('date_log'))

@app.route('/calendar', methods=['GET', 'POST'])
def calendar_page():
    if 'username' not in session:
        flash('Please log in first.')
        return redirect(url_for('welcome'))

    username = session['username']
    user_data = users_cycle_data.get(username, [])
    global notes_data
    if 'notes_data' not in globals():
        notes_data = {}

    if request.method == 'POST':
        #Save note
        note = request.form.get('note')
        if note is not None:
            notes_data[username] = note
            flash('Note saved!')
            return redirect(url_for('calendar_page'))

        #Add Date on Calendar page
        new_date = request.form.get('new_date')
        if new_date:
            try:
                datetime.strptime(new_date, '%m/%d/%Y')
                new_symptom = request.form.get('new_symptom', '').strip()
                user_data.append({'date': new_date, 'symptom': new_symptom})
                users_cycle_data[username] = user_data
                flash('Date logged from calendar!')
                return redirect(url_for('calendar_page'))
            except ValueError:
                flash('Invalid date format. Use MM/DD/YYYY.')

    today = datetime.today()
    current_year = today.year
    current_month = today.month

    logged_dates = set()
    for entry in user_data:
        try:
            dt = datetime.strptime(entry['date'], '%m/%d/%Y').date()
            logged_dates.add(dt)
        except:
            pass

    def get_month_calendar(year, month):
        cal = calendar.monthcalendar(year, month)
        month_days = []
        for week in cal:
            week_days = []
            for day in week:
                day_date = None
                if day != 0:
                    day_date = datetime(year, month, day).date()
                week_days.append({
                    'day': day,
                    'is_logged': day_date in logged_dates if day_date else False
                })
            month_days.append(week_days)
        return month_days

    current_cal = get_month_calendar(current_year, current_month)

    mini_cals = []
    for i in range(1, 4):
        next_month_date = today.replace(day=1) + timedelta(days=31 * i)
        y, m = next_month_date.year, next_month_date.month
        mini_cals.append({
            'year': y,
            'month': m,
            'name': calendar.month_name[m],
            'calendar': get_month_calendar(y, m)
        })

    return render_template('calendar.html',
                           current_year=current_year,
                           current_month=current_month,
                           current_month_name=calendar.month_name[current_month],
                           current_cal=current_cal,
                           mini_cals=mini_cals,
                           notes=notes_data.get(username, ""))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
