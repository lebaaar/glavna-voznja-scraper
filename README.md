# Glavna vožnja scraper

Scraper prostih terminov za opravljanje glavne vožnje v Sloveniji na podlagi podatkov iz [e-uprave](https://e-uprava.gov.si/si/javne-evidence/prosti-termini-zemljevid.html?lang=si#eyJwYWdlIjpbMF0sImZpbHRlcnMiOnsidHlwZSI6WyItIl0sImNhdCI6WyItIl0sIml6cGl0bmlDZW50ZXIiOlsiLTEiXSwibG9rYWNpamEiOlsiLTEiXSwib2Zmc2V0IjpbIjAiXSwic2VudGluZWxfdHlwZSI6WyJvayJdLCJzZW50aW5lbF9zdGF0dXMiOlsib2siXSwiaXNfYWpheCI6WyIxIl19fQ==).

## Uporaba
1. V `config.json` nastavi parametre, enake kot bi jih na spletni strani e-uprave:
   - `preverjanjeZnanja`: `"voznja"`, `"teorija"` ali `"vse"` (oboje).
   - `kategorija`: kategorija vozniškega dovoljenja - ena izmed `AM, A1, A2, A, B1, B, BE, C1, C1E, C, CE, D1, D1E, D, DE, F, G`. Lahko je niz (`"A2"`) ali seznam, če želiš spremljati več kategorij hkrati, npr. `["A2", "A1", "B"]`.
   - `obmocje`: številka Območja (`1`-`5`, glej spustni seznam "Izpitni center" na e-upravi), kjer želiš opravljati glavno vožnjo. Lahko je število (`1`) ali seznam, če želiš spremljati več območij hkrati, npr. `[1, 2, 3]`.
   - `scraperIntervalMinutes`: Interval v minutah, kako pogosto naj scraper preverja nove termine. Minimum je 15 minut. (Pri lokalnem poganjanju to določa, kako pogosto se scraper zažene v zanki; pri GitHub Actions to ne vpliva na urnik - ta je določen v `.github/workflows/scraper.yml`, glej spodaj.)
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
4. Scraper bo preverjal nove termine dokler ga ne ustaviš (npr. s `Ctrl+C`). Že najdene termine si zapomni v datoteko `seen_termini.json`, da te ob naslednjem preverjanju ne obvešča o istih terminih znova.

### Poganjanje preko GitHub Actions
1. Fork-aj ta repozitorij
2. V nastavitvah tvojega forka pojdi v *Settings* > *Secrets and variables* > *Actions* in dodaj nov secret z imenom `DISCORD_WEBHOOK_URL` z vrednostjo tvojega Discord webhook URL-ja.
3. V `config.json` nastavi željene parametre (glej zgoraj). Spremembe commitaj.
4. Po potrebi prilagodi urnik (`cron`) v [`.github/workflows/scraper.yml`](.github/workflows/scraper.yml) - privzeto je nastavljen na vsakih 15 minut (`*/15 * * * *`), kar je tudi minimalni interval, ki ga GitHub Actions zanesljivo podpira.
5. GitHub Actions bo samodejno zagnal scraper ob definiranem intervalu (lahko ga sprožiš tudi ročno preko zavihka *Actions* > *Glavna vožnja scraper* > *Run workflow*) in preverjal nove termine. Rezultati bodo poslani na tvoj Discord kanal preko webhooka.

   Scraper si med zagoni zapomni že najdene termine (`seen_termini.json`, shranjen preko GitHub Actions cache-a), zato te o istem terminu ne bo obveščal v nedogled.

## Legal
Ta scraper je namenjen izključno za osebno uporabo in pomoč pri spremljanju prostih terminov za glavno vožnjo. Uporaba scraperja za množično zbiranje podatkov ali kakršnokoli drugo zlorabo je prepovedana. Avtor ne prevzema odgovornosti za kakršnekoli posledice, ki bi lahko nastale zaradi uporabe tega scraperja.