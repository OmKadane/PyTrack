import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkcalendar import DateEntry
from PIL import Image, ImageTk
from datetime import datetime
import os
import sqlite3
import csv
import matplotlib
# Set the backend before importing pyplot to prevent GUI conflicts
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import threading
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import getpass

# ==============================================================================
# SECTION 1: CORE EXPENSE TRACKER LOGIC
# ==============================================================================

def connect_db():
    """Establishes a connection to the SQLite database."""
    if not os.path.exists('data'):
        os.makedirs('data')
    conn = sqlite3.connect('data/expenses.db')
    return conn

def initialize_db():
    """Initializes the database with the necessary tables if they don't exist."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            note TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            name TEXT PRIMARY KEY
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            month TEXT PRIMARY KEY,
            goal REAL NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    # Set default currency if not present
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('currency_symbol', '$')")
    
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        default_categories = ['Food', 'Travel', 'Shopping', 'Bills', 'Misc']
        cursor.executemany("INSERT INTO categories (name) VALUES (?)", [(cat,) for cat in default_categories])
    conn.commit()
    conn.close()

def get_setting(key):
    """Retrieves a setting value from the database."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def update_setting(key, value):
    """Updates a setting in the database."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def add_expense(date_str, amount, category, note):
    """Adds a new expense to the database."""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        if float(amount) <= 0:
            raise ValueError("Amount must be a positive number.")
    except ValueError as e:
        print(f"Error: Invalid input. {e}")
        return False
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO expenses (date, amount, category, note) VALUES (?, ?, ?, ?)",
                   (date_str, amount, category, note))
    conn.commit()
    conn.close()
    return True

def get_all_expenses():
    """Retrieves all expenses from the database, ordered by date."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, date, amount, category, note FROM expenses ORDER BY date DESC")
    expenses = cursor.fetchall()
    conn.close()
    return expenses

def delete_expense(expense_id):
    """Deletes an expense from the database by its ID."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def get_categories():
    """Retrieves all expense categories from the database."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories ORDER BY name")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories

def add_category(category_name):
    """Adds a new category to the database."""
    if not category_name.strip():
        return False, "Category name cannot be empty."
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
        conn.commit()
        return True, f"Category '{category_name}' added successfully."
    except sqlite3.IntegrityError:
        return False, f"Error: Category '{category_name}' already exists."
    finally:
        conn.close()

def set_monthly_goal(month_str, goal_amount):
    """Sets or updates the spending goal for a specific month (YYYY-MM)."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO goals (month, goal) VALUES (?, ?)", (month_str, goal_amount))
    conn.commit()
    conn.close()

def get_monthly_goal(month_str):
    """Retrieves the spending goal for a specific month (YYYY-MM)."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT goal FROM goals WHERE month = ?", (month_str,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0.0

def get_total_expenses_for_month(month_str):
    """Calculates the total expenses for a specific month (YYYY-MM)."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount) FROM expenses WHERE strftime('%Y-%m', date) = ?", (month_str,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result[0] is not None else 0.0

def send_summary_email(sender_email, password, recipient_email, plot_path):
    """Sends a summary email with the category breakdown plot."""
    currency_symbol = get_setting('currency_symbol')
    current_month_str = datetime.now().strftime('%Y-%m')
    total_expenses = get_total_expenses_for_month(current_month_str)

    if not plot_path:
        return False, "Could not generate the plot for the email."

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"Your Expense Summary for {current_month_str}"

    body = f"""
    <html><body>
        <h2>Expense Summary for {current_month_str}</h2>
        <p>Hello,</p>
        <p>Here is your expense summary for this month.</p>
        <p><b>Total Expenses: {currency_symbol}{total_expenses:,.2f}</b></p>
        <p>Please find the category-wise breakdown chart attached.</p>
        <p>Regards,<br>PyTrack</p>
    </body></html>
    """
    msg.attach(MIMEText(body, 'html'))

    try:
        with open(plot_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename= {os.path.basename(plot_path)}")
        msg.attach(part)
    except FileNotFoundError:
        return False, "Attachment file not found."

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        return True, "Email sent successfully!"
    except Exception as e:
        return False, f"Failed to send email: {e}"
        
def get_expenses_in_date_range(start_date, end_date):
    """Retrieves expenses within a specific date range."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT date, amount, category, note FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date",
                   (start_date, end_date))
    expenses = cursor.fetchall()
    conn.close()
    return expenses

def get_category_breakdown():
    """Calculates the total expense for each category."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT category, SUM(amount) FROM expenses GROUP BY category ORDER BY SUM(amount) DESC')
    breakdown = cursor.fetchall()
    conn.close()
    return breakdown

def get_highest_expense_current_month():
    """Finds the single highest expense in the current month."""
    current_month = datetime.now().strftime('%Y-%m')
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT date, amount, category, note FROM expenses
        WHERE strftime('%Y-%m', date) = ?
        ORDER BY amount DESC LIMIT 1
    ''', (current_month,))
    expense = cursor.fetchone()
    conn.close()
    return expense

def get_average_daily_expense():
    """Calculates the average daily expense."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT AVG(daily_total) FROM (SELECT SUM(amount) as daily_total FROM expenses GROUP BY date)')
    average = cursor.fetchone()[0]
    conn.close()
    return average if average else 0.0

def plot_and_save_breakdown(breakdown, currency_symbol='$'):
    """Generates and saves a bar chart from breakdown data. Must be run in the main thread."""
    if not breakdown:
        print("No expense data to plot.")
        return None
    if not os.path.exists('reports'):
        os.makedirs('reports')
    filepath = os.path.join('reports', 'category_breakdown.png')
    
    categories = [item[0] for item in breakdown]
    amounts = [item[1] for item in breakdown]
    
    plt.figure(figsize=(10, 6))
    plt.bar(categories, amounts, color='skyblue')
    plt.xlabel('Category')
    plt.ylabel(f'Total Amount ({currency_symbol})')
    plt.title('Expense Breakdown by Category')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(filepath)
    plt.close()
    print(f"Chart saved to {filepath}")
    return filepath

# ==============================================================================
# SECTION 2: TKINTER GUI
# ==============================================================================

class EmailCredentialDialog(simpledialog.Dialog):
    """A dialog for securely entering email credentials."""
    def body(self, master):
        self.title("Email Credentials")
        tk.Label(master, text="Sender Email:").grid(row=0, sticky="w")
        tk.Label(master, text="App Password:").grid(row=1, sticky="w")
        tk.Label(master, text="Recipient Email:").grid(row=2, sticky="w")
        
        self.sender_entry = tk.Entry(master, width=30)
        self.password_entry = tk.Entry(master, show="*", width=30)
        self.recipient_entry = tk.Entry(master, width=30)
        
        self.sender_entry.grid(row=0, column=1, padx=5, pady=5)
        self.password_entry.grid(row=1, column=1, padx=5, pady=5)
        self.recipient_entry.grid(row=2, column=1, padx=5, pady=5)
        return self.sender_entry

    def apply(self):
        self.result = (self.sender_entry.get(), self.password_entry.get(), self.recipient_entry.get())

class ExpenseTrackerApp(tk.Tk):
    """The main application class for the Tkinter GUI."""
    def __init__(self):
        super().__init__()
        self.currency_symbol = get_setting('currency_symbol')
        self.title("PyTrack")
        self.geometry("1150x850")
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.init_ui_styles()
        self.init_ui()

    def init_ui_styles(self):
        """Configure styles for the UI elements."""
        self.style.configure("TButton", padding=6, relief="flat", background="#cce7ff")
        self.style.configure("Treeview", rowheight=25)
        self.style.map("TButton", background=[('active', '#b3d9ff')])
        self.style.configure("Red.Horizontal.TProgressbar", background='red')
        self.style.configure("Green.Horizontal.TProgressbar", background='green')
        self.style.configure("Orange.Horizontal.TProgressbar", background='orange')

    def init_ui(self):
        """Initializes the user interface components."""
        # Add welcome label at the top
        self.title_label = tk.Label(self, text="Welcome to PyTrack - Your Smart Expense Tracker", font=("Arial", 20))
        self.title_label.pack(pady=10)

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(main_frame)
        left_panel.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="nsew")

        input_frame = ttk.LabelFrame(left_panel, text="Log an Expense", padding="10")
        input_frame.pack(fill=tk.X, expand=True)
        ttk.Label(input_frame, text="Date:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.date_entry = DateEntry(input_frame, width=15, date_pattern='y-mm-dd')
        self.date_entry.grid(row=0, column=1, sticky="ew", pady=3)
        ttk.Label(input_frame, text="Amount:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.amount_entry = ttk.Entry(input_frame)
        self.amount_entry.grid(row=1, column=1, sticky="ew", pady=3)
        ttk.Label(input_frame, text="Category:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.category_combobox = ttk.Combobox(input_frame, state="readonly")
        self.category_combobox.grid(row=2, column=1, sticky="ew", pady=3)
        self.load_categories()
        ttk.Label(input_frame, text="Note:").grid(row=3, column=0, sticky=tk.W, pady=3)
        self.note_entry = ttk.Entry(input_frame)
        self.note_entry.grid(row=3, column=1, sticky="ew", pady=3)
        input_frame.columnconfigure(1, weight=1)
        add_btn = ttk.Button(input_frame, text="Add Expense", command=self.start_add_expense_thread)
        add_btn.grid(row=4, column=0, columnspan=2, pady=10)

        goal_frame = ttk.LabelFrame(left_panel, text="Monthly Goal", padding="10")
        goal_frame.pack(fill=tk.X, expand=True, pady=10)
        self.goal_label = ttk.Label(goal_frame, text=f"Goal: {self.currency_symbol}0.00 | Spent: {self.currency_symbol}0.00")
        self.goal_label.pack()
        self.goal_progress = ttk.Progressbar(goal_frame, orient='horizontal', length=200, mode='determinate')
        self.goal_progress.pack(pady=5, fill=tk.X)
        self.budget_status_label = ttk.Label(goal_frame, text="Set a goal to see your status.")
        self.budget_status_label.pack()
        set_goal_btn = ttk.Button(goal_frame, text="Set Monthly Goal", command=self.set_goal_gui)
        set_goal_btn.pack(pady=5)
        self.update_goal_display()

        report_frame = ttk.LabelFrame(left_panel, text="Reports & Actions", padding="10")
        report_frame.pack(fill=tk.X, expand=True)
        plot_btn = ttk.Button(report_frame, text="Show Category Breakdown Plot", command=self.start_plot_thread)
        plot_btn.pack(pady=5, fill=tk.X)
        email_btn = ttk.Button(report_frame, text="Send Email Summary", command=self.email_summary_gui)
        email_btn.pack(pady=5, fill=tk.X)
        currency_btn = ttk.Button(report_frame, text="Change Currency", command=self.change_currency_gui)
        currency_btn.pack(pady=5, fill=tk.X)

        display_frame = ttk.LabelFrame(main_frame, text="Recent Expenses", padding="10")
        display_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        main_frame.columnconfigure(1, weight=3)
        main_frame.rowconfigure(0, weight=1)
        cols = ('ID', 'Date', 'Amount', 'Category', 'Note')
        self.tree = ttk.Treeview(display_frame, columns=cols, show='headings', height=20)
        for col in cols: self.tree.heading(col, text=col)
        self.tree.column("ID", width=40, anchor=tk.CENTER)
        self.tree.column("Amount", width=100, anchor=tk.E)
        scrollbar = ttk.Scrollbar(display_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        delete_btn = ttk.Button(display_frame, text="Delete Selected Expense", command=self.start_delete_expense_thread)
        delete_btn.pack()

        self.load_expenses()

    def load_categories(self):
        self.category_combobox['values'] = get_categories()
        if self.category_combobox['values']: self.category_combobox.current(0)

    def load_expenses(self):
        self.tree.heading('Amount', text=f'Amount ({self.currency_symbol})')
        for item in self.tree.get_children(): self.tree.delete(item)
        for exp in get_all_expenses():
            formatted_amount = f"{self.currency_symbol}{exp[2]:,.2f}"
            self.tree.insert("", "end", values=(exp[0], exp[1], formatted_amount, exp[3], exp[4]))
        self.update_goal_display()

    def update_goal_display(self):
        month_str = datetime.now().strftime('%Y-%m')
        goal = get_monthly_goal(month_str)
        spent = get_total_expenses_for_month(month_str)
        
        self.goal_label.config(text=f"Goal: {self.currency_symbol}{goal:,.2f} | Spent: {self.currency_symbol}{spent:,.2f}")
        
        if goal > 0:
            percentage = (spent / goal) * 100
            self.goal_progress['value'] = percentage
            if percentage > 100:
                self.budget_status_label.config(text="Status: Over Budget!", foreground="red")
                self.goal_progress.config(style="Red.Horizontal.TProgressbar")
            elif percentage > 85:
                self.budget_status_label.config(text="Status: Nearing Budget", foreground="orange")
                self.goal_progress.config(style="Orange.Horizontal.TProgressbar")
            else:
                self.budget_status_label.config(text="Status: On Track", foreground="green")
                self.goal_progress.config(style="Green.Horizontal.TProgressbar")
        else:
            self.goal_progress['value'] = 0
            self.budget_status_label.config(text="Set a goal to see your status.", foreground="black")

    def set_goal_gui(self):
        month_str = datetime.now().strftime('%Y-%m')
        current_goal = get_monthly_goal(month_str)
        new_goal = simpledialog.askfloat("Set Goal", f"Enter your spending goal for {month_str}:",
                                         initialvalue=current_goal, minvalue=0)
        if new_goal is not None:
            set_monthly_goal(month_str, new_goal)
            self.update_goal_display()
            
    def change_currency_gui(self):
        new_symbol = simpledialog.askstring("Change Currency", "Enter the new currency symbol:",
                                            initialvalue=self.currency_symbol)
        if new_symbol:
            self.currency_symbol = new_symbol
            update_setting('currency_symbol', new_symbol)
            self.load_expenses() # This will refresh all displays

    def start_add_expense_thread(self):
        date, amount_str, category, note = self.date_entry.get(), self.amount_entry.get(), self.category_combobox.get(), self.note_entry.get()
        if not amount_str or not category:
            messagebox.showerror("Error", "Amount and Category are required.")
            return
        try:
            amount = float(amount_str)
            if amount <= 0:
                messagebox.showerror("Error", "Amount must be a positive number.")
                return
        except ValueError:
            messagebox.showerror("Error", "Invalid amount. Please enter a number.")
            return
        threading.Thread(target=self.worker_add_expense, args=(date, amount, category, note), daemon=True).start()

    def worker_add_expense(self, date, amount, category, note):
        success = add_expense(date, amount, category, note)
        self.after(0, self.finish_add_expense, success)

    def finish_add_expense(self, success):
        if success:
            messagebox.showinfo("Success", "Expense added successfully.")
            self.clear_entries()
            self.load_expenses()
        else:
            messagebox.showerror("Error", "Failed to add expense.")
            
    def start_delete_expense_thread(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select an expense to delete.")
            return
        # In the GUI, the amount has the currency symbol, so we parse just the ID.
        expense_id = self.tree.item(selected_item[0])['values'][0]
        if messagebox.askyesno("Confirm Delete", f"Delete expense ID {expense_id}?"):
            threading.Thread(target=self.worker_delete_expense, args=(expense_id,), daemon=True).start()

    def worker_delete_expense(self, expense_id):
        success = delete_expense(expense_id)
        self.after(0, self.finish_delete_expense, success)

    def finish_delete_expense(self, success):
        if success:
            messagebox.showinfo("Success", "Expense deleted.")
            self.load_expenses()
        else:
            messagebox.showerror("Error", "Failed to delete expense.")

    def add_category_gui(self):
        new_cat = simpledialog.askstring("Add Category", "Enter new category name:", parent=self)
        if new_cat:
            success, message = add_category(new_cat.strip().title())
            (messagebox.showinfo if success else messagebox.showerror)("Status", message)
            if success: self.load_categories()

    def clear_entries(self):
        self.amount_entry.delete(0, tk.END)
        self.note_entry.delete(0, tk.END)
        self.date_entry.set_date(datetime.now())
        if self.category_combobox['values']: self.category_combobox.current(0)

    def email_summary_gui(self):
        dialog = EmailCredentialDialog(self)
        if dialog.result:
            sender, password, recipient = dialog.result
            if not all((sender, password, recipient)):
                messagebox.showerror("Error", "All fields are required.")
                return
            # Generate the plot in the main thread
            currency_symbol = get_setting('currency_symbol')
            breakdown_data = get_category_breakdown()
            plot_path = plot_and_save_breakdown(breakdown_data, currency_symbol)
            if not plot_path:
                messagebox.showerror("Error", "Could not generate the plot for the email.")
                return
            messagebox.showinfo("Sending", "Sending email in the background...")
            threading.Thread(target=self.worker_send_email, args=(sender, password, recipient, plot_path), daemon=True).start()

    def worker_send_email(self, sender, password, recipient, plot_path):
        success, message = send_summary_email(sender, password, recipient, plot_path)
        self.after(0, lambda: messagebox.showinfo("Email Status", message))

    def start_plot_thread(self):
        messagebox.showinfo("Generating Plot", "Fetching data...")
        threading.Thread(target=self.worker_fetch_breakdown_data, daemon=True).start()
        
    def worker_fetch_breakdown_data(self):
        breakdown_data = get_category_breakdown()
        self.after(0, self.finish_plot_generation, breakdown_data)

    def finish_plot_generation(self, breakdown_data):
        if not breakdown_data:
            messagebox.showinfo("Info", "No data to generate a plot.")
            return
        filepath = plot_and_save_breakdown(breakdown_data, self.currency_symbol)
        if filepath and os.path.exists(filepath):
            plot_window = tk.Toplevel(self)
            plot_window.title("Category Expense Breakdown")
            img = Image.open(filepath)
            photo = ImageTk.PhotoImage(img)
            img_label = tk.Label(plot_window, image=photo)
            img_label.image = photo
            img_label.pack()

def main_gui():
    app = ExpenseTrackerApp()
    app.mainloop()

# ==============================================================================
# SECTION 3: COMMAND-LINE INTERFACE
# ==============================================================================

def print_header(title):
    """Prints a formatted header for the CLI."""
    print(f"\n{'='*40}\n{title:^40}\n{'='*40}")

def get_expense_input_cli():
    """Gets expense details from user input in the CLI."""
    date_str = input("Enter date (YYYY-MM-DD, default is today): ") or datetime.now().strftime('%Y-%m-%d')
    while True:
        try:
            amount = float(input("Enter amount: "))
            if amount > 0: break
            print("Amount must be positive.")
        except ValueError: print("Invalid amount. Please enter a number.")
    categories = get_categories()
    for i, category in enumerate(categories, 1): print(f"  {i}. {category}")
    while True:
        try:
            choice = int(input(f"Enter choice (1-{len(categories)}): "))
            if 1 <= choice <= len(categories):
                category = categories[choice - 1]
                break
            print("Invalid choice.")
        except ValueError: print("Please enter a number.")
    return date_str, amount, category, input("Enter a short note (optional): ")

def view_all_expenses_cli():
    """Displays all recorded expenses in the CLI."""
    currency_symbol = get_setting('currency_symbol')
    print_header("All Expenses")
    expenses = get_all_expenses()
    if not expenses:
        print("No expenses logged yet.")
        return
    print(f"{'ID':<5} {'Date':<12} {'Amount':<12} {'Category':<15} {'Note':<20}\n{'-'*70}")
    for exp in expenses: 
        print(f"{exp[0]:<5} {exp[1]:<12} {currency_symbol}{exp[2]:<11,.2f} {exp[3]:<15} {exp[4]:<20}")

def delete_expense_cli():
    """Handles deleting an expense via the CLI."""
    print_header("Delete an Expense")
    view_all_expenses_cli()
    expenses = get_all_expenses()
    if not expenses:
        return
    try:
        expense_id = int(input("\nEnter the ID of the expense to delete (or 0 to cancel): "))
        if expense_id == 0: return
        if delete_expense(expense_id):
            print(f"Expense with ID {expense_id} has been deleted.")
        else:
            print(f"Error: No expense found with ID {expense_id}.")
    except ValueError:
        print("Invalid ID. Please enter a number.")

def view_reports_cli():
    """Shows the reporting submenu for the CLI."""
    currency_symbol = get_setting('currency_symbol')
    while True:
        print_header("Reports Menu")
        print("1. Total expenses for a date range\n2. Category-wise expense breakdown\n3. Highest expense of current month\n4. Average daily expense\n5. Generate category plot\n6. Back to main menu")
        choice = input("Enter your choice: ")
        if choice == '1':
            start = input("Enter start date (YYYY-MM-DD): ")
            end = input("Enter end date (YYYY-MM-DD): ")
            expenses = get_expenses_in_date_range(start, end)
            total = sum(exp[1] for exp in expenses)
            print_header(f"Expenses from {start} to {end}")
            for exp in expenses: print(f"- {exp[0]}: {currency_symbol}{exp[1]:.2f} ({exp[2]})")
            print(f"\nTotal: {currency_symbol}{total:,.2f}")
        elif choice == '2':
            print_header("Category-wise Breakdown")
            for cat, total in get_category_breakdown(): print(f"- {cat}: {currency_symbol}{total:,.2f}")
        elif choice == '3':
            print_header("Highest Expense This Month")
            expense = get_highest_expense_current_month()
            if expense: print(f"Date: {expense[0]}, Amount: {currency_symbol}{expense[1]:,.2f}, Category: {expense[2]}, Note: {expense[3]}")
            else: print("No expenses recorded this month.")
        elif choice == '4':
            print_header("Average Daily Expense")
            print(f"Your average daily expense is {currency_symbol}{get_average_daily_expense():,.2f}")
        elif choice == '5':
            data = get_category_breakdown()
            plot_and_save_breakdown(data, currency_symbol)
        elif choice == '6': break
        else: print("Invalid choice.")

def manage_categories_cli():
    """Shows the category management submenu for the CLI."""
    while True:
        print_header("Manage Categories")
        print("Existing Categories:", ", ".join(get_categories()))
        print("\n1. Add a new category\n2. Back to main menu")
        choice = input("Enter your choice: ")
        if choice == '1':
            new_cat = input("Enter new category name: ").strip().title()
            if new_cat:
                success, message = add_category(new_cat)
                print(message)
            else: print("Category name cannot be empty.")
        elif choice == '2': break
        else: print("Invalid choice.")

def manage_goal_cli():
    """Handles setting and viewing the monthly goal via the CLI."""
    currency_symbol = get_setting('currency_symbol')
    print_header("Monthly Goal")
    month_str = datetime.now().strftime('%Y-%m')
    goal = get_monthly_goal(month_str)
    spent = get_total_expenses_for_month(month_str)
    print(f"Current month: {month_str}")
    print(f"Your goal is set to: {currency_symbol}{goal:,.2f}")
    print(f"You have spent: {currency_symbol}{spent:,.2f}")
    if goal > 0:
        remaining = goal - spent
        print(f"Remaining budget: {currency_symbol}{remaining:,.2f}" if remaining >= 0 else f"You are {currency_symbol}{-remaining:,.2f} over budget.")
    
    try:
        new_goal_str = input("\nEnter a new goal amount (or leave blank to keep current): ")
        if new_goal_str:
            new_goal = float(new_goal_str)
            if new_goal >= 0:
                set_monthly_goal(month_str, new_goal)
                print(f"Goal for {month_str} updated to {currency_symbol}{new_goal:,.2f}")
            else:
                print("Goal must be a positive number.")
    except ValueError:
        print("Invalid amount. Please enter a number.")
        
def manage_currency_cli():
    """Handles changing the currency via the CLI."""
    print_header("Change Currency")
    current_symbol = get_setting('currency_symbol')
    print(f"Your current currency symbol is: {current_symbol}")
    new_symbol = input("Enter the new currency symbol (or leave blank to cancel): ")
    if new_symbol:
        update_setting('currency_symbol', new_symbol)
        print(f"Currency symbol updated to: {new_symbol}")

def send_email_cli():
    """Handles sending an email summary via the CLI."""
    print_header("Send Email Summary")
    sender_email = input("Enter your sender email address: ")
    password = getpass.getpass("Enter your email app password: ")
    recipient_email = input("Enter the recipient's email address: ")

    if not all((sender_email, password, recipient_email)):
        print("\nAll fields are required. Aborting.")
        return

    print("\nSending email...")
    success, message = send_summary_email(sender_email, password, recipient_email)
    print(message)

def main_cli():
    """Displays the main menu for the CLI and handles user interaction."""
    print("\nWelcome to PyTrack - Your Smart Expense Tracker\n")
    while True:
        print_header("PyTrack: Main Menu")
        print("1. Add expense\n2. View all expenses\n3. View reports\n4. Manage categories\n5. Delete expense\n6. Manage monthly goal\n7. Change Currency\n8. Send Email Summary\n9. Exit")
        choice = input("Enter your choice: ")
        if choice == '1':
            if add_expense(*get_expense_input_cli()): print("\nExpense added successfully!")
        elif choice == '2': view_all_expenses_cli()
        elif choice == '3': view_reports_cli()
        elif choice == '4': manage_categories_cli()
        elif choice == '5': delete_expense_cli()
        elif choice == '6': manage_goal_cli()
        elif choice == '7': manage_currency_cli()
        elif choice == '8': send_email_cli()
        elif choice == '9': print("Exiting PyTrack...\nGoodbye!"); break
        else: print("Invalid choice.")

# ==============================================================================
# SECTION 4: MAIN LAUNCHER
# ==============================================================================

def main():
    """Main function to let the user choose the interface."""
    initialize_db()
    print("Welcome to PyTrack: Your Smart Expense Tracker\nWhich interface would you like to use?")
    print("1. Command-Line Interface (CLI)\n2. Graphical User Interface (GUI)")
    while True:
        choice = input("Enter your choice (1 or 2): ")
        if choice == '1': 
            main_cli()
            break
        elif choice == '2': 
            print("Launching GUI...")
            main_gui()
            break
        else: 
            print("Invalid choice. Please enter 1 or 2.")

# Start the application
if __name__ == "__main__":
    main()
    