# Инструкция по настройке SSH для деплоя

## Генерация SSH ключей (Windows)

Откройте PowerShell или Git Bash и выполните:

\Generating public/private ed25519 key pair.
Your identification has been saved in github_deploy_key
Your public key has been saved in github_deploy_key.pub
The key fingerprint is:
SHA256:TX9uzidGr6v0Rxa9domsKMmLUEw1KtV+zPFotuTTy/8 github-actions-besthack25
The key's randomart image is:
+--[ED25519 256]--+
|     ..o         |
|    . o...       |
|   . o. o =     .|
|    +  . @ o   ..|
|     o  S + o o +|
|    .    + . =.++|
|   .  . . + +.++.|
|    . .+ . = =o +|
|     . .o   o+BE |
+----[SHA256]-----+
Generating public/private rsa key pair.
github_deploy_key already exists.
Overwrite (y/n)? 
Не вводите passphrase (оставьте пустым).

У вас появятся 2 файла:
- \ (приватный ключ) ← для GitHub Secrets
- \ (публичный ключ) ← для сервера

## Копирование ключей

### Windows (PowerShell):
\Windows PowerShell
(C) ��௮��� �������� (Microsoft Corporation). �� �ࠢ� ���饭�.

��⠭���� ��᫥���� ����� PowerShell ��� ����� �㭪権 � ���襭��! https://aka.ms/PSWindows

PS C:\Users\Apolon 1\RiderProjects\best_hack25> 
### Git Bash:
\ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDUBzUXNYkv6s/sCT1zxe3d1HUyIsLpsDi6Kkc5bYwfI github-actions-besthack25
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACA1Ac1FzWJL+rP7Ak9c8Xt3dR1MiLC6bA4uipHOW2MHyAAAAKBXvtZiV77W
YgAAAAtzc2gtZWQyNTUxOQAAACA1Ac1FzWJL+rP7Ak9c8Xt3dR1MiLC6bA4uipHOW2MHyA
AAAEB3DzkvXrmH7IG/F9jc4XsS7hUpS1XGw5wDfsaWFmrGlTUBzUXNYkv6s/sCT1zxe3d1
HUyIsLpsDi6Kkc5bYwfIAAAAGWdpdGh1Yi1hY3Rpb25zLWJlc3RoYWNrMjUBAgME
-----END OPENSSH PRIVATE KEY-----
