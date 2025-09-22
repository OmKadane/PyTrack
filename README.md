# 💰 PyTrack - Your Smart Expense Tracker

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white) 
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-red.svg) 
![SQLite](https://img.shields.io/badge/Database-SQLite-blue?logo=sqlite&logoColor=white) 
![Matplotlib](https://img.shields.io/badge/Plotting-Matplotlib-orange.svg) 
![SMTP](https://img.shields.io/badge/Email-SMTP-green?logo=gmail&logoColor=white)

PyTrack is a comprehensive desktop application designed to help you manage your personal finances with ease. It features both a user-friendly Graphical User Interface (GUI) and a powerful Command-Line Interface (CLI), ensuring a seamless experience for all types of users. Track expenses, set monthly budgets, and gain insights into your spending habits.

---

## ✨ Features

* 📊 **Dual Interface** – Choose between a feature-rich GUI built with Tkinter or a fast and efficient CLI.
* 💸 **Expense Management** – Easily add, view, and delete expenses with details like date, amount, category, and notes.
* 🎯 **Budget Tracking** – Set monthly spending goals and visualize your progress with a dynamic progress bar that shows your status (On Track, Nearing Budget, Over Budget).
* 📈 **Insightful Reports** – Generate detailed reports, including category-wise breakdowns, average daily spending, and your highest expense for the current month.
* 📧 **Email Summaries** – Send a monthly expense summary directly to your inbox, complete with an attached visual chart of your spending breakdown.
* 🎨 **Visual Charts** – Automatically generate and display bar charts for a clear visual representation of your expenses by category using Matplotlib.
* 🗃️ **Persistent Storage** – All data is securely stored locally in an SQLite database, ensuring your information is safe and always available.
* ⚙️ **Customization** – Personalize the app by managing your own spending categories and setting your preferred currency symbol.

---

## 🛠️ Technologies Used

- ***Python*** 3.10+ – Core programming language.
- ***Tkinter*** – For the Graphical User Interface (GUI).
- ***SQLite3*** – For the local database and data persistence.
- ***Matplotlib*** – For generating data visualizations and plots.
- ***tkcalendar*** – For the GUI's date selection widget.
- ***Pillow (PIL)*** – For displaying generated plots within the Tkinter UI.
- ***smtplib*** & ***email.mime*** – For sending structured summary emails.
- ***threading*** – To ensure the GUI remains responsive during background tasks like sending emails.

---

## ⚙️ Installation

1. **Clone this repository:**
  ```bash
  git clone https://github.com/OmKadane/PyTrack.git
  cd PyTrack
  ```
2. **Create a virtual environment (recommended):**
  ```bash
  # For macOS/Linux
  python3 -m venv venv
  source venv/bin/activate
  
  # For Windows
  python -m venv venv
  venv\Scripts\activate
  ```
3. **Install the required dependencies:**
  Create a requirements.txt file with the following content:
  ```bash
  tkcalendar
  matplotlib
  Pillow
  ```
  Then, run the installation command:
  ```bash
  pip install -r requirements.txt
  ```

---

## 🏃‍♂️ Running the Application

Once the installation is complete, run the following command in your terminal:
  ```bash
  python main.py
  ```
You will be prompted to choose your preferred interface:
1. **Command-Line Interface (CLI)**
2. **Graphical User Interface (GUI)**

Select your choice and start tracking your expenses!

---

## 🔮 Future Scope

* ✅ **Data Import/Export** – Add functionality to import expenses from and export reports to CSV/Excel files.
* ✅ **Recurring Expenses** – Implement a system to automatically log recurring transactions like monthly bills or subscriptions.
* ✅ **Advanced Filtering** – Enhance the GUI with options to filter and search expenses by date range, category, or amount.
* ✅ **Web Dashboard** – Create a web-based version using Flask or Django for access from any device.
* ✅ **Cloud Sync** – Allow users to sync their data across multiple devices using a cloud service like Firebase or Dropbox.
* ✅ **Dark Mode UI** – Introduce a dark theme for an improved visual experience, especially for night use.
