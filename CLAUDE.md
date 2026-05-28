# Easy EV Trip — Context del projecte

## Workflow de Git

Després de qualsevol canvi, **sempre fer merge a `main` i push**. No deixar canvis únicament a branques de feature.

## Visió general

MVP d'un planificador de viatges en cotxe elèctric que inverteix l'enfocament dels planificadors actuals (ABRP, Google Maps): en lloc de planificar al voltant de carregadors, planifica al voltant d'**ancores temporals humanes** — l'hora de dinar i l'hora de dormir. La pausa de càrrega gran coincideix amb el dinar (~60-90 min), i si el viatge és prou llarg es busca hotel amb carregador.

Hipòtesi a validar: els conductors d'EV troben més útil pensar el viatge així que en termes de SoC i parades tècniques.

## Estat actual

**Fase 1 completada**: esquelet funcional. Frontend → backend → resposta hardcoded → render. Tot el loop gira.

## Stack tècnic

- **Backend**: Python 3 + FastAPI + Pydantic, a `backend/`
- **Frontend**: HTML + JS vanilla (sense build, sense framework), a `frontend/`
- **Base de dades**: encara no (vindrà a fases posteriors per logging/feedback, probablement SQLite)
- **Hosting previst**: Vercel per al frontend (usuari ja té compte), Railway per al backend

## Estructura

```
EasyEvTrip/
├── backend/
│   ├── main.py           # FastAPI app, endpoint /plan
│   ├── models.py         # Esquemes Pydantic (PlanRequest, PlanResponse, PlanStop)
│   └── requirements.txt
├── frontend/
│   └── index.html        # Tot junt: HTML, CSS, JS
└── CLAUDE.md
```

## Categories de cotxe

| Categoria | Capacitat útil (kWh) | Consum (kWh/100km) | Autonomia útil (km) | Potència DC pic (kW) | Potència DC sostinguda (kW) |
|---|---|---|---|---|---|
| compact | 38 | 17 | 220 | 55 | 40 |
| medium | 55 | 17 | 320 | 110 | 80 |
| large | 72 | 18 | 400 | 175 | 130 |
| premium | 90 | 19 | 470 | 230 | 170 |

Exemples per UI (no per a model):
- compact: Zoe, e-208, Fiat 500e, BMW i3
- medium: MG4, Megane E-Tech, ID.3, Cupra Born
- large: Tesla M3 SR, EV6, Ioniq 5, ID.4
- premium: Tesla MY LR, EQE, Audi e-tron GT

## Model de càrrega (corba per tres zones)

- **Zona ràpida** (SoC 10-50%): rep `min(potència_pic_cotxe, potència_carregador)`
- **Zona mitja** (SoC 50-80%): rep `min(potència_sostinguda_cotxe, potència_carregador) × 0.7`
- **Zona lenta** (SoC 80-100%): ~30 kW × 0.5, independent del cotxe

Potència real del carregador = 80% de la potència anunciada (heurística per evitar prometre temps impossibles).

## Roadmap de fases

- ✅ **Fase 1**: esquelet funcional amb pla hardcoded
- ⏳ **Fase 2**: routing real amb OpenRouteService (distància i durada reals)
- **Fase 3**: model del cotxe (4 categories) + decisió "cal planificar o no"
- **Fase 4**: integració d'Open Charge Map per identificar carregadors
- **Fase 5**: restaurants amb Google Places (la finestra de dinar de l'usuari + carregador ≤300m)
- **Fase 6**: hotels amb amenity de càrrega EV via Google Places (fallback a hotel + carregador proper si no en troba)
- **Fase 7**: UI presentable estil línia de temps (vegeu disseny acordat)
- **Fase 8**: recollida de feedback (formulari final) + analítica privacy-friendly (Plausible/Umami)

## Decisions de disseny clau

1. **No app nativa al MVP**: web responsive és suficient per validar.
2. **Sense comptes d'usuari**: accés directe, sense autenticació, sense perfils persistents.
3. **Sense live status de carregadors al MVP**: confiem en Open Charge Map estàtic. Els problemes de fiabilitat es notaran al feedback i serà el següent gran problema a resoldre.
4. **Sense reserves dins l'app**: enllaços externs a Booking i Google Maps. Afiliació de Booking ve després de validar.
5. **Àmbit geogràfic**: viatges interurbans llargs (300-1500 km) a Europa Occidental. No limitar geografia.
6. **Cas degenerat útil**: si la distància cap dins l'autonomia del cotxe, retornar missatge clar "no cal planificar" en lloc de proposar parades innecessàries.
7. **Idioma**: català (i castellà més endavant). Tot el text d'usuari en català.

## Edge cases coneguts a tenir presents

- No hi ha carregador adient a la finestra de dinar → cal proposta alternativa raonada
- No hi ha hotel amb càrrega a la zona de pernoctació → fallback a hotel + carregador proper
- Cotxe petit en ruta llarga: cal pausa pre-dinar curta + dinar amb càrrega gran
- Cotxe gran en ruta curta: potser només cal "topar bateria opcional" al dinar
- Falla API externa: missatge clar a l'usuari, sense retry sofisticat al MVP

## Monetització (futur, no al MVP)

- Programa d'afiliats de Booking.com (deep links → comissió 25-40% del marge de Booking)
- Subscripció premium ~€3-4/mes per a power users (després de validar)
- No anuncis, no venda de dades

## Tone de veu

- Català natural, sentence case, no Title Case
- Honesto sobre limitacions ("encara no fem X")
- Sense bombo de màrqueting al producte ni al màrqueting d'arribada (forums EV són sensibles a això)
- Tipus de llançament: "tinc una eina experimental que potser et serveix" — no "us presentem la nova app"
