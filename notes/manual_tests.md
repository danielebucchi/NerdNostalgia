# Manual tests — Articles API

Test manuali per la Fase 1 (CRUD articoli + filtri + ricerca full-text).

## Setup

```bash
# Se la porta 5432 e' occupata sull'host (es. devtrix Domotz),
# creare un override locale che esponga il db sulla 5433:
cat > docker-compose.local.yml <<'EOF'
services:
  db:
    ports: !override
      - "5433:5432"
EOF

docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
# altrimenti:
# docker compose up -d --build
```

Verifica health:

```bash
curl -s http://localhost:7373/status
# {"status":"healthy","database":"connected"}
```

## Test E2E

```bash
BASE=http://localhost:7373

# 1) Crea utente
USER_ID=$(curl -s -X POST $BASE/api/users/ -H 'Content-Type: application/json' -d '{
  "username":"dani",
  "email":"dani@nerdnostalgia.it",
  "password":"secret1",
  "full_name":"Daniele",
  "role":"ADMIN"
}' | jq -r '.id')

# 2) Crea articolo
ART_ID=$(curl -s -X POST $BASE/api/articles/ -H 'Content-Type: application/json' -d "{
  \"user_id\": $USER_ID,
  \"title\": \"Charizard 1st Edition Holo Base Set\",
  \"description\": \"Carta Pokemon prima edizione, condizioni eccellenti\",
  \"price\": 1200.00,
  \"category\": \"pokemon-cards\",
  \"condition\": \"USED\",
  \"brand\": \"Wizards of the Coast\",
  \"sku\": \"PKM-CHAR-1ED-001\",
  \"images\": [\"https://example.com/charizard.jpg\"]
}" | jq -r '.id')

# 3) Lista
curl -s $BASE/api/articles/ | jq

# 4) Filtri
curl -s "$BASE/api/articles/?category=pokemon-cards&min_price=1000" | jq
curl -s "$BASE/api/articles/?condition=USED&max_price=100" | jq
curl -s "$BASE/api/articles/?status=DRAFT" | jq

# 5) Ricerca full-text (italiano)
curl -s "$BASE/api/articles/?search=charizard" | jq
curl -s "$BASE/api/articles/?search=carta" | jq

# 6) PATCH prezzo
curl -s -X PATCH $BASE/api/articles/$ART_ID -H 'Content-Type: application/json' -d '{"price": 1500.00}' | jq

# 7) Lifecycle
curl -s -X POST $BASE/api/articles/$ART_ID/publish | jq '{status,published_at}'
curl -s -X POST $BASE/api/articles/$ART_ID/sell | jq '{status,sold_at}'
curl -s -X POST $BASE/api/articles/$ART_ID/archive | jq '{status}'

# 8) Immagini
curl -s -X POST $BASE/api/articles/$ART_ID/images \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com/charizard2.jpg"}' | jq '.images'

curl -s -X DELETE "$BASE/api/articles/$ART_ID/images?url=https://example.com/charizard.jpg" | jq '.images'

# 9) Errori
curl -s -o /dev/null -w "%{http_code}\n" $BASE/api/articles/9999  # 404
curl -s -X POST $BASE/api/articles/ -H 'Content-Type: application/json' -d '{
  "user_id": 9999, "title": "x", "price": 1
}' -w "\n%{http_code}\n"  # 400 — user inesistente

# SKU duplicato
curl -s -X POST $BASE/api/articles/ -H 'Content-Type: application/json' -d "{
  \"user_id\": $USER_ID,
  \"title\": \"Dup\", \"price\": 1, \"sku\": \"PKM-CHAR-1ED-001\"
}" -w "\n%{http_code}\n"  # 400

# 10) Delete
curl -s -X DELETE $BASE/api/articles/$ART_ID -w "%{http_code}\n"  # 204
```

## Esito atteso

- Tutti gli endpoint rispondono con i codici sopra
- `published_at` / `sold_at` vengono popolati automaticamente quando lo status cambia
- La ricerca full-text usa l'indice GIN `idx_articles_search` (italiano) creato da `02_articles.sql`
- L'ordinamento di default e' `created_at DESC`

## Cleanup

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml down -v
rm -f docker-compose.local.yml
```

---

# Manual tests — Auth JWT (NN-003)

## Routing pubblico vs admin-only

| Endpoint | Auth |
|----------|------|
| `POST /api/users/` | pubblico (signup, fa hash bcrypt) |
| `GET /api/users/*`, `PATCH /api/users/{id}`, `DELETE /api/users/{id}` | admin-only |
| `POST /api/auth/login`, `GET /api/auth/me` | login form-data, /me richiede Bearer |
| `GET /api/articles/`, `/api/articles/{id}`, `/api/articles/sku/{sku}` | pubblico (vetrina) |
| `POST/PATCH/DELETE /api/articles/...`, `publish/sell/archive/images` | admin-only |

## Test E2E auth

```bash
BASE=http://localhost:7373

# 1) Signup admin (la password viene hashata con bcrypt lato server)
curl -s -X POST $BASE/api/users/ -H 'Content-Type: application/json' -d '{
  "username":"dani","email":"dani@nerdnostalgia.it","password":"secret1",
  "full_name":"Daniele","role":"ADMIN"
}' | jq

# 2) Login form-data (OAuth2 password flow)
TOKEN=$(curl -s -X POST $BASE/api/auth/login \
  -d 'username=dani&password=secret1' \
  -H 'Content-Type: application/x-www-form-urlencoded' | jq -r '.access_token')

# 3) /me col token
curl -s $BASE/api/auth/me -H "Authorization: Bearer $TOKEN" | jq

# 4) Endpoint protetto — articolo creato come admin
curl -s -X POST $BASE/api/articles/ \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"user_id":1,"title":"Test","price":10,"sku":"T-1"}' | jq

# 5) Senza token → 401
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/api/articles/ \
  -H 'Content-Type: application/json' -d '{"user_id":1,"title":"x","price":1}'

# 6) Con token USER (non admin) → 403
curl -s -X POST $BASE/api/users/ -H 'Content-Type: application/json' -d '{
  "username":"mario","email":"mario@nerd.it","password":"pwmario","role":"USER"
}' > /dev/null
TOKEN_USER=$(curl -s -X POST $BASE/api/auth/login \
  -d 'username=mario&password=pwmario' \
  -H 'Content-Type: application/x-www-form-urlencoded' | jq -r '.access_token')
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/api/articles/ \
  -H "Authorization: Bearer $TOKEN_USER" \
  -H 'Content-Type: application/json' \
  -d '{"user_id":2,"title":"hack","price":1}'

# 7) Token invalido → 401
curl -s -o /dev/null -w '%{http_code}\n' $BASE/api/auth/me \
  -H 'Authorization: Bearer notatoken'

# 8) Vetrina pubblica resta accessibile senza token
curl -s -o /dev/null -w '%{http_code}\n' $BASE/api/articles/
```

## Configurazione

Variabili env in `.env` (vedi `.env.example`):

- `JWT_SECRET_KEY` — in prod generare con `openssl rand -hex 32`
- `JWT_ALGORITHM` — default `HS256`
- `JWT_EXPIRE_MINUTES` — durata token in minuti (default `60`)

## Bootstrap admin

Il primo admin va creato via `POST /api/users/` (pubblico) finche' il signup
non viene blindato in una fase successiva. Subito dopo, le rotte `/api/users/*`
in lettura/scrittura diventano accessibili solo con token admin.

---

# Manual tests — Images upload (NN-004)

## Endpoint

- `POST /api/articles/{id}/upload-image` — multipart/form-data, campo `file`.
  Salva su `${APP_TMP_DIR}/uploads/articles/{id}/{uuid}.{ext}` e aggiunge
  l'URL pubblico a `article.images`. Admin-only.
- `DELETE /api/articles/{id}/images?url=...` — rimuove URL dall'array; se
  l'URL e' interno al nostro storage cancella anche il file su disco.
- `DELETE /api/articles/{id}` — cancella articolo + intera cartella uploads
  dell'articolo.
- `GET /static/articles/{id}/{filename}` — servito da FastAPI StaticFiles.

Validazioni:
- Content-type ammessi: `image/jpeg`, `image/png`, `image/webp`, `image/gif`.
- Dimensione massima: `MAX_UPLOAD_SIZE_MB` (default 5).

## Test E2E

```bash
BASE=http://localhost:7373

# PNG 1x1 valido di test
python3 -c "
import base64
open('/tmp/test.png','wb').write(base64.b64decode(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII='
))
"

TOKEN=$(curl -s -X POST $BASE/api/auth/login \
  -d 'username=dani&password=secret1' \
  -H 'Content-Type: application/x-www-form-urlencoded' | jq -r '.access_token')

# Upload
curl -s -X POST $BASE/api/articles/1/upload-image \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test.png;type=image/png" | jq '.images'

# Senza token → 401
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/api/articles/1/upload-image \
  -F "file=@/tmp/test.png;type=image/png"

# Content-type non ammesso → 400
echo "not an image" > /tmp/test.txt
curl -s -X POST $BASE/api/articles/1/upload-image \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test.txt;type=text/plain" -w "\n%{http_code}\n"

# Dimensione > limite → 400 (richiede file >5MB, opzionale)
# dd if=/dev/urandom of=/tmp/big.png bs=1M count=6
# curl -s -X POST $BASE/api/articles/1/upload-image -H "Authorization: Bearer $TOKEN" \
#   -F "file=@/tmp/big.png;type=image/png" -w "\n%{http_code}\n"
```

## Configurazione

Variabili env (vedi `.env.example`):

- `APP_TMP_DIR` — directory base degli upload (default `/tmp/nerdnostalgia`)
- `BASE_URL` — usato per costruire gli URL pubblici (default `http://localhost:7373`)
- `MAX_UPLOAD_SIZE_MB` — limite di dimensione per file (default 5)

## Note

- I file vengono salvati come `{uuid}.{ext}` per evitare path traversal e
  conflitti tra upload dello stesso nome.
- La directory `uploads/` deve essere persistente: il `docker-compose.yml`
  monta `./tmp:/tmp/nerdnostalgia`.
- In produzione, sostituire lo static FS con un object store (es. S3/R2/MinIO)
  cambiando l'implementazione di `utils/storage.py` senza toccare l'API.

---

# Manual tests — Inquiries (NN-005)

## Endpoint

- `POST /api/inquiries/` — pubblico. Submit di una richiesta di contatto.
  Campi: `name`, `email`, `message` obbligatori. `article_id`, `phone`,
  `subject` opzionali.
- `GET /api/inquiries/` — admin-only. Lista con filtri `status`,
  `article_id`, `email`, paginazione.
- `GET /api/inquiries/{id}` — admin-only. Auto-marca come `READ` se era `NEW`.
- `PATCH /api/inquiries/{id}` — admin-only. Aggiorna `status` e/o
  `admin_notes`. Passando `status=REPLIED` popola `replied_at`.
- `DELETE /api/inquiries/{id}` — admin-only.

## Test E2E

```bash
BASE=http://localhost:7373

# 1) Submit pubblico (no token)
curl -s -X POST $BASE/api/inquiries/ -H 'Content-Type: application/json' -d '{
  "name":"Mario Rossi","email":"mario@test.it",
  "subject":"Ricerca Game Boy Advance",
  "message":"Ciao, vorrei sapere se hai per caso un Game Boy Advance SP."
}' | jq

# 2) Submit con article_id
curl -s -X POST $BASE/api/inquiries/ -H 'Content-Type: application/json' -d '{
  "article_id": 6, "name":"Luigi","email":"luigi@test.it",
  "message":"Salve, e ancora disponibile?"
}' | jq

# 3) Senza token (GET) → 401
curl -s -o /dev/null -w '%{http_code}\n' $BASE/api/inquiries/

# 4) Admin login + lista
TOKEN=$(curl -s -X POST $BASE/api/auth/login \
  -d 'username=dani&password=secret1' \
  -H 'Content-Type: application/x-www-form-urlencoded' | jq -r '.access_token')
curl -s $BASE/api/inquiries/ -H "Authorization: Bearer $TOKEN" | jq

# 5) Dettaglio (auto NEW → READ)
curl -s $BASE/api/inquiries/1 -H "Authorization: Bearer $TOKEN" | jq '.status'

# 6) Set REPLIED (popola replied_at)
curl -s -X PATCH $BASE/api/inquiries/1 -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"status":"REPLIED","admin_notes":"Risposto via email"}' | jq

# 7) Validazione: email invalida o messaggio troppo corto → 422
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/api/inquiries/ \
  -H 'Content-Type: application/json' \
  -d '{"name":"x","email":"non-email","message":"hello"}'
```

## Frontend

- `/contatti` — pagina con CTA che apre il dialog di contatto generico.
- `/articles/{id}` — bottone "Chiedi info" apre il dialog con l'`article_id`
  precompilato e l'oggetto `Info su: <titolo>`.
- `InquiryDialog.tsx` — client component con validazione HTML5, gestione
  stato `inviato`, errori.
