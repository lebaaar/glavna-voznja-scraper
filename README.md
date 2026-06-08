# Glavna vožnja scraper

Scraper prostih terminov za opravljanje glavne vožnje v Sloveniji na podlagi podatkov iz [e-uprave](https://e-uprava.gov.si/si/javne-evidence/prosti-termini-zemljevid.html?lang=si#eyJwYWdlIjpbMF0sImZpbHRlcnMiOnsidHlwZSI6WyItIl0sImNhdCI6WyItIl0sIml6cGl0bmlDZW50ZXIiOlsiLTEiXSwibG9rYWNpamEiOlsiLTEiXSwib2Zmc2V0IjpbIjAiXSwic2VudGluZWxfdHlwZSI6WyJvayJdLCJzZW50aW5lbF9zdGF0dXMiOlsib2siXSwiaXNfYWpheCI6WyIxIl19fQ==).

## Uporaba
V `config.json` nastavi parametre, enake kot bi jih na spletni strani e-uprave:
- `preverjanjeZnanja`: `"voznja"` ali `"teorija"`.
- `kategorija`: kategorija vozniškega dovoljenja - ena izmed `AM, A1, A2, A, B1, B, BE, C1, C1E, C, CE, D1, D1E, D, DE, F, G`. Lahko je niz (`"A2"`) ali seznam, če želiš spremljati več kategorij hkrati, npr. `["A2", "A1", "B"]`.
- `obmocje`: številka Območja (`1`-`5`, glej spustni seznam "Izpitni center" na e-upravi), kjer želiš opravljati glavno vožnjo. Lahko je število (`1`) ali seznam, če želiš spremljati več območij hkrati, npr. `[1, 2, 3]`.
- `discordWebhookUrls`: URL Discord webhooka, na katerega naj scraper pošilja obvestila. Lahko je niz (`"https://discord.com/api/webhooks/..."`) ali seznam, če želiš obveščati več kanalov hkrati, npr. `["https://discord.com/api/webhooks/...", "https://discord.com/api/webhooks/..."]`.<br>Navodila za pridobitev webhook URL-ja najdeš [tukaj](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks).

### Poganjanje
`python main.py` preveri trenutno najboljše termine, pošlje Discord obvestilo o novih in si zapomni že najdene termine v `seen.json`, da te ob naslednjem zagonu ne obvešča o istih terminih znova.
<br>
Za redno preverjanje novih terminov scraper poganjaj periodično:

**Linux / macOS**<br>
Scraper poganjaj prek cron job-a:

1. Namesti scraper:
   ```bash
   git clone https://github.com/lebaaar/glavna-voznja-scraper.git
   cd glavna-voznja-scraper
   pip install -r requirements.txt
   ```
2. Nastavi `config.json` (glej zgoraj):
   ```bash
   cp config.example.json config.json
   ```
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

**Windows**<br>
Scraper poganjaj preko Task Scheduler. Navodila so skoraj enaka kot zgoraj, le da namesto cron job-a uporabiš Task Scheduler. Navodila za uporabo Task Schedulerja najdeš [tukaj](https://www.windowscentral.com/how-create-automated-task-using-task-scheduler-windows-10).

## Legal
Ta scraper je namenjen izključno za osebno uporabo in pomoč pri spremljanju prostih terminov za glavno vožnjo. Uporaba scraperja za množično zbiranje podatkov ali kakršnokoli drugo zlorabo je prepovedana. Avtor ne prevzema odgovornosti za kakršnekoli posledice, ki bi lahko nastale zaradi uporabe tega scraperja.