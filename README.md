# Glavna vožnja scraper

Scraper prostih terminov za opravljanje glavne vožnje v Sloveniji na podlagi podatkov iz [e-uprave](https://e-uprava.gov.si/si/javne-evidence/prosti-termini-zemljevid.html?lang=si#eyJwYWdlIjpbMF0sImZpbHRlcnMiOnsidHlwZSI6WyItIl0sImNhdCI6WyItIl0sIml6cGl0bmlDZW50ZXIiOlsiLTEiXSwibG9rYWNpamEiOlsiLTEiXSwib2Zmc2V0IjpbIjAiXSwic2VudGluZWxfdHlwZSI6WyJvayJdLCJzZW50aW5lbF9zdGF0dXMiOlsib2siXSwiaXNfYWpheCI6WyIxIl19fQ==).

## Uporaba
1. V `config.json` nastavi parametre, enake kot bi jih na spletni strani e-uprave:
   - `preverjanjeZnanja`: `"voznja"` ali `"teorija"`
   - `kategorija`: kategorija vozniškega dovoljenja (npr. `"A2"`).<br>
   Če želiš spremljati več območij, jih naštej v seznamu, npr. `["A2", "A1", "B"]`.
   - `obmocje`: številka Območja, kjer želiš opravljati glavno vožnjo. Številko območja lahko najdeš na spletni strani e-uprave.<br>
   Če želiš spremljati več območij, jih naštej v seznamu, npr. `[1, 2, 3]`.
   - `scraperIntervalMinutes`: Interval v minutah, kako pogosto naj scraper preverja nove termine. Minimum je 60 minut.
2. V `.env` datoteki nastavi `DISCORD_WEBHOOK_URL` na URL Discord webhooka.<br>Navodila za pridobitev webhook URL-ja najdeš [tukaj](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks).
3. Odloči se, kje želiš poganjati scraper - lahko ga poganjaš lokalno na svojem računalniku ali pa ga poganjaš preko GitHub Actions, da bo deloval neprekinjeno v oblaku. Navodila za obe možnosti najdeš spodaj.

### Lokalno poganjanje
1. Namesti scraper
   ```bash
   git clone https://github.com/lebaaar/glavna-voznja-scraper.git
   cd glavna-voznja-scraper
   pip install -r requirements.txt
   ```
2. Nastavi `config.json` in `.env` datoteko (glej zgoraj).
3. Zaženi scraper:
   ```bash
   python main.py
   ```
4. Scraper bo preverjal bo nove termine dokler ga ne ustaviš (npr. s `Ctrl+C`).

### Poganjanje preko GitHub Actions
1. Fork-aj ta repozitorij
2. V nastavitvah tvojega forka pojdi na "Secrets and variables" > "Actions" in dodaj nov secret z imenom `DISCORD_WEBHOOK_URL` in vrednostjo tvojega Discord webhook URL-ja.
3. V `config.json` nastavi željene parametre (glej zgoraj).
4. GitHub Actions bo samodejno zagnal scraper ob definiranem intervalu in preverjal nove termine. Rezultati bodo poslani na tvoj Discord kanal preko webhooka.