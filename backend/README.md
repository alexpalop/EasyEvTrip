# EV Trip Planner — MVP

Planificador de viatges en cotxe elèctric basat en ancores temporals (dinar, dormir) en lloc de carregadors.

## Estat actual

**Fase 1**: esquelet funcional. El backend retorna un pla hardcoded; el frontend l'ensenya correctament. Serveix per validar que tot el loop funciona.

## Executar localment

### Backend (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate   # a Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

El backend queda escoltant a http://localhost:8000

Pots provar-lo amb la documentació interactiva: http://localhost:8000/docs

### Frontend

Obre `frontend/index.html` directament al navegador (doble click), o serveix-lo amb qualsevol servidor estàtic:

```bash
cd frontend
python -m http.server 5500
```

Després: http://localhost:5500

## Properes fases

- Fase 2: routing real amb OpenRouteService
- Fase 3: model del cotxe (4 categories) + decisió "cal planificar o no"
- Fase 4: integració d'Open Charge Map per identificar carregadors
- Fase 5: restaurants amb Google Places
- Fase 6: hotels amb càrrega
- Fase 7: UI presentable estil línia de temps
- Fase 8: feedback i analítica
