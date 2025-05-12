import telebot
import time
import threading
import yfinance as yf
import requests
import os
import datetime
import feedparser

TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

bot = telebot.TeleBot(TOKEN)

def analisi_titolo(nome, ticker_str):
    ticker = yf.Ticker(ticker_str)
    dati = ticker.history(period="60d")
    chiusure = dati["Close"]
    prezzo_attuale = chiusure.iloc[-1]
    media_30gg = chiusure[-30:].mean()
    media_7gg = chiusure[-7:].mean()
    variazione = ((prezzo_attuale - chiusure.iloc[-30]) / chiusure.iloc[-30]) * 100

    if prezzo_attuale < media_30gg and media_7gg < media_30gg and variazione < -5:
        valutazione = "Potrebbe essere un buon momento per COMPRARE"
        termometro = "POSITIVO"
    elif prezzo_attuale > media_30gg and media_7gg > media_30gg and variazione > 5:
        valutazione = "Prezzo alto, forse meglio ASPETTARE"
        termometro = "NEGATIVO"
    else:
        valutazione = "Prezzo stabile, continua a OSSERVARE"
        termometro = "NEUTRO"

    return {
        "nome": nome,
        "prezzo": prezzo_attuale,
        "variazione": variazione,
        "valutazione": valutazione,
        "termometro": termometro
    }

def notizie_google(titolo):
    url = f"https://news.google.com/rss/search?q={titolo}+stock&hl=it&gl=IT&ceid=IT:it"
    r = requests.get(url)
    if r.status_code != 200:
        return "Notizie non disponibili"
    from xml.etree import ElementTree as ET
    root = ET.fromstring(r.text)
    items = root.findall(".//item")[:2]
    titoli = [item.find("title").text for item in items]
    return "\n- " + "\n- ".join(titoli)

def eventi_macroeconomici():
    url = 'https://nfs.faireconomy.media/ff_calendar_thisweek.xml'
    now = datetime.datetime.utcnow()
    feed = feedparser.parse(url)
    eventi_oggi = []
    for entry in feed.entries:
        published = entry.get("published_parsed")
        if published:
            data_evento = datetime.datetime(*published[:6])
            if data_evento.date() == now.date():
                title = entry.get("title", "Evento")
                eventi_oggi.append(f"- {title}")
    if not eventi_oggi:
        return "Nessun evento economico rilevante oggi."
    messaggio = "**[Avvisi Economici di Oggi]**\n" + "\n".join(eventi_oggi)
    return messaggio

def invia_report_orario():
    while True:
        try:
            assets = [
                analisi_titolo("NVIDIA", "NVDA"),
                analisi_titolo("ETF Globale VWCE", "VWCE.DE"),
                analisi_titolo("ETF Obbligazionario IBTS", "IBTS.MI"),
                analisi_titolo("Ethereum", "ETH-USD")
            ]
            livelli = {"POSITIVO": 1, "NEUTRO": 0, "NEGATIVO": -1}
            punteggio = sum([livelli[a["termometro"]] for a in assets])
            if punteggio >= 2:
                termometro_finale = "PORTAFOGLIO FORTE"
            elif punteggio <= -2:
                termometro_finale = "PORTAFOGLIO A RISCHIO"
            else:
                termometro_finale = "PORTAFOGLIO NEUTRO"

            messaggio = f"**[Analisi Oraria]**\n\n"
            for a in assets:
                notizie = notizie_google(a["nome"])
                messaggio += (
                    f"*{a['nome']}*\n"
                    f"- Prezzo: {a['prezzo']:.2f} $\n"
                    f"- Variazione 30gg: {a['variazione']:.2f}%\n"
                    f"- Valutazione: {a['valutazione']}\n"
                    f"- Notizie:{notizie}\n\n"
                )
            messaggio += f"**TERMOMETRO PORTAFOGLIO:** {termometro_finale}\n\n"
            messaggio += eventi_macroeconomici()
            bot.send_message(CHAT_ID, messaggio, parse_mode='Markdown')
            time.sleep(3600)

        except Exception as e:
            bot.send_message(CHAT_ID, f"Errore nel report: {e}")
            time.sleep(3600)

# Avvia il bot e il ciclo parallelo
threading.Thread(target=invia_report_orario).start()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Ciao! Bot investitore attivo ogni ora!")

print("Bot avviato...")
bot.polling()
