# Truck Volvo 221 Bot

Робоча версія Telegram-бота для обліку рейсів і заправок у Google Sheets.

## Що вміє

- записує Pickup
- записує Delivery
- записує Fuel
- рахує Loaded miles
- рахує Deadhead miles
- рахує Fuel total
- рахує Gross
- рахує After fuel
- записує всі дані в Google Sheets

## Команди

```text
/pickup Chicago IL пробіг 745120
```

```text
/fuel Loves 198 gal 1132.22 пробіг 745900
```

```text
/delivery Los Angeles CA пробіг 747300 rate 6200
```

```text
/summary
```

## Важливо

Файл `google_credentials.json` не завантажуй публічно в GitHub.
Його треба покласти поруч із `bot.py` на тому пристрої, де запускається бот.
