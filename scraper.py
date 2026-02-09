import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3
import sqlite3
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

class PlanszeoTracker:
  def __init__(self):
    self.session = requests.Session()
    self.session.headers.update({
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

  def scrape_planszeo(self):
    """Scrapuje wszystkie gry z Planszeo"""
    gry = []
    # Strona 1-5 (najpopularniejsze)
    for page in range(1, 6):
      url = f"https://planszeo.pl/gry-planszowe?page={page}"
      resp = self.session.get(url)
      soup = BeautifulSoup(resp.text, 'html.parser')

      for item in soup.select('.product-item, .gra-item'):  # Dostosuj selektor
        try:
          nazwa = item.select_one('h3, .title').text.strip()
          cena_str = item.select_one('.price, .cena').text.strip()
          cena = float(cena_str.replace(' zł', '').replace(',', '.'))

          # BGG link
          bgg_a = item.select_one('a[href*="boardgamegeek"]')
          bgg_url = bgg_a['href'] if bgg_a else None

          # Status specjalny
          opis = item.get_text().lower()
          koniec_serii = any(x in opis for x in ['końcówka', 'ostatnie', 'clearance'])
          dodruk = any(x in opis for x in ['dodruk', 'reedycja', 'nowe wydanie'])

          gry.append({
            'nazwa': nazwa,
            'cena': cena,
            'bgg_url': bgg_url,
            'koncowka_serii': koniec_serii,
            'dodruk': dodruk,
            'data': datetime.now(),
            'sklep': 'Planszeo'  # lub konkretny sklep
          })
        except:
          continue

    return pd.DataFrame(gry)

  def get_bgg_stats(self, bgg_url):
    """BGG API - rating i rank"""
    if not bgg_url:
      return {'rating': 0, 'rank': 9999}

    try:
      # BGG XML API2 [web:8]
      bgg_id = bgg_url.split('thing/')[1].split('?')[0]
      api_url = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}&stats=1"
      resp = self.session.get(api_url)

      # Parsowanie (uproszczone)
      soup = BeautifulSoup(resp.text, 'xml')
      rating = float(soup.find('average') or 0)
      rank = int(soup.find('bayesaverage') or 9999)
      return {'rating': rating, 'rank': rank}
    except:
      return {'rating': 0, 'rank': 9999}

  def analyze_prices(self, df):
    """Analizuje okazje i trendy cenowe"""
    # Historia 90 dni
    conn = sqlite3.connect('prices.db')
    hist_90 = pd.read_sql('SELECT * FROM prices WHERE data > datetime("now", "-90 days")', conn)
    conn.close()

    # Średnie ceny
    srednie = df.groupby('nazwa')['cena'].mean().to_dict()

    results = []
    for _, gra in df.iterrows():
      stats = self.get_bgg_stats(gra['bgg_url'])

      # Ocena okazji
      srednia_cena = srednie.get(gra['nazwa'], gra['cena'])
      okazja_score = (stats['rating'] * 10) / (gra['cena'] / srednia_cena + 1)

      # Historia dla tej gry
      hist_gra = hist_90[hist_90['nazwa'] == gra['nazwa']]
      cena_min_90 = hist_gra['cena'].min() if len(hist_gra) > 0 else gra['cena']

      result = {
        **gra.to_dict(),
        **stats,
        'srednia_cena': srednia_cena,
        'okazja_score': okazja_score,
        'cena_min_90': cena_min_90,
        'trend': '⬇️' if cena_min_90 < srednia_cena * 0.9 else '➡️'
      }
      results.append(result)

    return pd.DataFrame(results)

  def find_best_deals(self, df, top_n=10):
    """Znajduje najlepsze okazje"""
    # TOP 3 kategorie:
    top_bgg = df[(df['rating'] >= 8.0) & (df['cena'] < df['srednia_cena'] * 0.9)].sort_values('okazja_score', ascending=False)
    koncowki = df[df['koncowka_serii'] == True].sort_values('rating', ascending=False)
    dodruki = df[df['dodruk'] == True].sort_values('cena')

    return {
      'top_bgg': top_bgg.head(top_n),
      'koncowki_serii': koncowki.head(top_n),
      'dodruki': dodruki.head(top_n)
    }

  def send_alerts(self, deals, email_to='twoj@email.pl'):
    """Wysyła email z okazjami"""
    if all(len(df) == 0 for df in deals.values()):
      return

    msg = MimeMultipart()
    msg['Subject'] = f"🕹️ Planszeo Okazje {datetime.now().strftime('%d/%m')}"
    msg['To'] = email_to

    html = """
        <h2>Planszeo Price Tracker - Nowe okazje!</h2>
        """

    for kategoria, df in deals.items():
      if len(df) > 0:
        html += f"<h3>{kategoria.replace('_', ' ').title()}</h3>"
        html += df[['nazwa', 'cena', 'rating', 'okazja_score']].round(2).to_html()

    msg.attach(MimeText(html, 'html'))

    # Gmail SMTP (skonfiguruj secrets w GitHub)
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login('your-bot@gmail.com', 'your-app-password')
    server.send_message(msg)
    server.quit()

# MAIN EXECUTION
tracker = PlanszeoTracker()

print("🔍 Scrapuję Planszeo...")
raw_data = tracker.scrape_planszeo()

print("📊 Analizuję BGG + ceny...")
analyzed = tracker.analyze_prices(raw_data)

# Zapisz wszystko
analyzed.to_sql('prices', sqlite3.connect('prices.db'), if_exists='append', index=False)

print("🎯 Szukam okazji...")
deals = tracker.find_best_deals(analyzed)

# Generuj raporty
deals_flat = pd.concat(deals.values(), keys=deals.keys())
deals_flat.to_csv('data/okazje.csv')
deals_flat.to_html('data/dashboard.html')

# Historia 90 dni z wykresami (prosty HTML)
hist_90 = pd.read_sql('SELECT * FROM prices WHERE data > datetime("now", "-90 days") ORDER BY nazwa, data', sqlite3.connect('prices.db'))
hist_90.pivot(index='data', columns='nazwa', values='cena').plot().savefig('data/historia_90dni.png')

# Alert tylko jeśli są dobre okazje
if deals['top_bgg'].shape[0] > 0:
  tracker.send_alerts(deals)

print(f"✅ Znaleziono okazji: {sum(len(df) for df in deals.values())}")
print("📁 Sprawdź: data/okazje.csv + data/dashboard.html")
