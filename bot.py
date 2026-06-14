import os
import re
import json
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

DATA_FILE = Path("truck_data.json")


def load_data():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {"current_trip": None, "trips": [], "fuel": [], "expenses": []}


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def find_odometer(text):
    m = re.search(r"(?:пробіг|odometer|odo)\s*[:\-]?\s*(\d+)", text, re.I)
    return int(m.group(1)) if m else None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚛 Truck Volvo 221 готовий.\n\n"
        "Пиши так:\n"
        "/pickup Chicago IL пробіг 745120\n"
        "/fuel Loves 198 gal 1132.22 пробіг 745900\n"
        "/delivery Los Angeles CA пробіг 747300 rate 6200\n"
        "/summary"
    )


async def pickup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    text = update.message.text
    odo = find_odometer(text)
    place = text.replace("/pickup", "").strip()
    place = re.sub(r"(пробіг|odometer|odo).*", "", place, flags=re.I).strip()

    data["current_trip"] = {
        "pickup_place": place,
        "pickup_odo": odo,
        "pickup_time": datetime.now().isoformat(timespec="seconds"),
        "delivery_place": None,
        "delivery_odo": None,
        "rate": 0,
    }
    save_data(data)

    await update.message.reply_text(f"✅ Завантаження записано:\n📍 {place}\n🛣️ Пробіг: {odo}")


async def fuel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    text = update.message.text

    gallons_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:gal|gallon|гал|галон)", text, re.I)
    gallons = float(gallons_match.group(1).replace(",", ".")) if gallons_match else None

    odo = find_odometer(text)

    numbers = [float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", text)]
    amount = None
    for n in numbers:
        if n > 50 and (gallons is None or abs(n - gallons) > 0.01) and (odo is None or int(n) != odo):
            amount = n

    station = text.replace("/fuel", "").strip()
    station = re.sub(r"\d+(?:[.,]\d+)?\s*(gal|gallon|гал|галон)", "", station, flags=re.I)
    station = re.sub(r"\$?\s*\d+(?:[.,]\d+)?", "", station)
    station = re.sub(r"(пробіг|odometer|odo).*", "", station, flags=re.I).strip()

    item = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "station": station,
        "gallons": gallons,
        "amount": amount,
        "odometer": odo,
    }
    data["fuel"].append(item)
    save_data(data)

    price = amount / gallons if amount and gallons else None
    msg = f"⛽ Заправка записана:\n📍 {station}\n💵 ${amount}\n⛽ {gallons} gal\n🛣️ Пробіг: {odo}"
    if price:
        msg += f"\n📌 Ціна/гал: ${price:.2f}"
    await update.message.reply_text(msg)


async def delivery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    text = update.message.text

    if not data.get("current_trip"):
        await update.message.reply_text("❌ Немає відкритого рейсу. Спочатку введи /pickup.")
        return

    odo = find_odometer(text)
    rate_match = re.search(r"(?:rate|ставка|ціна)\s*[:\-]?\s*\$?\s*(\d+(?:[.,]\d+)?)", text, re.I)
    rate = float(rate_match.group(1).replace(",", ".")) if rate_match else 0

    place = text.replace("/delivery", "").strip()
    place = re.sub(r"(пробіг|odometer|odo).*", "", place, flags=re.I)
    place = re.sub(r"(rate|ставка|ціна).*", "", place, flags=re.I).strip()

    trip = data["current_trip"]
    trip["delivery_place"] = place
    trip["delivery_odo"] = odo
    trip["delivery_time"] = datetime.now().isoformat(timespec="seconds")
    trip["rate"] = rate

    loaded_miles = None
    if trip.get("pickup_odo") and odo:
        loaded_miles = odo - trip["pickup_odo"]
    trip["loaded_miles"] = loaded_miles

    data["trips"].append(trip)
    data["current_trip"] = None
    save_data(data)

    await update.message.reply_text(
        f"✅ Рейс закрито:\n"
        f"{trip['pickup_place']} → {place}\n"
        f"🛣️ Loaded miles: {loaded_miles}\n"
        f"💵 Rate: ${trip['rate']}"
    )


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    total_fuel = sum(x.get("amount") or 0 for x in data["fuel"])
    total_gal = sum(x.get("gallons") or 0 for x in data["fuel"])
    total_rate = sum(x.get("rate") or 0 for x in data["trips"])
    total_miles = sum(x.get("loaded_miles") or 0 for x in data["trips"] if x.get("loaded_miles"))

    avg_price = total_fuel / total_gal if total_gal else 0
    fuel_per_mile = total_fuel / total_miles if total_miles else 0
    profit_after_fuel = total_rate - total_fuel

    await update.message.reply_text(
        f"📊 Підсумок:\n"
        f"📦 Рейсів: {len(data['trips'])}\n"
        f"🛣️ Loaded miles: {total_miles}\n"
        f"💵 Gross: ${total_rate:.2f}\n"
        f"⛽ Fuel: ${total_fuel:.2f}\n"
        f"⛽ Gallons: {total_gal:.2f}\n"
        f"📌 Avg fuel price: ${avg_price:.2f}/gal\n"
        f"⛽ Fuel per mile: ${fuel_per_mile:.2f}\n"
        f"✅ After fuel: ${profit_after_fuel:.2f}"
    )


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Я поки розумію команди:\n/pickup\n/fuel\n/delivery\n/summary")


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pickup", pickup))
    app.add_handler(CommandHandler("fuel", fuel))
    app.add_handler(CommandHandler("delivery", delivery))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    app.run_polling()


if __name__ == "__main__":
    main()
