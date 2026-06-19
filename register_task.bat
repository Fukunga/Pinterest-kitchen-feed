@echo off
schtasks /create /tn "Pinterest_Amazon_Automation" /tr "cmd.exe /c \"\"cd /d c:\Datas\Gemini\Pinterest_Amazon && python -u src\main.py >> c:\Datas\Gemini\Pinterest_Amazon\run_log.txt 2>&1\"\"" /sc DAILY /st 07:00 /f
pause
