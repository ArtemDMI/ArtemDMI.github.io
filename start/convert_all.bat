@echo off
cd /d "%~dp0.."
python start/md_to_html_converter.py
python start/update_index.py
