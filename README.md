# SqlToExcel
Get Data from SQL and Create an Excel File from it

## Dependencies

```bash
pip install mysql-connector-python pandas openpyxl python-dotenv
# optional, only for EMAIL_SEND_METHOD=outlook
pip install pywin32
```

## Sending the generated .eml files

`fetchMySql.py` writes `output/result_<timestamp>.eml`. `sendEmail.py` sends them
over SMTP (or through Outlook) and moves sent files to `output/sent/`.

```bash
python sendEmail.py              # send every .eml in ./output
python sendEmail.py --latest     # send only the newest one
python sendEmail.py --dry-run    # preview without sending
python sendEmail.py --method outlook
```

Configure `SMTP_*` and `EMAIL_SEND_METHOD` in `.env` (see `.env.example`).