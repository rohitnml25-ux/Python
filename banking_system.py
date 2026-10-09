"""
Banking Management System
-------------------------
Python Programming Lab (PCCCM304P) - Experiential Learning Project

Features : create accounts, deposit, withdraw, transfer funds, view balance,
           transaction history, and account statement generation.
Storage  : SQLite database (database management) + text file statements
           (file handling).
Security : PINs are stored as salted PBKDF2 hashes, never in plain text.
Concepts : OOP (classes, custom exceptions), data structures (list, dict,
           tuple), functions/modularity, file handling, exception handling.

Run      : python banking_system.py
"""

import getpass
import hashlib
import hmac
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

DB_FILE = "bank.db"
MIN_OPENING_BALANCE = Decimal("500.00")
MAX_PIN_ATTEMPTS = 3


# ------------------------------------------------------------ exceptions
class BankError(Exception):
    """Base class for all banking errors."""


class InvalidInputError(BankError):
    pass


class AccountNotFoundError(BankError):
    pass


class InsufficientFundsError(BankError):
    pass


# ------------------------------------------------------------ data classes
@dataclass
class Account:
    acc_no: int
    name: str
    phone: str
    balance: Decimal
    created_at: str


@dataclass
class Transaction:
    txn_id: int
    acc_no: int
    txn_type: str
    amount: Decimal
    balance_after: Decimal
    description: str
    created_at: str


# ------------------------------------------------------------ helpers
def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_amount(text):
    """Convert user text to a positive Decimal with 2 places."""
    try:
        amount = Decimal(str(text)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise InvalidInputError("Invalid amount.")
    if amount <= 0:
        raise InvalidInputError("Amount must be greater than zero.")
    return amount


def hash_pin(pin, salt):
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, 100_000)


# ------------------------------------------------------------ the bank
class Bank:
    """All banking operations, backed by an SQLite database."""

    def __init__(self, db_file=DB_FILE):
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                acc_no     INTEGER PRIMARY KEY,
                name       TEXT NOT NULL,
                phone      TEXT NOT NULL,
                pin_hash   BLOB NOT NULL,
                salt       BLOB NOT NULL,
                balance    TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS transactions (
                txn_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                acc_no        INTEGER NOT NULL REFERENCES accounts(acc_no),
                txn_type      TEXT NOT NULL,
                amount        TEXT NOT NULL,
                balance_after TEXT NOT NULL,
                description   TEXT,
                created_at    TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def close(self):
        self.conn.close()

    # ---- internal
    def _balance(self, acc_no):
        row = self.conn.execute(
            "SELECT balance FROM accounts WHERE acc_no = ?", (acc_no,)
        ).fetchone()
        if row is None:
            raise AccountNotFoundError(f"Account {acc_no} not found.")
        return Decimal(row["balance"])

    def _set_balance(self, acc_no, balance):
        self.conn.execute(
            "UPDATE accounts SET balance = ? WHERE acc_no = ?",
            (str(balance), acc_no),
        )

    def _record(self, acc_no, txn_type, amount, balance_after, desc):
        self.conn.execute(
            "INSERT INTO transactions (acc_no, txn_type, amount,"
            " balance_after, description, created_at) VALUES (?,?,?,?,?,?)",
            (acc_no, txn_type, str(amount), str(balance_after), desc, now()),
        )

    # ---- accounts
    def create_account(self, name, phone, pin, opening):
        name = name.strip()
        if not name:
            raise InvalidInputError("Name cannot be empty.")
        if not (phone.isdigit() and len(phone) == 10):
            raise InvalidInputError("Phone must be a 10-digit number.")
        if not (pin.isdigit() and len(pin) == 4):
            raise InvalidInputError("PIN must be exactly 4 digits.")
        opening = parse_amount(opening)
        if opening < MIN_OPENING_BALANCE:
            raise InvalidInputError(
                f"Minimum opening balance is {MIN_OPENING_BALANCE}."
            )
        salt = os.urandom(16)
        with self.conn:
            row = self.conn.execute(
                "SELECT MAX(acc_no) AS m FROM accounts"
            ).fetchone()
            acc_no = (row["m"] or 1000) + 1  # account numbers start at 1001
            self.conn.execute(
                "INSERT INTO accounts (acc_no, name, phone, pin_hash, salt,"
                " balance, created_at) VALUES (?,?,?,?,?,?,?)",
                (acc_no, name, phone, hash_pin(pin, salt), salt,
                 str(opening), now()),
            )
            self._record(acc_no, "DEPOSIT", opening, opening,
                         "Opening balance")
        return acc_no

    def verify_pin(self, acc_no, pin):
        row = self.conn.execute(
            "SELECT pin_hash, salt FROM accounts WHERE acc_no = ?", (acc_no,)
        ).fetchone()
        if row is None:
            return False
        return hmac.compare_digest(row["pin_hash"], hash_pin(pin, row["salt"]))

    def get_account(self, acc_no):
        row = self.conn.execute(
            "SELECT * FROM accounts WHERE acc_no = ?", (acc_no,)
        ).fetchone()
        if row is None:
            raise AccountNotFoundError(f"Account {acc_no} not found.")
        return Account(row["acc_no"], row["name"], row["phone"],
                       Decimal(row["balance"]), row["created_at"])

    # ---- money movement
    def get_balance(self, acc_no):
        return self._balance(acc_no)

    def deposit(self, acc_no, amount):
        amount = parse_amount(amount)
        with self.conn:
            new_bal = self._balance(acc_no) + amount
            self._set_balance(acc_no, new_bal)
            self._record(acc_no, "DEPOSIT", amount, new_bal, "Cash deposit")
        return new_bal

    def withdraw(self, acc_no, amount):
        amount = parse_amount(amount)
        with self.conn:
            balance = self._balance(acc_no)
            if amount > balance:
                raise InsufficientFundsError("Insufficient funds.")
            new_bal = balance - amount
            self._set_balance(acc_no, new_bal)
            self._record(acc_no, "WITHDRAWAL", amount, new_bal,
                         "Cash withdrawal")
        return new_bal

    def transfer(self, from_acc, to_acc, amount):
        amount = parse_amount(amount)
        if from_acc == to_acc:
            raise InvalidInputError("Cannot transfer to the same account.")
        with self.conn:  # atomic: both updates succeed or neither does
            src = self._balance(from_acc)
            dst = self._balance(to_acc)
            if amount > src:
                raise InsufficientFundsError("Insufficient funds.")
            self._set_balance(from_acc, src - amount)
            self._set_balance(to_acc, dst + amount)
            self._record(from_acc, "TRANSFER_OUT", amount, src - amount,
                         f"Transfer to {to_acc}")
            self._record(to_acc, "TRANSFER_IN", amount, dst + amount,
                         f"Transfer from {from_acc}")
        return src - amount

    # ---- history and statements
    def get_history(self, acc_no):
        self._balance(acc_no)  # raises if account does not exist
        rows = self.conn.execute(
            "SELECT * FROM transactions WHERE acc_no = ? ORDER BY txn_id",
            (acc_no,),
        ).fetchall()
        return [
            Transaction(r["txn_id"], r["acc_no"], r["txn_type"],
                        Decimal(r["amount"]), Decimal(r["balance_after"]),
                        r["description"], r["created_at"])
            for r in rows
        ]

    def generate_statement(self, acc_no, out_dir="."):
        """Write the account statement to a text file and return its path."""
        acc = self.get_account(acc_no)
        path = os.path.join(out_dir, f"statement_{acc_no}.txt")
        lines = [
            "=" * 78,
            "ACCOUNT STATEMENT".center(78),
            "=" * 78,
            f"Account No : {acc.acc_no}",
            f"Holder     : {acc.name}",
            f"Opened on  : {acc.created_at}",
            f"Generated  : {now()}",
            "-" * 78,
            f"{'Date':<20}{'Type':<14}{'Amount':>12}{'Balance':>14}"
            "  Description",
            "-" * 78,
        ]
        for t in self.get_history(acc_no):
            lines.append(
                f"{t.created_at:<20}{t.txn_type:<14}{t.amount:>12,.2f}"
                f"{t.balance_after:>14,.2f}  {t.description}"
            )
        lines += ["-" * 78, f"Closing balance: {acc.balance:,.2f}", "=" * 78]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return path


# ------------------------------------------------------------ command line
def ask_pin(prompt="Enter PIN: "):
    try:
        return getpass.getpass(prompt)
    except Exception:
        return input(prompt)


def login(bank):
    try:
        acc_no = int(input("Account number: ").strip())
    except ValueError:
        print("Invalid account number.")
        return None
    for attempt in range(MAX_PIN_ATTEMPTS):
        if bank.verify_pin(acc_no, ask_pin()):
            return acc_no
        left = MAX_PIN_ATTEMPTS - attempt - 1
        print(f"Incorrect PIN or account ({left} attempts left).")
    print("Too many failed attempts.")
    return None


def account_menu(bank, acc_no):
    while True:
        print(f"\n--- Account {acc_no} ---")
        print("1. Deposit\n2. Withdraw\n3. Transfer\n4. Check balance")
        print("5. Transaction history\n6. Generate statement\n7. Logout")
        choice = input("Choice: ").strip()
        try:
            if choice == "1":
                bal = bank.deposit(acc_no, input("Amount: "))
                print(f"Deposited. Balance: {bal:,.2f}")
            elif choice == "2":
                bal = bank.withdraw(acc_no, input("Amount: "))
                print(f"Withdrawn. Balance: {bal:,.2f}")
            elif choice == "3":
                to = int(input("Recipient account no: "))
                bal = bank.transfer(acc_no, to, input("Amount: "))
                print(f"Transferred. Balance: {bal:,.2f}")
            elif choice == "4":
                print(f"Balance: {bank.get_balance(acc_no):,.2f}")
            elif choice == "5":
                for t in bank.get_history(acc_no):
                    print(f"{t.created_at}  {t.txn_type:<13}{t.amount:>10,.2f}"
                          f"  bal {t.balance_after:>10,.2f}  {t.description}")
            elif choice == "6":
                print("Statement saved to:", bank.generate_statement(acc_no))
            elif choice == "7":
                return
            else:
                print("Invalid choice.")
        except ValueError:
            print("Error: please enter a valid number.")
        except BankError as e:
            print("Error:", e)


def main():
    bank = Bank()
    while True:
        print("\n===== BANKING MANAGEMENT SYSTEM =====")
        print("1. Create account\n2. Login\n3. Exit")
        choice = input("Choice: ").strip()
        if choice == "1":
            try:
                acc = bank.create_account(
                    input("Full name: "),
                    input("Phone (10 digits): "),
                    ask_pin("Set 4-digit PIN: "),
                    input(f"Opening deposit (min {MIN_OPENING_BALANCE}): "),
                )
                print(f"Account created! Your account number: {acc}")
            except BankError as e:
                print("Error:", e)
        elif choice == "2":
            acc = login(bank)
            if acc:
                account_menu(bank, acc)
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid choice.")
    bank.close()


if __name__ == "__main__":
    main()
