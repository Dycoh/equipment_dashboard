@echo off
cd %~dp0
call venv\Scripts\activate
streamlit run app.py
pause
