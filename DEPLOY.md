# Deploy del dashboard

La herramienta publicada no necesita correr Python. El pipeline deja una salida estatica en:

```text
site/dist/
  index.html
  data/reports/*.csv
```

Esa carpeta se puede publicar en cualquier hosting estatico:

- GitHub Pages
- Netlify
- Vercel
- Cloudflare Pages

El dashboard publicado consume los CSV desde:

```text
data/reports/*.csv
```

Por eso, si cambian los reports, alcanza con actualizar los CSV publicados junto al HTML.

## Flujo local

```bash
python3 run_all.py
```

Ese comando regenera:

```text
data/stage/
data/clean/
data/reports/
site/dist/
```

## GitHub Pages

El repo incluye el workflow:

```text
.github/workflows/pages.yml
```

Ese workflow publica automaticamente la carpeta:

```text
site/dist
```

Una vez subido a GitHub, el link queda con este formato:

```text
https://franferraro.github.io/Sawy-TostaderoRuta9/
```
