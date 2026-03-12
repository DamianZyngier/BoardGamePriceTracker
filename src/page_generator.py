import os
from datetime import datetime
from typing import List, Dict, Any
from src.config import settings

def generate_html(
    last_run: str,
    last_new_deals_date: str,
    thresholds: str,
    deals: List[Dict[str, Any]]
) -> str:
    """Generates the static index.html content."""
    
    deals_html = ""
    if not deals:
        deals_html = "<p>No new deals found in the last run.</p>"
    else:
        deals_html = """
        <table border="1" cellpadding="5" cellspacing="0">
            <thead>
                <tr>
                    <th>Nazwa</th>
                    <th>Cena (zł)</th>
                    <th>Obniżka</th>
                    <th>Planszeo Rank</th>
                    <th>BGG Rank</th>
                    <th>BGG Rating</th>
                    <th>Alert?</th>
                </tr>
            </thead>
            <tbody>
        """
        for d in deals:
            alert_class = "alert" if d.get('passed_threshold', False) else ""
            alert_text = "YES" if d.get('passed_threshold', False) else "NO"
            
            deals_html += f"""
                <tr class="{alert_class}">
                    <td><a href="{d.get('planszeo_url', '#')}" target="_blank">{d.get('nazwa', 'N/A')}</a></td>
                    <td>{d.get('cena', 0):.2f}</td>
                    <td>{d.get('obnizka', '0%')}</td>
                    <td>{d.get('planszeo_rank', 'N/A')}</td>
                    <td>{d.get('bgg_rank', 'N/A')}</td>
                    <td>{d.get('bgg_rating', 'N/A')}</td>
                    <td align="center"><strong>{alert_text}</strong></td>
                </tr>
            """
        deals_html += "</tbody></table>"

    html_template = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BoardGamePriceTracker - Status</title>
    <style>
        body {{ font-family: sans-serif; margin: 20px; line-height: 1.6; color: #333; }}
        h1 {{ color: #2c3e50; }}
        .info-section {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #dee2e6; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th {{ background: #e9ecef; text-align: left; padding: 10px; }}
        td {{ padding: 10px; border-bottom: 1px solid #dee2e6; }}
        .alert {{ background-color: #d4edda; font-weight: bold; }}
        .threshold-info {{ font-size: 0.9em; color: #666; font-style: italic; }}
        a {{ color: #007bff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>BoardGamePriceTracker</h1>
    
    <div class="info-section">
        <p><strong>🔗 Link do okazji:</strong> <a href="{settings.PLANSZEO_DEALS_URL}" target="_blank">Planszeo Okazje</a></p>
        <p><strong>🕒 Ostatnie sprawdzenie (Warszawa):</strong> {last_run}</p>
        <p><strong>🔥 Ostatnio znalezione nowe okazje:</strong> {last_new_deals_date}</p>
    </div>

    <div class="info-section">
        <h3>🔔 Progi powiadomień e-mail:</h3>
        <pre class="threshold-info">{thresholds}</pre>
    </div>

    <h2>🆕 Ostatnio znalezione nowe okazje:</h2>
    {deals_html}

    <footer style="margin-top: 40px; font-size: 0.8em; color: #999;">
        Generowane automatycznie przez GitHub Actions.
    </footer>
</body>
</html>
"""
    return html_template

def save_page(html_content: str):
    """Saves the index.html file to the docs directory."""
    docs_dir = 'docs'
    os.makedirs(docs_dir, exist_ok=True)
    with open(os.path.join(docs_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)
