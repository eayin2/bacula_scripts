$SERVER_IP = "192.168.2.191"
$CLIENT_FQDN = "vm-win02.testenv01.com"
$SMB_SHARE_NAME = "bareos"

Write-Host "Mounting the SMB-share \\$SERVER_IP\$SMB_SHARE_NAME to Q:"
net use Q: \\$SERVER_IP\$SMB_SHARE_NAME
Write-Host "Copy bareos installer to C:\"
robocopy Q:\bareos-bins C:\bareos-bins /COPYALL /E /DCOPY:T
Write-Host "Install Bareos"
C:\bareos-bins\bareos64.exe /S | Out-Null
Write-Host "Copy configuration files to C:\"
mkdir C:\ProgramData\bareos\ 2> NULL
Copy-Item -Path Q:\bareos-bins\bconsole.exe,Q:\bareos-bins\*.dll -Destination "C:\Program
Files\bareos\"
robocopy Q:\$CLIENT_FQDN\certs\ C:\ProgramData\bareos\
robocopy Q:\$CLIENT_FQDN\ C:\ProgramData\bareos\ bconsole.conf
robocopy Q:\$CLIENT_FQDN\bareos-fd.d C:\ProgramData\bareos\bareos-fd.d /COPYALL /E /DCOPY:T
Write-Host "Unmount the samba share"
net use  Q: /delete
Write-Host "Restart bareos daemons"
net stop bareos-fd
net start bareos-fd
Read-Host -Prompt "Press Enter to exit"
