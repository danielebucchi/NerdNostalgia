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
