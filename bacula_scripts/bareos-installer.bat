@echo off
PowerShell -NoProfile -ExecutionPolicy Bypass ^
  -Command "Start-Process -WindowStyle Maximized PowerShell -ArgumentList '-ExecutionPolicy Unrestricted','-File %CD%\bareos-installer.ps1' -Verb RunAs"
