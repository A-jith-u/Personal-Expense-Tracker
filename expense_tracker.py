import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, filedialog
import json
import os
from datetime import datetime
import csv
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import calendar
try:
    from tkcalendar import Calendar
except ImportError:
    print("Error: tkcalendar module not found. Please install it using 'pip install tkcalendar'")
    Calendar = None  # Set Calendar to None to avoid further errors if the module is not installed
import requests  # For currency conversion
from tkinter import PhotoImage

# ---------- Expense Class ----------
class Expense:
    def __init__(self, amount, category, description, date=None, payment_method="Cash", currency="INR"):
        self.amount = amount
        self.category = category
        self.description = description
        self.date = date if date else datetime.now().strftime("%Y-%m-%d")
        self.payment_method = payment_method
        self.currency = currency

    def to_dict(self):
        return {
            "amount": self.amount,
            "category": self.category,
            "description": self.description,
            "date": self.date,
            "payment_method": self.payment_method,
            "currency": self.currency
        }


# ---------- Tracker ----------
class ExpenseTracker:
    def __init__(self, username):
        self.username = username
        self.expenses = []
        self.filename = f"{username}_expenses.json"
        self.load_expenses()
        self.budgets = {}  # Category-wise monthly budgets
        self.load_budgets()

    def add_expense(self, expense):
        self.expenses.append(expense)
        self.save_expenses()
        self.check_budget(expense)

    def save_expenses(self):
        with open(self.filename, "w") as f:
            json.dump([e.to_dict() for e in self.expenses], f, indent=4)

    def load_expenses(self):
        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                data = json.load(f)
                self.expenses = [Expense(**e) for e in data]

    def get_summary(self, year=None, month=None):
        summary = {}
        filtered_expenses = self.filter_expenses(year, month)
        for exp in filtered_expenses:
            summary[exp.category] = summary.get(exp.category, 0) + exp.amount
        return summary

    def search_expenses(self, keyword):
        return [exp for exp in self.expenses if keyword.lower() in exp.description.lower() or keyword.lower() in exp.category.lower()]

    def filter_by_category(self, category):
        return [exp for exp in self.expenses if exp.category.lower() == category.lower()]

    def filter_by_date_range(self, start_date, end_date):
        return [exp for exp in self.expenses if start_date <= exp.date <= end_date]

    def delete_expense(self, date, category, amount, description):
        self.expenses = [
            exp
            for exp in self.expenses
            if not (
                exp.date == date
                and exp.category == category
                and exp.amount == amount
                and exp.description == description
            )
        ]
        self.save_expenses()

    # Budget Management
    def set_budget(self, category, amount):
        self.budgets[category] = amount
        self.save_budgets()

    def load_budgets(self):
        budget_file = f"{self.username}_budgets.json"
        if os.path.exists(budget_file):
            with open(budget_file, "r") as f:
                self.budgets = json.load(f)

    def save_budgets(self):
        budget_file = f"{self.username}_budgets.json"
        with open(budget_file, "w") as f:
            json.dump(self.budgets, f, indent=4)

    def check_budget(self, expense):
        category = expense.category
        if category in self.budgets:
            spent = sum(exp.amount for exp in self.filter_expenses(month=datetime.now().month, category=category))
            if spent > self.budgets[category]:
                messagebox.showwarning("Budget Alert", f"You have exceeded your budget for {category}!")

    # Recurring Expenses
    def add_recurring_expense(self, amount, category, description, day_of_month):
        today = datetime.now()
        if today.day <= day_of_month:
            target_date = today.replace(day=day_of_month).strftime("%Y-%m-%d")
        else:
            next_month = today.month % 12 + 1
            next_year = today.year + (1 if next_month == 1 else 0)
            target_date = today.replace(year=next_year, month=next_month, day=day_of_month).strftime("%Y-%m-%d")

        expense = Expense(amount, category, description, date=target_date)
        self.add_expense(expense)

    # Currency Conversion
    def convert_currency(self, amount, from_currency, to_currency="INR"):
        if from_currency == to_currency:
            return amount

        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        try:
            response = requests.get(url)
            data = response.json()
            rate = data["rates"][to_currency]
            return amount * rate
        except Exception as e:
            messagebox.showerror("Currency Conversion Error", str(e))
            return None

    def filter_expenses(self, year=None, month=None, category=None, payment_method=None):
        filtered = self.expenses
        if year:
            filtered = [exp for exp in filtered if datetime.strptime(exp.date, "%Y-%m-%d").year == year]
        if month:
            filtered = [exp for exp in filtered if datetime.strptime(exp.date, "%Y-%m-%d").month == month]
        if category:
            filtered = [exp for exp in filtered if exp.category == category]
        if payment_method:
            filtered = [exp for exp in filtered if exp.payment_method == payment_method]
        return filtered


# ---------- GUI ----------
class ExpenseApp:
    def __init__(self, root, tracker):
        self.root = root
        self.tracker = tracker
        self.root.title(f"Expense Tracker - {tracker.username}")

        # Load Images
        self.add_icon = self.load_image("add_icon.png")
        self.summary_icon = self.load_image("summary_icon.png")
        self.search_icon = self.load_image("search_icon.png")
        self.filter_icon = self.load_image("filter_icon.png")
        self.export_icon = self.load_image("export_icon.png")
        self.charts_icon = self.load_image("charts_icon.png")
        self.budget_icon = self.load_image("budget_icon.png")
        self.recurring_icon = self.load_image("recurring_icon.png")
        self.delete_icon = self.load_image("delete_icon.png")

        # Configure style
        self.style = ttk.Style()  # Initialize the style here
        self.style.configure("TButton", padding=5, relief="raised")
        self.style.configure("TLabel", padding=5)
        self.style.configure("TEntry", padding=5)
        self.style.configure("Treeview.Heading", padding=5)

        # Theme
        self.dark_mode = False
        self.apply_theme()

        # Menu Bar
        self.menu_bar = tk.Menu(root)
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Export to CSV", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit)
        self.menu_bar.add_cascade(label="File", menu=file_menu)

        settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        settings_menu.add_command(label="Toggle Dark/Light Mode", command=self.toggle_theme)
        self.menu_bar.add_cascade(label="Settings", menu=settings_menu)

        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)

        root.config(menu=self.menu_bar)

        # --- Notebook Widget ---
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Expenses Tab ---
        self.expenses_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.expenses_tab, text="Expenses")
        self.create_expenses_tab_content(self.expenses_tab)

        # --- Dashboard Tab ---
        self.dashboard_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.create_dashboard_tab_content(self.dashboard_tab)

    def create_expenses_tab_content(self, parent):
        # Input Frame
        input_frame = ttk.Frame(parent, padding=10)
        input_frame.grid(row=0, column=0, sticky="ew", columnspan=3)

        # Input fields
        ttk.Label(input_frame, text="Amount:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.amount_entry = ttk.Entry(input_frame)
        self.amount_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(input_frame, text="Category:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.category_entry = ttk.Entry(input_frame)
        self.category_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        ttk.Label(input_frame, text="Description:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.desc_entry = ttk.Entry(input_frame)
        self.desc_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(input_frame, text="Payment Method:").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.payment_method_combo = ttk.Combobox(input_frame, values=["Cash", "UPI", "Bank", "Credit Card"])
        self.payment_method_combo.grid(row=1, column=3, padx=5, pady=5, sticky="w")
        self.payment_method_combo.set("Cash")

        ttk.Label(input_frame, text="Currency:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.currency_entry = ttk.Entry(input_frame)
        self.currency_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.currency_entry.insert(0, "INR")  # Default currency

        # Buttons Frame
        buttons_frame = ttk.Frame(parent, padding=10)
        buttons_frame.grid(row=1, column=0, sticky="ew", columnspan=3)

        # Buttons with Icons
        ttk.Button(buttons_frame, text="Add Expense", command=self.add_expense, image=self.add_icon, compound=tk.LEFT).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Show Summary", command=self.show_summary, image=self.summary_icon, compound=tk.LEFT).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Search", command=self.search_expense, image=self.search_icon, compound=tk.LEFT).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Filter by Category", command=self.filter_category, image=self.filter_icon, compound=tk.LEFT).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Filter by Date", command=self.filter_date, image=self.filter_icon, compound=tk.LEFT).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Export to CSV", command=self.export_csv, image=self.export_icon, compound=tk.LEFT).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Show Charts", command=self.show_charts, image=self.charts_icon, compound=tk.LEFT).grid(row=0, column=3, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Set Budget", command=self.set_budget, image=self.budget_icon, compound=tk.LEFT).grid(row=1, column=3, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Add Recurring Expense", command=self.add_recurring_expense, image=self.recurring_icon, compound=tk.LEFT).grid(row=0, column=4, padx=5, pady=5)

        # Table Frame
        table_frame = ttk.Frame(parent, padding=10)
        table_frame.grid(row=2, column=0, sticky="nsew", columnspan=3)

        # Table
        self.tree = ttk.Treeview(
            table_frame, columns=("Date", "Category", "Amount", "Description", "Payment Method", "Currency"), show="headings"
        )
        for col in ("Date", "Category", "Amount", "Description", "Payment Method", "Currency"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)  # Adjust column width
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar
        self.scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Delete Button
        self.delete_button = ttk.Button(parent, text="Delete Expense", command=self.delete_selected_expense, image=self.delete_icon, compound=tk.LEFT)
        self.delete_button.grid(row=3, column=0, columnspan=3, pady=10)

        parent.grid_rowconfigure(2, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_columnconfigure(2, weight=1)

        self.update_table()

    def create_dashboard_tab_content(self, parent):
        # Dashboard Frame
        dashboard_frame = ttk.Frame(parent, padding=10)
        dashboard_frame.grid(row=0, column=0, columnspan=3, sticky="ew")

        # Dashboard Controls
        ttk.Label(dashboard_frame, text="Year:").grid(row=0, column=0, padx=5, pady=5)
        self.year_entry = ttk.Entry(dashboard_frame, width=5)
        self.year_entry.grid(row=0, column=1, padx=5, pady=5)
        self.year_entry.insert(0, str(datetime.now().year))

        ttk.Label(dashboard_frame, text="Month:").grid(row=0, column=2, padx=5, pady=5)
        self.month_combo = ttk.Combobox(dashboard_frame, values=["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"], width=3)
        self.month_combo.grid(row=0, column=3, padx=5, pady=5)

        ttk.Button(dashboard_frame, text="Update Dashboard", command=self.update_dashboard).grid(row=0, column=4, padx=5, pady=5)

        # Chart Frame (initially empty)
        self.chart_frame = ttk.Frame(parent, padding=10)
        self.chart_frame.grid(row=1, column=0, columnspan=3, sticky="nsew")

        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_columnconfigure(2, weight=1)

        self.update_dashboard()

    def add_expense(self):
        try:
            amount = float(self.amount_entry.get())
            category = self.category_entry.get()
            desc = self.desc_entry.get()
            payment_method = self.payment_method_combo.get()
            currency = self.currency_entry.get()

            expense = Expense(amount, category, desc, payment_method=payment_method, currency=currency)
            self.tracker.add_expense(expense)
            messagebox.showinfo("Success", "Expense added successfully!")
            self.update_table()
            self.update_dashboard()
        except ValueError:
            messagebox.showerror("Error", "Invalid amount entered!")

    def update_table(self, expenses=None):
        for row in self.tree.get_children():
            self.tree.delete(row)
        if expenses is None:
            expenses = self.tracker.expenses
        for exp in expenses:
            self.tree.insert("", "end", values=(exp.date, exp.category, exp.amount, exp.description, exp.payment_method, exp.currency))

    def show_summary(self):
        year = self.get_dashboard_year()
        month = self.get_dashboard_month()
        summary = self.tracker.get_summary(year, month)
        msg = "\n".join([f"{cat}: {amt}" for cat, amt in summary.items()])
        messagebox.showinfo("Summary", msg if msg else "No expenses recorded.")

    def search_expense(self):
        keyword = simpledialog.askstring("Search", "Enter keyword:")
        if keyword:
            results = self.tracker.search_expenses(keyword)
            self.update_table(results)

    def filter_category(self):
        category = simpledialog.askstring("Filter", "Enter category:")
        if category:
            results = self.tracker.filter_by_category(category)
            self.update_table(results)

    def filter_date(self):
        # Use Calendar popup for date selection
        if Calendar is None:
            messagebox.showerror("Error", "tkcalendar is not installed.")
            return

        def popup_calendar(entry):
            cal = Calendar(None, selectmode="day", date_pattern="yyyy-%m-%d")
            cal.popup()
            date = cal.selection_get()
            entry.delete(0, tk.END)
            entry.insert(0, date)

        filter_window = tk.Toplevel(self.root)
        filter_window.title("Date Filter")

        ttk.Label(filter_window, text="Start Date:").grid(row=0, column=0, padx=5, pady=5)
        start_date_entry = ttk.Entry(filter_window)
        start_date_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(filter_window, text="Choose Date", command=lambda: popup_calendar(start_date_entry)).grid(
            row=0, column=2, padx=5, pady=5
        )

        ttk.Label(filter_window, text="End Date:").grid(row=1, column=0, padx=5, pady=5)
        end_date_entry = ttk.Entry(filter_window)
        end_date_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(filter_window, text="Choose Date", command=lambda: popup_calendar(end_date_entry)).grid(
            row=1, column=2, padx=5, pady=5
        )

        def apply_filter():
            start = start_date_entry.get()
            end = end_date_entry.get()
            if start and end:
                results = self.tracker.filter_by_date_range(start, end)
                self.update_table(results)
            filter_window.destroy()

        ttk.Button(filter_window, text="Apply Filter", command=apply_filter).grid(row=2, column=0, columnspan=3, pady=10)

    def export_csv(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if filename:
            with open(filename, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Category", "Amount", "Description", "Payment Method", "Currency"])
                for exp in self.tracker.expenses:
                    writer.writerow([exp.date, exp.category, exp.amount, exp.description, exp.payment_method, exp.currency])
            messagebox.showinfo("Export", f"Expenses exported to {filename}")

    def show_charts(self):
        year = self.get_dashboard_year()
        month = self.get_dashboard_month()
        summary = self.tracker.get_summary(year, month)
        if not summary:
            messagebox.showwarning("Charts", "No expenses to display.")
            return

        chart_window = tk.Toplevel(self.root)
        chart_window.title("Expense Charts")

        # Pie Chart
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.pie(summary.values(), labels=summary.keys(), autopct="%1.1f%%")
        ax.set_title("Category-wise Expenses")

        canvas = FigureCanvasTkAgg(fig, master=chart_window)
        canvas.get_tk_widget().pack()
        canvas.draw()

        # Bar Chart
        fig2, ax2 = plt.subplots(figsize=(5, 4))
        categories = list(summary.keys())
        amounts = list(summary.values())
        ax2.bar(categories, amounts)
        ax2.set_title("Expenses by Category")
        ax2.set_xlabel("Category")
        ax2.set_ylabel("Amount")
        fig2.autofmt_xdate()  # Rotate category labels

        canvas2 = FigureCanvasTkAgg(fig2, master=chart_window)
        canvas2.get_tk_widget().pack()
        canvas2.draw()

        # Line Chart (Expenses over time)
        expenses_by_date = {}
        filtered_expenses = self.tracker.filter_expenses(year=year, month=month)
        for exp in filtered_expenses:
            date = exp.date
            expenses_by_date[date] = expenses_by_date.get(date, 0) + exp.amount

        dates = sorted(expenses_by_date.keys())
        amounts = [expenses_by_date[date] for date in dates]

        fig3, ax3 = plt.subplots(figsize=(5, 4))
        ax3.plot(dates, amounts)
        ax3.set_title("Expenses Over Time")
        ax3.set_xlabel("Date")
        ax3.set_ylabel("Amount")
        fig3.autofmt_xdate()

        canvas3 = FigureCanvasTkAgg(fig3, master=chart_window)
        canvas3.get_tk_widget().pack()
        canvas3.draw()

    def show_about(self):
        messagebox.showinfo("About", "Personal Expense Tracker\nVersion 1.0")

    def delete_selected_expense(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showinfo("Delete", "Please select an expense to delete.")
            return

        # Get values from the selected row
        date, category, amount, description, _, _ = self.tree.item(selected_item, "values")

        # Confirm deletion
        if messagebox.askyesno("Delete", "Are you sure you want to delete this expense?"):
            # Delete the expense from the tracker
            self.tracker.delete_expense(date, category, float(amount), description)
            # Update the table
            self.update_table()
            self.update_dashboard()
            messagebox.showinfo("Delete", "Expense deleted successfully.")

    def set_budget(self):
        category = simpledialog.askstring("Budget", "Enter category for budget:")
        if category:
            amount_str = simpledialog.askstring("Budget", f"Enter monthly budget for {category}:")
            try:
                amount = float(amount_str)
                self.tracker.set_budget(category, amount)
                messagebox.showinfo("Budget", f"Budget set for {category}: {amount}")
            except ValueError:
                messagebox.showerror("Error", "Invalid amount entered!")

    def add_recurring_expense(self):
        def add():
            try:
                amount = float(amount_entry.get())
                category = category_entry.get()
                description = desc_entry.get()
                day = int(day_entry.get())

                self.tracker.add_recurring_expense(amount, category, description, day)
                messagebox.showinfo("Success", "Recurring expense added!")
                recurring_window.destroy()
            except ValueError:
                messagebox.showerror("Error", "Invalid input!")

        recurring_window = tk.Toplevel(self.root)
        recurring_window.title("Add Recurring Expense")

        ttk.Label(recurring_window, text="Amount:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        amount_entry = ttk.Entry(recurring_window)
        amount_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(recurring_window, text="Category:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        category_entry = ttk.Entry(recurring_window)
        category_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(recurring_window, text="Description:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        desc_entry = ttk.Entry(recurring_window)
        desc_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(recurring_window, text="Day of Month:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        day_entry = ttk.Entry(recurring_window)
        day_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        ttk.Button(recurring_window, text="Add", command=add).grid(row=4, column=0, columnspan=2, pady=10)

    def update_dashboard(self):
        # Clear previous charts
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        year = self.get_dashboard_year()
        month = self.get_dashboard_month()

        summary = self.tracker.get_summary(year, month)
        expenses = self.tracker.filter_expenses(year, month)

        # --- Pie Chart ---
        if summary:
            fig_pie, ax_pie = plt.subplots(figsize=(4, 3))
            ax_pie.pie(summary.values(), labels=summary.keys(), autopct="%1.1f%%")
            ax_pie.set_title("Expenses by Category")
            canvas_pie = FigureCanvasTkAgg(fig_pie, master=self.chart_frame)
            canvas_pie.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            canvas_pie.draw()

        # --- Bar Chart (Expenses Over Time) ---
        expenses_by_date = {}
        for exp in expenses:
            date = exp.date
            expenses_by_date[date] = expenses_by_date.get(date, 0) + exp.amount

        dates = sorted(expenses_by_date.keys())
        amounts = [expenses_by_date[date] for date in dates]

        if dates:
            fig_bar, ax_bar = plt.subplots(figsize=(6, 3))  # Wider bar chart
            ax_bar.bar(dates, amounts)
            ax_bar.set_title("Expenses Over Time")
            ax_bar.set_xlabel("Date")
            ax_bar.set_ylabel("Amount")
            fig_bar.autofmt_xdate()  # Rotate date labels
            canvas_bar = FigureCanvasTkAgg(fig_bar, master=self.chart_frame)
            canvas_bar.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            canvas_bar.draw()

    def get_dashboard_year(self):
        try:
            return int(self.year_entry.get())
        except ValueError:
            return None

    def get_dashboard_month(self):
        month = self.month_combo.get()
        return int(month) if month else None

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

    def apply_theme(self):
        if self.dark_mode:
            self.root.configure(bg="gray12")
            self.style.configure(".", background="gray12", foreground="white")
            self.style.configure("TButton", background="gray24", foreground="white")
            self.style.configure("TLabel", background="gray12", foreground="white")
            self.style.configure("TEntry", background="gray18", foreground="white")
            self.style.configure("Treeview", background="gray18", foreground="white")
            self.style.configure("Treeview.Heading", background="gray24", foreground="white")
        else:
            self.root.configure(bg="SystemButtonFace")
            self.style.configure(".", background="SystemButtonFace", foreground="black")
            self.style.configure("TButton", background="SystemButtonFace", foreground="black")
            self.style.configure("TLabel", background="SystemButtonFace", foreground="black")
            self.style.configure("TEntry", background="white", foreground="black")
            self.style.configure("Treeview", background="white", foreground="black")
            self.style.configure("Treeview.Heading", background="SystemButtonFace", foreground="black")

    def load_image(self, filename):
        try:
            # Assuming images are in the same directory as the script
            filepath = os.path.join(os.path.dirname(__file__), filename)
            return PhotoImage(file=filepath)
        except tk.TclError as e:
            print(f"Error loading image {filename}: {e}")
            return None


# ---------- User Authentication ----------
def authenticate():
    users_file = "users.json"

    if os.path.exists(users_file):
        with open(users_file, "r") as f:
            users = json.load(f)
    else:
        users = {}

    root = tk.Tk()
    root.withdraw()
    action = simpledialog.askstring("Login/Register", "Type 'login' or 'register':")

    if action == "register":
        username = simpledialog.askstring("Register", "Enter username:")
        password = simpledialog.askstring("Register", "Enter password:", show="*")
        if username in users:
            messagebox.showerror("Error", "User already exists!")
            return None, None
        users[username] = password
        with open(users_file, "w") as f:
            json.dump(users, f, indent=4)
        messagebox.showinfo("Success", "User registered successfully!")
        return username, password

    elif action == "login":
        username = simpledialog.askstring("Login", "Enter username:")
        password = simpledialog.askstring("Login", "Enter password:", show="*")
        if username in users and users[username] == password:
            messagebox.showinfo("Success", "Login successful!")
            return username, password
        else:
            messagebox.showerror("Error", "Invalid credentials!")
            return None, None
    else:
        return None, None


# ---------- Main ----------
if __name__ == "__main__":
    username, password = authenticate()
    if username:
        root = tk.Tk()
        tracker = ExpenseTracker(username)
        app = ExpenseApp(root, tracker)
        root.mainloop()
