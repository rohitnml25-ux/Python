import streamlit as st
import sqlite3
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
import pandas as pd

# Educational project only. Do not use for real money or real customer data.
DB_PATH = Path(__file__).with_name("banking.db")

st.set_page_config(page_title="Banking Management System", page_icon="🏦", layout="wide")

def connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                account_no TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                pin_salt TEXT NOT NULL,
                pin_hash TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_no TEXT NOT NULL,
                txn_type TEXT NOT NULL,
                amount REAL NOT NULL,
                note TEXT,
                related_account TEXT,
                created_at TEXT NOT NULL
            )
        """)

def hash_pin(pin, salt):
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 200_000).hex()

def make_account_no():
    with connect() as conn:
        while True:
            number = str(secrets.randbelow(9000000000) + 1000000000)
            if not conn.execute("SELECT 1 FROM accounts WHERE account_no=?", (number,)).fetchone():
                return number

def record_txn(conn, account_no, txn_type, amount, note="", related_account=None):
    conn.execute(
        """INSERT INTO transactions(account_no, txn_type, amount, note, related_account, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (account_no, txn_type, float(amount), note, related_account, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

def get_account(account_no):
    with connect() as conn:
        return conn.execute("SELECT * FROM accounts WHERE account_no=?", (account_no,)).fetchone()

def money(value):
    return f"₹{float(value):,.2f}"

init_db()

st.markdown("""
<style>
    .main {background: #f6f8fc;}
    .hero {padding: 1.2rem 1.5rem; border-radius: 18px; background: linear-gradient(120deg,#102a43,#176b87); color:white;}
    .hero h1 {color:white; margin-bottom:.2rem;}
    div[data-testid="stMetric"] {background:white; padding:16px; border-radius:14px; border:1px solid #e8edf3;}
    .small-note {color:#5b6573;font-size:.9rem;}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🏦 BankDesk")
    st.caption("Banking Management System")
    page = st.radio("Navigation", [
        "Dashboard", "Create Account", "Account Login", "Deposit", "Withdraw",
        "Transfer Funds", "Transaction History", "Account Statement"
    ])
    st.divider()
    st.caption("Academic demo • SQLite database")

st.markdown("""
<div class="hero">
  <h1>Banking Management System</h1>
  <p>Create accounts, manage deposits and withdrawals, transfer demo funds, and view transaction records.</p>
</div>
""", unsafe_allow_html=True)

st.warning("Educational project only. This app is not connected to a real bank and must not be used for real money, real PINs, or sensitive customer information.")

def account_picker(label="Select account"):
    with connect() as conn:
        rows = conn.execute("SELECT account_no, full_name FROM accounts ORDER BY created_at DESC").fetchall()
    if not rows:
        st.info("No accounts exist yet. Create an account first.")
        return None
    choices = {f"{r['account_no']} — {r['full_name']}": r["account_no"] for r in rows}
    chosen = st.selectbox(label, list(choices.keys()))
    return choices[chosen]

if page == "Dashboard":
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        total = conn.execute("SELECT COALESCE(SUM(balance),0) FROM accounts").fetchone()[0]
        txn_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    a, b, c = st.columns(3)
    a.metric("Total accounts", count)
    b.metric("Demo deposits held", money(total))
    c.metric("Transactions", txn_count)
    st.subheader("Quick actions")
    cols = st.columns(3)
    for col, title, desc in zip(cols, ["Create an account", "Move money", "View records"],
                                ["Register a demo customer", "Deposit, withdraw or transfer", "Review history and statements"]):
        with col:
            st.markdown(f"### {title}")
            st.write(desc)
    st.subheader("Recent transactions")
    with connect() as conn:
        df = pd.read_sql_query("""
            SELECT id AS 'ID', account_no AS 'Account', txn_type AS 'Type',
                   amount AS 'Amount (₹)', note AS 'Note', related_account AS 'Related account',
                   created_at AS 'Date/time'
            FROM transactions ORDER BY id DESC LIMIT 8
        """, conn)
    if df.empty:
        st.info("Transactions will appear here after you create an account and make a demo transaction.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Create Account":
    st.subheader("Create a new account")
    with st.form("create_account_form", clear_on_submit=True):
        full_name = st.text_input("Full name")
        email = st.text_input("Email address")
        phone = st.text_input("Phone (optional)")
        pin = st.text_input("Create a 4–8 digit demo PIN", type="password", max_chars=8)
        opening = st.number_input("Opening balance (₹)", min_value=0.0, max_value=1_000_000.0, value=0.0, step=100.0)
        submitted = st.form_submit_button("Create account", type="primary")
    if submitted:
        if not full_name.strip() or not email.strip():
            st.error("Please enter a name and email address.")
        elif not (pin.isdigit() and 4 <= len(pin) <= 8):
            st.error("PIN must contain 4 to 8 digits.")
        else:
            salt = secrets.token_hex(16)
            account_no = make_account_no()
            try:
                with connect() as conn:
                    conn.execute("""
                        INSERT INTO accounts(account_no, full_name, email, phone, pin_salt, pin_hash, balance, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (account_no, full_name.strip(), email.strip().lower(), phone.strip(), salt,
                          hash_pin(pin, salt), float(opening), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    if opening > 0:
                        record_txn(conn, account_no, "Opening deposit", opening, "Initial balance")
                st.success(f"Account created! Demo account number: {account_no}")
                st.info("Save this account number for this local demo. Do not use a real PIN.")
            except sqlite3.IntegrityError:
                st.error("An account with this email already exists.")

elif page == "Account Login":
    st.subheader("Account login")
    st.write("Use the account number and demo PIN you created in this app.")
    with st.form("login_form"):
        account_no = st.text_input("Account number")
        pin = st.text_input("Demo PIN", type="password", max_chars=8)
        submitted = st.form_submit_button("View account", type="primary")
    if submitted:
        acc = get_account(account_no.strip())
        if acc and hash_pin(pin, acc["pin_salt"]) == acc["pin_hash"]:
            st.session_state["logged_account"] = acc["account_no"]
            st.success("Login successful.")
        else:
            st.error("Account number or PIN is incorrect.")
    logged = st.session_state.get("logged_account")
    if logged:
        acc = get_account(logged)
        if acc:
            st.markdown(f"### Welcome, {acc['full_name']}")
            x, y = st.columns(2)
            x.metric("Account number", acc["account_no"])
            y.metric("Available demo balance", money(acc["balance"]))
            st.caption(f"Created: {acc['created_at']}")
            if st.button("Log out"):
                st.session_state.pop("logged_account", None)
                st.rerun()

elif page == "Deposit":
    st.subheader("Deposit demo funds")
    acct = account_picker()
    if acct:
        amount = st.number_input("Deposit amount (₹)", min_value=1.0, max_value=1_000_000.0, value=100.0, step=100.0)
        note = st.text_input("Description (optional)", value="Cash deposit")
        if st.button("Confirm deposit", type="primary"):
            with connect() as conn:
                conn.execute("UPDATE accounts SET balance=balance+? WHERE account_no=?", (amount, acct))
                record_txn(conn, acct, "Deposit", amount, note)
            st.success(f"Deposited {money(amount)}. New balance: {money(get_account(acct)['balance'])}")

elif page == "Withdraw":
    st.subheader("Withdraw demo funds")
    acct = account_picker()
    if acct:
        acc = get_account(acct)
        st.metric("Current balance", money(acc["balance"]))
        amount = st.number_input("Withdrawal amount (₹)", min_value=1.0, max_value=1_000_000.0, value=100.0, step=100.0)
        note = st.text_input("Description (optional)", value="Cash withdrawal")
        if st.button("Confirm withdrawal", type="primary"):
            acc = get_account(acct)
            if amount > acc["balance"]:
                st.error("Insufficient balance.")
            else:
                with connect() as conn:
                    conn.execute("UPDATE accounts SET balance=balance-? WHERE account_no=?", (amount, acct))
                    record_txn(conn, acct, "Withdrawal", amount, note)
                st.success(f"Withdrew {money(amount)}. New balance: {money(get_account(acct)['balance'])}")

elif page == "Transfer Funds":
    st.subheader("Transfer demo funds")
    with connect() as conn:
        rows = conn.execute("SELECT account_no, full_name FROM accounts ORDER BY full_name").fetchall()
    if len(rows) < 2:
        st.info("Create at least two demo accounts to test transfers.")
    else:
        choices = {f"{r['account_no']} — {r['full_name']}": r["account_no"] for r in rows}
        with st.form("transfer_form"):
            source_label = st.selectbox("From account", list(choices.keys()), key="source")
            destination_options = [label for label in choices if choices[label] != choices[source_label]]
            dest_label = st.selectbox("To account", destination_options)
            amount = st.number_input("Transfer amount (₹)", min_value=1.0, max_value=1_000_000.0, value=100.0, step=100.0)
            note = st.text_input("Description (optional)", value="Account transfer")
            submitted = st.form_submit_button("Transfer funds", type="primary")
        if submitted:
            source, destination = choices[source_label], choices[dest_label]
            with connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                src = conn.execute("SELECT balance FROM accounts WHERE account_no=?", (source,)).fetchone()
                if not src or amount > src["balance"]:
                    st.error("Insufficient balance in the source account.")
                else:
                    conn.execute("UPDATE accounts SET balance=balance-? WHERE account_no=?", (amount, source))
                    conn.execute("UPDATE accounts SET balance=balance+? WHERE account_no=?", (amount, destination))
                    record_txn(conn, source, "Transfer sent", amount, note, destination)
                    record_txn(conn, destination, "Transfer received", amount, note, source)
                    st.success(f"Transferred {money(amount)} successfully.")

elif page == "Transaction History":
    st.subheader("Transaction history")
    acct = account_picker()
    if acct:
        with connect() as conn:
            df = pd.read_sql_query("""
                SELECT id AS 'Transaction ID', txn_type AS 'Type', amount AS 'Amount (₹)',
                       note AS 'Description', related_account AS 'Related account', created_at AS 'Date/time'
                FROM transactions WHERE account_no=? ORDER BY id DESC
            """, conn, params=(acct,))
        if df.empty:
            st.info("No transactions for this account yet.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("Download history as CSV", df.to_csv(index=False).encode("utf-8"),
                               file_name=f"transactions_{acct}.csv", mime="text/csv")

elif page == "Account Statement":
    st.subheader("Account statement")
    acct = account_picker()
    if acct:
        acc = get_account(acct)
        st.markdown(f"### {acc['full_name']}")
        st.write(f"**Account number:** {acc['account_no']}  ")
        st.write(f"**Email:** {acc['email']}  ")
        st.write(f"**Account opened:** {acc['created_at']}")
        st.metric("Current balance", money(acc["balance"]))
        with connect() as conn:
            df = pd.read_sql_query("""
                SELECT created_at AS 'Date/time', txn_type AS 'Transaction',
                       amount AS 'Amount (₹)', note AS 'Description',
                       related_account AS 'Related account'
                FROM transactions WHERE account_no=? ORDER BY id
            """, conn, params=(acct,))
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("Download account statement (CSV)", df.to_csv(index=False).encode("utf-8"),
                           file_name=f"statement_{acct}.csv", mime="text/csv")

st.divider()
st.caption("Student project: Python + Streamlit + SQLite. For a real banking system, use audited infrastructure, strong authentication, authorization, encryption, monitoring, backups, and regulatory review.")
