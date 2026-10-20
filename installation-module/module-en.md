# Quality Report Data Flow: Installation Module

**English** | [Bahasa Indonesia](module-id.md)

This guide installs the Quality Report Data Flow on a Windows PC and takes you all the way to a report that is emailed automatically every day.

**Prerequisites:**

- A Windows PC with internet access, because Gmail is used to send the report.
- Access to the MySQL/MariaDB database that holds the QID tables (`process_header`, `process_raw`, `member`): host, port, database name, user and password.
- A Gmail or Google Workspace account that will send the reports.
- The email addresses that should receive the report.

## Contents

- [Quality Report Data Flow: Installation Module](#quality-report-data-flow-installation-module)
  - [Contents](#contents)
  - [1. Install the software](#1-install-the-software)
  - [2. Install the Python packages](#2-install-the-python-packages)
  - [3. Set up the database](#3-set-up-the-database)
  - [4. Fill in the .env file](#4-fill-in-the-env-file)
    - [4.1 Encryption key](#41-encryption-key)
    - [4.2 Database](#42-database)
    - [4.3 Report values](#43-report-values)
    - [4.4 Recipients](#44-recipients)
  - [5. Set up Gmail sending (Google Cloud Console)](#5-set-up-gmail-sending-google-cloud-console)
    - [5.1 Create the OAuth client](#51-create-the-oauth-client)
    - [5.2 Add the client to .env](#52-add-the-client-to-env)
    - [5.3 Sign in once to create the refresh token](#53-sign-in-once-to-create-the-refresh-token)
  - [6. Run the report](#6-run-the-report)
  - [7. Run it automatically every day](#7-run-it-automatically-every-day)
  - [8. Troubleshooting](#8-troubleshooting)

> **Opening a Command Prompt in the project folder.** Many steps run a command. Open the project folder in File Explorer, click the address bar, type `cmd` and press **Enter**. A Command Prompt opens in that folder. Run every command in this guide from there.

---

## 1. Install the software

1. **Install Python 3.13.**
   [Download Python 3.13](https://www.python.org/downloads/release/python-31316/). Any 3.13.x release from [python.org/downloads/windows](https://www.python.org/downloads/windows/) works.
   On the first screen of the installer, tick **"Add python.exe to PATH"** before you click **Install Now**. If you skip this, the `python` command in this guide will not work.

2. **Install a text editor**, for editing the `.env` file:
   - [Sublime Text (recommended)](https://www.sublimetext.com/download)
   - [VS Code](https://code.visualstudio.com/download)

3. **Download the code from GitHub.**
   [GitHub Repo](https://github.com/ThePerfectJox/QualityReportDataFlow.git)
   Click **Code → Download ZIP** and extract it to a folder that will stay put, for example `C:\QualityReportDataFlow`. If Git is installed, you can run `git clone https://github.com/ThePerfectJox/QualityReportDataFlow.git` instead.

> **Shortcut:** `setup\environment.bat` installs Python 3.13, Git and Notepad++ with winget, then clones the repository into `C:\`. Right-click the file, choose **Run as administrator**, and paste the repository URL when it asks for one.

**Check:** open a **new** Command Prompt and run `python --version`. It should print `Python 3.13.x`.

---

## 2. Install the Python packages

Double-click **`setup\python-configurations.bat`**.

It installs the packages listed in `requirements.txt` (`mysql-connector-python`, `pandas`, `numpy`, `openpyxl`, `python-dotenv` and `cryptography`). It also creates `.env` from `.env.example` if `.env` does not exist yet. A successful run ends with:

```text
[OK] Python packages
[OK] Created .env from .env.example
...
  Setup completed.
```

Do this step before section 4, because the scripts in section 4 need these packages.

---

## 3. Set up the database

1. Make sure the MySQL server is running. In XAMPP, click **Start** next to *MySQL*.
2. Optional: also start **Apache**, so you can use phpMyAdmin at `http://localhost/phpmyadmin`. The MySQL command line works too.
3. Run **`installation-module\sql-configuration.sql`** on the database that holds the QID tables:
   - **phpMyAdmin:** click the database in the left panel, then **Import** → **Choose file** → select `sql-configuration.sql` → **Import**.
   - **MySQL command line:** `mysql -u <user> -p <database> < installation-module\sql-configuration.sql`

   The script creates the `daily_report` view that the program reads from, and three indexes that make the view faster.
4. **Check:** run `SELECT * FROM daily_report LIMIT 5;`. It should return rows.

You can safely run the script again. The view is replaced. Errors that say `Duplicate key name` only mean the indexes already exist.

---

## 4. Fill in the .env file

`.env` holds every setting the program uses. Secrets such as passwords and tokens are stored **encrypted** with a key that is kept in the same file. Treat `.env` like a password: don't email it, share it or upload it. It is already excluded from Git.

Open `.env` in your text editor and fill it in **in this order**.

### 4.1 Encryption key

1. Run:

   ```bat
   python script\create_key.py
   ```

2. Copy the two lines it prints into `.env`, replacing the placeholder lines:

   ```text
   ENCRYPTION_ALGORITHM = aes-gcm
   ENCRYPTION_KEY = <the generated key>
   ```

3. **Save `.env`.** The encryption script in the next step reads the key from the saved file.

Create the key once, before you encrypt anything. If you create a new key later, you have to encrypt every encrypted value in `.env` again.

> **How to encrypt a value.** Run `python script\encrypt_value.py "<plain value>"` and paste the printed token into `.env`. To check a token, run `python script\decrypt_value.py "<token>"`, which prints the original value.

### 4.2 Database

| Key | What to enter |
| --- | --- |
| `MYSQL_HOST` | Address of the MySQL server. Use `localhost` if MySQL runs on this PC. |
| `MYSQL_PORT` | Usually `3306`. |
| `MYSQL_DATABASE` | The database you ran `sql-configuration.sql` on. |
| `MYSQL_USER` | MySQL user name. It only needs `SELECT` permission on that database. |
| `MYSQL_PASSWORD` | The password, **encrypted** with `encrypt_value.py`. Leave it empty if the user has no password, as with the default XAMPP `root` user. |

### 4.3 Report values

These values are written into every row of the report.

| Key | Report column | Example |
| --- | --- | --- |
| `PLANT` | Plant/Reg | `RK1` |
| `LOCATION` | Location | `U6` |
| `GROUP` | Group/Cell | `99` |
| `BRAND` | Brand | `DUMMY` |
| `BAGIAN` | Bagian | `Rolling & Cutting` |
| `SET_SAMPLE` | Set Sample | `1` |

### 4.4 Recipients

| Key | What to enter |
| --- | --- |
| `EMAIL_RECIPIENT` | Addresses that receive the report, separated by commas, e.g. `qa.lead@example.com, supervisor@example.com` |
| `EMAIL_SUBJECT` | *Optional.* Replaces the default subject `[QID] Quality Inspection Device - Rungkut 1 - Unit 1 - <today's date>`. |

Every report is also CC'd to the addresses in `LIST_CC_EMAIL` near the top of `main.py`. Edit that list to change them.

You fill in the email keys `SMTP_USER` and `OAUTH_*` in section 5.

> **Upgrading an older install?** Older `.env` files contain `SMTP_HOST`, `SMTP_PASSWORD` and `SMTP_AUTH`. They are no longer used and can be deleted. Email now always goes through Gmail with OAuth.

---

## 5. Set up Gmail sending (Google Cloud Console)

The program signs in to Gmail with **OAuth 2.0**, Google's standard sign-in for apps. It doesn't need the Gmail password or an app password. You create an OAuth client once in Google Cloud Console and sign in once in the browser. After that, the program sends email on its own.

### 5.1 Create the OAuth client

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and sign in. Signing in with the Gmail account that will send the reports keeps everything in one place.
2. **Create a project.** Click the project picker at the top of the page, then **New project**. Enter a name such as `Quality Report` and click **Create**. Make sure the new project is selected afterwards.
3. Open **☰ Menu → Google Auth platform** (or type "Google Auth platform" in the search bar) and click **Get started**. Fill in:
   - **App information:** App name `Quality Report`, and your email as the User support email.
   - **Audience:** **External** for a regular `@gmail.com` account. Choose **Internal** if the sending account is a company Google Workspace account and the project belongs to that organization.
   - **Contact information:** your email.
   - Agree to the policy and click **Create**.
4. **External only:** open **Audience**, click **Publish app**, then **Confirm**. The status must say **In production**. While the status is *Testing*, Google ends the sign-in after 7 days and the program stops sending.
5. Open **Clients → Create client**:
   - **Application type:** `Desktop app`
   - **Name:** anything, e.g. `Quality Report Desktop`
   - Click **Create**.

   **Copy the Client ID and the Client secret now**, or click **Download JSON**. Google shows the secret only once. If you lose it, add a new secret to the same client.

You don't need to enable the Gmail API.

### 5.2 Add the client to .env

| Key | What to enter |
| --- | --- |
| `SMTP_USER` | The Gmail address that sends the reports. |
| `OAUTH_CLIENT_ID` | The Client ID, as plain text. It ends with `.apps.googleusercontent.com`. |
| `OAUTH_CLIENT_SECRET` | The Client secret, **encrypted**: `python script\encrypt_value.py "<client secret>"` |

Save `.env`.

### 5.3 Sign in once to create the refresh token

1. Run:

   ```bat
   python script\create_oauth_token.py
   ```

2. Your browser opens Google's sign-in page. Sign in as the **`SMTP_USER`** account.
3. Google shows **"Google hasn't verified this app"**. It is your own app, so click **Advanced → Go to Quality Report (unsafe)**.
4. On the access screen, allow access to Gmail and click **Continue**. If a checkbox is shown, tick it.
5. The browser shows **"Access granted."** Back in the Command Prompt, the script tests the Gmail login and prints:

   ```text
   SMTP login OK.

   Add this to your .env:

   OAUTH_REFRESH_TOKEN = <encrypted token>
   ```

6. Copy the `OAUTH_REFRESH_TOKEN` line into `.env` and save it.

Gmail only allows SMTP sign-in with full mail access (`https://mail.google.com/`), so the consent screen asks for that. The program only uses it to send the report. To revoke access, remove the app at [myaccount.google.com/permissions](https://myaccount.google.com/permissions).

**Run step 5.3 again** if any of these happens: the Gmail password is changed, access is removed, the token goes unused for 6 months, or the program reports that Google rejected the refresh token.

---

## 6. Run the report

```bat
python main.py
```

A successful run looks like this:

```text
1) Loading .env
2) Connecting to MySQL
3) Running query
4) Processing query results
   12 rows, 40 columns
   ...
5) Writing Excel
   Report: C:\QualityReportDataFlow\reports\2026\october\quality_report_20261020_070000.xlsx
6) Building email
   Recipients: ['qa.lead@example.com', ...]
7) Sending email
   Email sent.
8) Updating query cache
   Cache updated to: 2026-10-20T06:58:12
```

- The Excel report is saved in `reports\<year>\<month>\`.
- `cache.json` stores the `End` time of the newest row that was sent. The next run only sends rows that ended after that time. On a new install, set `last_end_timestamp` in `cache.json` to the point where reporting should start, for example `{"last_end_timestamp": "2026-10-20T00:00:00"}`.
- `Query returned no rows. Nothing to report.` means there are no new rows since the last run, so nothing is sent.
- If sending fails, the cache is not updated, so the same rows are sent on the next run.

To send only a test email, without touching the database or the cache, run `python test\TestEmailManager.py`.

---

## 7. Run it automatically every day

`setup\run-report.bat` runs `main.py` once and appends its output to `report.log` in the project folder. Use Windows Task Scheduler to run it on a schedule:

1. Open the Start menu, type **Task Scheduler** and open it. Click **Create Basic Task…**.
2. **Name:** `Quality Report`, then **Next**.
3. **Trigger:** **Daily**, then choose the time, then **Next**.
4. **Action:** **Start a program**. Under **Program/script**, click **Browse…** and select `setup\run-report.bat` in the project folder. Click **Next**, then **Finish**.
5. *Optional:* open the task's **Properties** and select **Run whether user is logged on or not**, so the task also runs when the PC is locked or signed out. Windows asks for the account password. Use the same Windows account that ran section 2.
6. **Test it:** right-click the task, choose **Run**, then open `report.log`.

The PC must be switched on and connected to the internet at the scheduled time.

---

## 8. Troubleshooting

| Message | What to do |
| --- | --- |
| `'python' is not recognized` or the Microsoft Store opens | Python is not on PATH. Reinstall Python with **"Add python.exe to PATH"** ticked, or use `py -3` in place of `python`. |
| `ModuleNotFoundError: No module named ...` | Run `setup\python-configurations.bat` again. |
| `.env file not found` | Run `setup\python-configurations.bat`, or copy `.env.example` to `.env`. |
| `X environment variable has not been configured` / `X is empty` | Add key `X` to `.env`, or fill in its value. |
| `Key must be (16, 24, 32) bytes` / `ENCRYPTION_KEY is not valid base64` | `ENCRYPTION_KEY` is still the placeholder or is damaged. Redo section 4.1. |
| `InvalidTag` / `Token is not valid base64` | An encrypted value was made with a different key or was pasted incompletely. Encrypt it again. |
| `MYSQL_PASSWORD could not be decrypted` | `MYSQL_PASSWORD` is plain text. Encrypt it (section 4.1), or leave it empty if there is no password. |
| `2003 Can't connect to MySQL server` | MySQL is not running, or `MYSQL_HOST` / `MYSQL_PORT` is wrong. |
| `1045 Access denied for user` | `MYSQL_USER` or `MYSQL_PASSWORD` is wrong. |
| `1146 Table '...daily_report' doesn't exist` | Run `sql-configuration.sql` on the database named in `MYSQL_DATABASE` (section 3). |
| `Google rejected the OAuth client` | Check `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET`, and that the client still exists in Google Cloud Console. |
| `Google rejected the refresh token` | Run section 5.3 again. If this happens every 7 days, publish the app (section 5.1, step 4). |
| `Google did not return a refresh token` | Remove the app at [myaccount.google.com/permissions](https://myaccount.google.com/permissions), then run section 5.3 again. |
| `Gmail access was not granted` | Run section 5.3 again and allow Gmail access on the consent screen. |
| `OAuth login for ... was rejected` | You signed in with a different account than `SMTP_USER`. Run section 5.3 again and sign in as `SMTP_USER`. |
| Google shows "Access blocked" or "This app is blocked" | App still in *Testing*: publish it (section 5.1, step 4). Company Workspace account: ask the admin to trust the Client ID (Admin console → Security → API controls), or use an **Internal** app. |
| `Could not reach https://oauth2.googleapis.com/token` | There is no internet connection, or a proxy or firewall is blocking Google. |
| `TimeoutError` when sending, or `does not offer XOAUTH2 login` | The network may block port 587. Add `SMTP_PORT = 465` and `SMTP_SECURITY = ssl` to `.env`. |
| `Query returned no rows. Nothing to report.` | Not an error: there are no new rows since the time in `cache.json` (section 6). |
