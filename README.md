# ts3bot-plugins

Pluginy (služby) pro TeamSpeak bota. Každá složka je jeden plugin. Bot si ho stáhne přímo odsud,
nic se nekopíruje ručně a bot se kvůli tomu nerestartuje.

## Instalace (v TeamSpeaku, zpráva botovi)

```
!service import                       seznam pluginů v knihovně
!service import badges                nainstaluje plugin z knihovny (ukáže co dělá, zeptá se, spustí ho na zkoušku)
!service import badges notify=me,Tisi  … rovnou s nastavením
!service update                       které služby mají novější verzi
!service update badges                aktualizuje (nastavení zůstane; když chce víc práv, znovu se zeptá)
!service set badges notify me         změna nastavení
```

Funguje i jakékoli jiné veřejné repo:

```
!service import github.com/<účet>/<repo>                 plugin v kořeni repa
!service import github.com/<účet>/<repo>/<složka>        plugin ve složce
!service import github.com/<účet>/<repo>/<složka>@v1.2   konkrétní verze (tag, větev, commit)
```

…nebo odkaz zkopírovaný z prohlížeče (`https://github.com/<účet>/<repo>/tree/main/<složka>`), případně odkaz
na jeden soubor (gist, pastebin) s hlavičkou `# ts3bot-service`.

## Kostra pluginu

```
muj-plugin/
├── ts3bot.yml          co to je (povinné)
├── main.py             co se spouští (nebo main.sh / main.js)
├── requirements.txt    balíčky pro Python (volitelné)
├── Dockerfile          volitelné: cokoli jiného (Go, Rust, Java…) - bot image sestaví sám
└── …                   další soubory, které plugin potřebuje
```

Hotová šablona je ve složce [`template/`](template/).

### ts3bot.yml

```yaml
name: muj-plugin                  # název služby (povinné)
description: Co dělá, jednou větou.
version: 1.0.0                    # ukazuje se při instalaci a aktualizaci
run:
  cron: "*/15 * * * *"            # kdy běží (místní čas) …
  command: mujplugin              # … a/nebo na příkaz !mujplugin …
  daemon: true                    # … nebo pořád (nejde s cron/command)
network: true                     # smí na internet (jinak ne)
tools: [say_channel, message_user] # co smí v botovi - nic jiného
deps: [requests]                  # balíčky (Python), nebo requirements.txt
main: main.py                     # co se spouští (výchozí main.py / main.sh / main.js)
image: ghcr.io/ty/neco:1          # nebo hotový image (nebo Dockerfile vedle)
settings:                         # vlastní nastavení → proměnná SVC_<KLÍČ>
  mesto: pro jaké město
  notify:
    type: users                   # lidi - bot je uloží podle UID (nejde podvrhnout jménem)
    description: komu psát
```

## Co má plugin k dispozici

- **Bota**: `ts-tool <nástroj> '<json>'` (v obrazech bota), vrací `ok: …` / `error: …`. Jen nástroje z `tools`.
  V jiném image totéž přes HTTP: `POST http://localhost/tool/<nástroj>` přes unix socket `$TS_BOT_SOCK`,
  s hlavičkou `X-Bot-Token: $TS_BOT_TOKEN` - viz [`examples/docker-hello`](examples/docker-hello/).
- **Nastavení**: proměnné `SVC_<KLÍČ>` (např. `SVC_NOTIFY`).
- **`/data/`**: jediné místo, kam smí zapisovat; přežije další běhy i restart bota.
- **Výstup** (`print`) jde lidem: při plánovaném běhu adminům, na příkaz tomu, kdo ho napsal. Když není co
  říct, nic nevypisuj.

## Hranice (sandbox)

Každý běh je zamčený kontejner: nevidí server ani jeho soubory, nemá porty ven, na internet jen s
`network: true`, nejvýš 2 minuty a 256 MB na běh (daemon běží pořád). Plugin nikdy nesmí víc než ten,
kdo ho nainstaloval.

## Pluginy

| Plugin | Co dělá |
|---|---|
| [badges](badges/) | Hlídá nové TeamSpeak badges a jejich kódy (oficiální seznam + vlákno na fóru); do kanálu, nebo soukromě vybraným lidem podle UID. |
| [cs2-news](cs2-news/) | Nové články o CS2 ze Steamu do kanálu. |
| [examples/docker-hello](examples/docker-hello/) | Ukázka pluginu ve vlastním Docker image. |
