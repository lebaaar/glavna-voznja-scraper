# Glavna vožnja scraper

Scraper prostih terminov za opravljanje glavne vožnje v Sloveniji na podlagi podatkov iz [e-uprave](https://e-uprava.gov.si/si/javne-evidence/prosti-termini-zemljevid.html?lang=si#eyJwYWdlIjpbMF0sImZpbHRlcnMiOnsidHlwZSI6WyItIl0sImNhdCI6WyItIl0sIml6cGl0bmlDZW50ZXIiOlsiLTEiXSwibG9rYWNpamEiOlsiLTEiXSwib2Zmc2V0IjpbIjAiXSwic2VudGluZWxfdHlwZSI6WyJvayJdLCJzZW50aW5lbF9zdGF0dXMiOlsib2siXSwiaXNfYWpheCI6WyIxIl19fQ==).

## Uporaba
1. V `config.json` nastavi parametre, enake kot bi jih na spletni strani e-uprave:
   - `preverjanjeZnanja`: `"voznja"` ali `"teorija"`.
   - `kategorija`: kategorija vozniškega dovoljenja - ena izmed `AM, A1, A2, A, B1, B, BE, C1, C1E, C, CE, D1, D1E, D, DE, F, G`. Lahko je niz (`"A2"`) ali seznam, če želiš spremljati več kategorij hkrati, npr. `["A2", "A1", "B"]`.
   - `obmocje`: številka Območja (`1`-`5`, glej spustni seznam "Izpitni center" na e-upravi), kjer želiš opravljati glavno vožnjo. Lahko je število (`1`) ali seznam, če želiš spremljati več območij hkrati, npr. `[1, 2, 3]`.
2. V `.env` datoteki nastavi `DISCORD_WEBHOOK_URL` na URL Discord webhooka.<br>Navodila za pridobitev webhook URL-ja najdeš [tukaj](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks).

### Poganjanje
`python main.py` opravi en sam zagon - preveri trenutno najboljše termine, pošlje Discord obvestilo o novih in se zaključi (že najdene termine si zapomni v `seen.json`, da te ob naslednjem zagonu ne obvešča o istih terminih znova). Za redno preverjanje scraper poganjaj periodično prek cron job-a:

1. Namesti scraper
   ```bash
   git clone https://github.com/lebaaar/glavna-voznja-scraper.git
   cd glavna-voznja-scraper
   pip install -r requirements.txt
   ```
2. Nastavi `config.json` in `.env` datoteko (glej zgoraj).
3. Preizkusi scraper:
   ```bash
   python main.py
   ```
4. Dodaj cron job:
   ```bash
   crontab -e
   ```
   in dodaj:
   ```cron
   */15 * * * * cd /pot/do/glavna-voznja-scraper && /usr/bin/python3 main.py >> scraper.log 2>&1
   ```
   Pot (`/pot/do/glavna-voznja-scraper`) in pot do Python interpreterja prilagodi svojemu sistemu.
   Pot do Python interpreterja lahko preveriš z `which python3`.

## Legal
Ta scraper je namenjen izključno za osebno uporabo in pomoč pri spremljanju prostih terminov za glavno vožnjo. Uporaba scraperja za množično zbiranje podatkov ali kakršnokoli drugo zlorabo je prepovedana. Avtor ne prevzema odgovornosti za kakršnekoli posledice, ki bi lahko nastale zaradi uporabe tega scraperja.