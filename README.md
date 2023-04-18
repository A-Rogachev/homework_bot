
<a id='start_page'></a>
# <p align = center>Telegram бот-ассистент для сервиса Практикум.Домашка</p>
#### *Telegram-бот для доступа к API сервиса Практикум.Домашка*
___
-   бот раз в 10 минут опрашивает сервис и проверяет статус отправленной на ревью домашней работы;
-  при обновлении статуса в Telegram отправляется соответствующее уведомление;
- в процессе работы ведется логирование - бот сообщает о важных проблемах сообщением в Telegram.

[![](https://img.shields.io/badge/Python-3.7.9-blue)](https://www.python.org/downloads/release/python-379/) [![](https://img.shields.io/badge/python-telegram-bot)](https://pypi.org/project/python-telegram-bot/)

#### Как запустить проект:
1. Клонировать репозиторий и перейти в него в терминале:
```
git clone https://github.com/A-Rogachev/homework_bot.git
```
```
cd homework_bot
```
2. Создать и активировать виртуальное окружение.
```
python3 -m venv env
```
```
source env/bin/activate
```
3. Установить зависимости из файла requirements.txt:
```
python3 -m pip install --upgrade pip
```
```
pip install -r requirements.txt
```
4. Запустить проект:
 ```
python3 homework.py
```

#### Автор

><font size=2>Рогачев А.Г.  
Студент факультета Бэкенд. Когорта № 50</font>

[вверх](#start_page)
