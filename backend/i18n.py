from typing import Any

LANGS = {"ca", "es", "en", "fr", "it", "de"}
DEFAULT_LANG = "ca"

STRINGS: dict[str, dict[str, str]] = {
    # ── Stop names ────────────────────────────────────────────────────────────
    "start_name": {
        "ca": "Sortida de {origin}",
        "es": "Salida de {origin}",
        "en": "Departure from {origin}",
        "fr": "Départ de {origin}",
        "it": "Partenza da {origin}",
        "de": "Abfahrt von {origin}",
    },
    "start_desc": {
        "ca": "Bateria carregada al màxim.",
        "es": "Batería cargada al máximo.",
        "en": "Battery fully charged.",
        "fr": "Batterie chargée au maximum.",
        "it": "Batteria al massimo.",
        "de": "Akku vollständig geladen.",
    },
    "destination_name": {
        "ca": "Arribada a {dest}",
        "es": "Llegada a {dest}",
        "en": "Arrival at {dest}",
        "fr": "Arrivée à {dest}",
        "it": "Arrivo a {dest}",
        "de": "Ankunft in {dest}",
    },
    "destination_desc": {
        "ca": "Fi del viatge.",
        "es": "Fin del viaje.",
        "en": "End of trip.",
        "fr": "Fin du voyage.",
        "it": "Fine del viaggio.",
        "de": "Ende der Reise.",
    },
    "charge_name": {
        "ca": "Càrrega DC",
        "es": "Carga DC",
        "en": "DC Charge",
        "fr": "Charge DC",
        "it": "Ricarica DC",
        "de": "DC-Laden",
    },
    "pre_lunch_charge_name": {
        "ca": "Càrrega breu (pre-dinar)",
        "es": "Carga breve (antes de comer)",
        "en": "Brief charge (pre-lunch)",
        "fr": "Charge rapide (avant déjeuner)",
        "it": "Ricarica breve (pre-pranzo)",
        "de": "Kurze Ladung (vor Mittagessen)",
    },
    "lunch_name": {
        "ca": "Parada a dinar",
        "es": "Parada para comer",
        "en": "Lunch stop",
        "fr": "Pause déjeuner",
        "it": "Sosta pranzo",
        "de": "Mittagspause",
    },
    "lunch_charge_name": {
        "ca": "Dinar + càrrega DC",
        "es": "Comida + carga DC",
        "en": "Lunch + DC charge",
        "fr": "Déjeuner + charge DC",
        "it": "Pranzo + ricarica DC",
        "de": "Mittagessen + DC-Laden",
    },
    "hotel_name": {
        "ca": "Pernoctació",
        "es": "Pernoctación",
        "en": "Overnight stay",
        "fr": "Nuitée",
        "it": "Pernottamento",
        "de": "Übernachtung",
    },
    # ── Descriptions ─────────────────────────────────────────────────────────
    "lunch_no_charge_desc": {
        "ca": "45 min de descans. No cal carregar.",
        "es": "45 min de descanso. Sin necesidad de cargar.",
        "en": "45 min rest. No charging needed.",
        "fr": "45 min de repos. Pas besoin de recharger.",
        "it": "45 min di riposo. Nessuna ricarica necessaria.",
        "de": "45 min Pause. Kein Laden nötig.",
    },
    "lunch_simple_desc": {
        "ca": "45 min de descans.",
        "es": "45 min de descanso.",
        "en": "45 min rest.",
        "fr": "45 min de repos.",
        "it": "45 min di riposo.",
        "de": "45 min Pause.",
    },
    "lunch_high_soc_desc": {
        "ca": "45 min de descans. Bateria suficient ({soc}%), sense necessitat de carregar.",
        "es": "45 min de descanso. Batería suficiente ({soc}%), sin necesidad de cargar.",
        "en": "45 min rest. Battery sufficient ({soc}%), no charging needed.",
        "fr": "45 min de repos. Batterie suffisante ({soc}%), pas besoin de recharger.",
        "it": "45 min di riposo. Batteria sufficiente ({soc}%), nessuna ricarica.",
        "de": "45 min Pause. Akku ausreichend ({soc}%), kein Laden nötig.",
    },
    "pre_lunch_charge_suffix": {
        "ca": " Càrrega principal durant el dinar.",
        "es": " Carga principal durante la comida.",
        "en": " Main charge during lunch.",
        "fr": " Charge principale pendant le déjeuner.",
        "it": " Ricarica principale durante il pranzo.",
        "de": " Hauptladung beim Mittagessen.",
    },
    "charger_fallback": {
        "ca": "Carregador DC",
        "es": "Cargador DC",
        "en": "DC charger",
        "fr": "Chargeur DC",
        "it": "Caricatore DC",
        "de": "DC-Ladepunkt",
    },
    "network_fallback_suffix": {
        "ca": " · xarxa preferida no disponible",
        "es": " · red preferida no disponible",
        "en": " · preferred network unavailable",
        "fr": " · réseau préféré indisponible",
        "it": " · rete preferita non disponibile",
        "de": " · bevorzugtes Netz nicht verfügbar",
    },
    "walk_min_label": {
        "ca": "min a peu",
        "es": "min andando",
        "en": "min walk",
        "fr": "min à pied",
        "it": "min a piedi",
        "de": "min zu Fuß",
    },
    "restaurant_label": {
        "ca": "Restaurant",
        "es": "Restaurante",
        "en": "Restaurant",
        "fr": "Restaurant",
        "it": "Ristorante",
        "de": "Restaurant",
    },
    "hotel_desc": {
        "ca": "Hotel: {hotel}. Carregador a {walk_min} min a peu ({charger}).",
        "es": "Hotel: {hotel}. Cargador a {walk_min} min andando ({charger}).",
        "en": "Hotel: {hotel}. Charger {walk_min} min walk away ({charger}).",
        "fr": "Hôtel: {hotel}. Chargeur à {walk_min} min à pied ({charger}).",
        "it": "Hotel: {hotel}. Ricaricatore a {walk_min} min a piedi ({charger}).",
        "de": "Hotel: {hotel}. Ladepunkt {walk_min} min zu Fuß ({charger}).",
    },
    # ── Notes ────────────────────────────────────────────────────────────────
    "note_no_charge": {
        "ca": "El teu cotxe arriba a {dest} sense necessitat de carregar (bateria estimada: ~{soc}%).",
        "es": "Tu coche llega a {dest} sin necesidad de cargar (batería estimada: ~{soc}%).",
        "en": "Your car reaches {dest} without needing to charge (estimated battery: ~{soc}%).",
        "fr": "Votre voiture arrive à {dest} sans recharger (batterie estimée: ~{soc}%).",
        "it": "La tua auto arriva a {dest} senza ricaricare (batteria stimata: ~{soc}%).",
        "de": "Ihr Auto erreicht {dest} ohne Laden (geschätzte Batterie: ~{soc}%).",
    },
    "note_1night": {
        "ca": "Viatge de 2 dies. La durada indicada és el temps actiu (sense la nit a l'hotel).",
        "es": "Viaje de 2 días. La duración es el tiempo activo (sin la noche en el hotel).",
        "en": "2-day trip. Duration shown is active travel time (excluding hotel night).",
        "fr": "Voyage de 2 jours. La durée est le temps actif (hors nuit d'hôtel).",
        "it": "Viaggio di 2 giorni. La durata è il tempo attivo (esclusa la notte in hotel).",
        "de": "2-tägige Reise. Dauer ist Fahrzeit (ohne Hotelübernachtung).",
    },
    "note_multinight": {
        "ca": "Viatge de {days} dies. La durada indicada és el temps actiu (sense les nits a l'hotel).",
        "es": "Viaje de {days} días. La duración es el tiempo activo (sin las noches en el hotel).",
        "en": "{days}-day trip. Duration shown is active travel time (excluding hotel nights).",
        "fr": "Voyage de {days} jours. La durée est le temps actif (hors nuits d'hôtel).",
        "it": "Viaggio di {days} giorni. La durata è il tempo attivo (escluse le notti in hotel).",
        "de": "{days}-tägige Reise. Dauer ist Fahrzeit (ohne Hotelübernachtungen).",
    },
}


def normalize_lang(lang: str | None) -> str:
    if not lang:
        return DEFAULT_LANG
    code = lang.lower().split("-")[0]
    return code if code in LANGS else DEFAULT_LANG


def _t(lang: str, key: str, **kwargs: Any) -> str:
    bucket = STRINGS.get(key, {})
    text = bucket.get(lang) or bucket.get(DEFAULT_LANG) or key
    return text.format(**kwargs) if kwargs else text
