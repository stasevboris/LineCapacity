@echo off
echo Запуск VoltStream Designer...

:: Переходим в папку, где лежит сам этот .bat файл
cd /d "%~dp0"

:: Активируем виртуальное окружение
call venv\Scripts\activate

:: Ждем 2 секунды, чтобы сервер успел запуститься, и открываем браузер
timeout /t 2 /nobreak > NUL
start http://127.0.0.1:8000/

:: Запускаем сам Django-сервер
python manage.py runserver

pause