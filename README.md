# QualityReportDataFlow

![Python 3.13](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)
![MySQL / MariaDB](https://img.shields.io/badge/database-MySQL%20%2F%20MariaDB-4479A1?logo=mysql&logoColor=white)
![Gmail OAuth2](https://img.shields.io/badge/email-Gmail%20OAuth2-EA4335?logo=gmail&logoColor=white)
![Windows](https://img.shields.io/badge/runs%20on-Windows-0078D6?logo=windows&logoColor=white)

Daily **QID (Quality Inspection Device)** report. Each run reads the new inspections from MySQL, calculates the CW / BE / ME results against spec, saves them as an Excel report and emails it through Gmail.

**Installation guide:** [English](installation-module/module-en.md) · [Bahasa Indonesia](installation-module/module-id.md)

---

## Quick links

| | English | Bahasa Indonesia |
| --- | --- | --- |
| 📘 Full installation guide | [module-en.md](installation-module/module-en.md) | [module-id.md](installation-module/module-id.md) |
| 💻 Install software | [Section 1](installation-module/module-en.md#1-install-the-software) | [Bagian 1](installation-module/module-id.md#1-instal-perangkat-lunak) |
| 📦 Install Python packages | [Section 2](installation-module/module-en.md#2-install-the-python-packages) | [Bagian 2](installation-module/module-id.md#2-instal-paket-python) |
| 🗄️ Set up the database | [Section 3](installation-module/module-en.md#3-set-up-the-database) | [Bagian 3](installation-module/module-id.md#3-siapkan-database) |
| ⚙️ Fill in `.env` | [Section 4](installation-module/module-en.md#4-fill-in-the-env-file) | [Bagian 4](installation-module/module-id.md#4-isi-file-env) |
| ✉️ Gmail OAuth setup | [Section 5](installation-module/module-en.md#5-set-up-gmail-sending-google-cloud-console) | [Bagian 5](installation-module/module-id.md#5-siapkan-pengiriman-gmail-google-cloud-console) |
| ▶️ Run the report | [Section 6](installation-module/module-en.md#6-run-the-report) | [Bagian 6](installation-module/module-id.md#6-jalankan-laporan) |
| ⏰ Schedule daily runs | [Section 7](installation-module/module-en.md#7-run-it-automatically-every-day) | [Bagian 7](installation-module/module-id.md#7-jalankan-otomatis-setiap-hari) |
| 🛠️ Troubleshooting | [Section 8](installation-module/module-en.md#8-troubleshooting) | [Bagian 8](installation-module/module-id.md#8-pemecahan-masalah) |
