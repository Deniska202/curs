#!/usr/bin/env python3

# GPIO
import RPi.GPIO as GPIO

# Зависимости для ЖК экрана
from subprocess import Popen, PIPE
from time import sleep
from datetime import datetime
import board
import digitalio
import adafruit_character_lcd.character_lcd as characterlcd

# Асинхронные ивенты
import asyncio
from datetime import datetime

# http api
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from starlette import status
from starlette.responses import Response

# Размеры экрана
lcd_columns = 16
lcd_rows = 2
# Адрес реле
relay_address = 27

# адреса пинов LCD
lcd_rs = digitalio.DigitalInOut(board.D22)
lcd_en = digitalio.DigitalInOut(board.D17)
lcd_d4 = digitalio.DigitalInOut(board.D25)
lcd_d5 = digitalio.DigitalInOut(board.D24)
lcd_d6 = digitalio.DigitalInOut(board.D23)
lcd_d7 = digitalio.DigitalInOut(board.D18)

# declare some stuff
app = FastAPI()
event = asyncio.Event()
lcd = characterlcd.Character_LCD_Mono(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6,
                                      lcd_d7, lcd_columns, lcd_rows)


# Проинициализировать GPIO
def init_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(relay_address, GPIO.OUT, initial = GPIO.LOW)


# generate placeholder text
async def placeholder():
    while True:
        try:
            await asyncio.wait_for(event.wait(), 10)
        except asyncio.CancelledError:
            print("Cancelled")
        except asyncio.TimeoutError:
            msg = create_no_new_notifications()
            lcd.message = msg.str()


# on request hooks
def on_request():
    event.set()
    event.clear()


# notification class
class Notification(BaseModel):
    text: str


# relay class
class RelayState(BaseModel):
    enabled: bool


# lcd message class
class LcdMessage:
    lcd_line_1: str
    lcd_line_2: str

    def str(self):
        return self.lcd_line_1 + "\n" + self.lcd_line_2


# Обработчик запроса на новое уведомление
@app.post("/notification")
async def save_notification(notification: Notification):
    msg = create_notification_msg(notification)
    lcd.message = msg.str()
    on_request()
    return Response(status_code=status.HTTP_200_OK)


# Обработчик запроса на переключение реле
@app.post("/relay")
async def relay(state: RelayState):
    msg = create_relay_state(state)
    lcd.message = msg.str()
    on_request()
    return Response(status_code=status.HTTP_200_OK)


# Создать сообщение на экран с уведомлением
def create_notification_msg(notification: Notification):
    lcd_line_1 = datetime.now().strftime('%b %d     %H:%M\n')
    lcd_line_2 = notification.text + "                "
    msg = LcdMessage()
    msg.lcd_line_1 = lcd_line_1
    msg.lcd_line_2 = lcd_line_2
    return msg


# Создать сообщение на экран с переключением реле
def create_relay_state(new_state: RelayState):
    line_1 = datetime.now().strftime('%b %d     %H:%M\n')
    if new_state.enabled:
        line_2 = "Relay up        "
        GPIO.output(relay_address, GPIO.HIGH)
    else:
        line_2 = "Relay down      "
        GPIO.output(relay_address, GPIO.LOW)
    msg = LcdMessage()
    msg.lcd_line_1 = line_1
    msg.lcd_line_2 = line_2
    return msg


# Создать сообщение на экран с заглушкой
def create_no_new_notifications():
    line_1 = datetime.now().strftime('%b %d     %H:%M\n')
    line_2 = "No notifications"
    msg = LcdMessage()
    msg.lcd_line_1 = line_1
    msg.lcd_line_2 = line_2
    return msg


# Старт приложения
@app.on_event("startup")
async def startup():
    init_gpio()
    lcd.message = "App starting... \n                 "
    asyncio.gather(
        placeholder(),
    )


# Завершение работы приложения
@app.on_event("shutdown")
def shutdown_event():
    GPIO.output(relay_address, GPIO.LOW)
    lcd.message = "Shutdown APP    \n               "


# Точка входа в приложение
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
