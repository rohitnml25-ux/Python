# Banking Management System — Streamlit

A student-friendly Python website for a Banking Management System practical.

## Features
- Create demo customer accounts
- Store account details in SQLite
- PIN-based demo account login
- Deposit and withdraw demo funds
- Transfer demo funds between accounts
- View transaction history
- View and download account statements as CSV

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Run:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

## Deploy on Streamlit Community Cloud
1. Create a GitHub repository and upload `app.py`, `requirements.txt`, and this README.
2. Open https://share.streamlit.io/ and sign in with GitHub.
3. Choose your repository, branch, and `app.py` as the main file.
4. Click Deploy.

## Important
This is an educational demonstration, not real banking software. It uses a local SQLite database and is not designed for real customer information or real financial transactions. Cloud-hosted local files may not be persistent across all hosting/redeployment scenarios; for a durable deployment, configure a supported external database.
