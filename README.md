# Banking Management System

Python Programming Lab (PCCCM304P) – Experiential Learning Project
**Student:** Rohit Harish Nagarkoti | **Project ID:** CM25108
**Status:** Phase II – coding complete (testing and deployment follow in Phase III)

## Overview
A command-line banking application written in Python. Users can create
accounts, deposit and withdraw money, transfer funds between accounts, check
balances, view transaction history and generate account statements. Data is
stored in an SQLite database.

## Installation and running
Requires Python 3.8+. No external packages are needed.

```bash
git clone <your-repo-url>
cd <repo-folder>
python banking_system.py
```

## Summary of logic
- **`Bank` class** holds every operation (create account, deposit, withdraw,
  transfer, history, statement) on top of an SQLite database.
- **`Account` and `Transaction` dataclasses** represent records read from the DB.
- **Custom exceptions** (`InvalidInputError`, `AccountNotFoundError`,
  `InsufficientFundsError`) give clear error handling.
- **Security:** PINs are never stored, only a salted PBKDF2-SHA256 hash.
- **Accuracy:** money is handled with `Decimal`, not floats.
- **Consistency:** each operation runs inside a database transaction, so a
  transfer either updates both accounts or neither.
- **File handling:** statements are written to `statement_<account no>.txt`.

## Roadmap
- [x] Phase I – problem understanding and logic design
- [x] Phase II – coding of all modules
- [ ] Phase III – testing, deployment, final report
- [ ] 
