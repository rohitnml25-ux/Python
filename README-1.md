# Banking Management System

Python Programming Lab (N-PCCCM304P) - Experiential Learning Project
Rohit Harish Nagarkoti (CM25108) | Guide: Mrs. Mayuri Getme | S. B. Jain Institute of Technology, Management & Research, Nagpur

## Overview
A console-based banking system in Python: create accounts with unique account numbers, deposit, withdraw,
transfer funds, check balance, and print account statements. All data and transaction history are stored in a JSON file.

## Installation
1. Install Python 3.10 or newer.
2. Clone the repository and open the folder.
3. (Optional, only for CSV statement export) `pip install pandas`
4. Run: `python banking_system.py`
5. Run tests: `python -m unittest -v`

## Logic summary
- `Account` holds name, balance and history; `deposit`/`withdraw` validate the amount and log every transaction.
- `Bank` keeps all accounts in a dict keyed by account number (`max + 1` guarantees uniqueness) and saves to `bank_data.json` after each operation.
- Custom exceptions (`AccountNotFound`, `InsufficientBalance`) and `ValueError` handle invalid transactions.
- `transfer` withdraws from the sender first, so a failed transfer changes nothing.
