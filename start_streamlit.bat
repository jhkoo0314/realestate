@echo off
cd /d C:\realestate-main
C:\realestate-main\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
