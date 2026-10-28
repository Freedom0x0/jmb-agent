@echo off
rem jmb 每日清单的定时任务壳（schtasks 调这个；只挂 10:00 一条，无 ONLOGON/ONSTART —— D30）
cd /d "C:\Users\15532\Desktop\xj\jmb"
"C:\Users\15532\AppData\Local\Programs\Python\Python313\Scripts\uv.exe" run jmb brief
