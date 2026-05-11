#!/usr/bin/env python3
"""
PROSPECCIÓN_AGENT v4.0 — 2 Modos: SEARCH (6:30am) + SEND (8:00pm)
"""

import requests
from bs4 import BeautifulSoup
import json
import logging
from datetime import datetime
import time
import os
import re
from urllib.parse import quote

# ============================================================================
# CONFIG
# ============================================================================

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")
MODE = os.getenv("MODE", "search")  # search o send

NOTION_BASE_URL = "https://api.notion.com/v1"
HUBSPOT_BASE_URL = "https://api.hubapi.com"
NOTION_DATA_SOURCE_ID = "34247570-dee5-80b0-89a4-000b3f770c3b"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

headers_notion = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

headers_hubspot = {
    "Authorization": f"Bearer {HUBSPOT_API_KEY}",
    "Content-Type": "application/json"
}

headers_web = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

SEARCH_KEYWORDS = [
    "arquitecto Guadalajara diseño interior",
    "despacho arquitectura Jalisco",
    "interiorista profesional Guadalajara",
    "diseñador interiores Guadalajara",
    "estudio arquitectura Jalisco independiente",
]

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def validate_email(email):
    if not email or "@" not in email:
        return False
    bad = ["example.com", "test.com"]
    domain = email.split("@")[1].lower()
    if any(b in domain for b in bad):
        return False
    return re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email) is not None

def score_candidate(candidate):
    score = 0
    if validate_email(candidate.get("email", "")):
        score += 20
    else:
        return 0, "Email inválido", False
    
    if candidate.get("website"):
        score += 15
    
    role = candidate.get("role", "").lower()
    if any(r in role for r in ["arquitecto", "diseñador", "interiorista"]):
        score += 25
    
    sector = candidate.get("sector", "").lower()
    if any(s in sector for s in ["arquitectura", "diseño", "interior"]):
        score += 20
    
    return score, "Válido", score >= 60

# ============================================================================
# MODO SEARCH — Buscar en web + escribir en Notion
# ============================================================================

def search_web(keyword):
    logger.info(f"Buscando: {keyword}")
    candidates = []
    try:
        search_url = f"https://www.google.com/search?q={quote(keyword)}"
        response = requests.get(search_url, headers=headers_web, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for link in soup.find_all('a', href=True)[:3]:
            href = link['href']
            text = link.get_text()
            if href.startswith('/url?q=') and 'google' not in href:
                url = href.split('/url?q=')[1].split('&')[0]
                if any(w in text.lower() for w in ["arquitecto", "diseño", "interiorista"]):
                    candidate = {
                        "name": text[:60],
                        "email": "contacto@ejemplo.com",
                        "role": "Profesional",
                        "sector": "Arquitectura/Diseño",
                        "website": url,
                        "company": text[:40]
                    }
                    candidates.append(candidate)
    except:
        pass
    return candidates

def create_notion_candidate(candidate, score):
    try:
        url = f"{NOTION_BASE_URL}/pages"
        payload = {
            "parent": {"database_id": NOTION_DATA_SOURCE_ID},
            "properties": {
                "CLIENTE": {"title": [{"text": {"content": candidate.get("name", "Unknown")[:100]}}]},
                "Email": {"email": candidate.get("email", "")},
                "Sector": {"select": {"name": candidate.get("sector", "Otro")}},
                "Nivel": {"select": {"name": "N2" if score >= 75 else "N1"}},
                "Notas": {"rich_text": [{"text": {"content": f"SCORE: {score}/100"}}]}
            }
        }
        response = requests.post(url, json=payload, headers=headers_notion, timeout=10)
        if response.status_code in [200, 201]:
            logger.info(f"✅ Notion: {candidate.get('name')}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error Notion: {e}")
        return False

def run_search_mode():
    logger.info("=" * 70)
    logger.info("MODO SEARCH — Búsqueda en web + escritura en Notion")
    logger.info("=" * 70)
    
    all_candidates = []
    for keyword in SEARCH_KEYWORDS:
        candidates = search_web(keyword)
        all_candidates.extend(candidates)
        time.sleep(1)
    
    logger.info(f"Encontrados: {len(all_candidates)}")
    
    created_notion = 0
    for candidate in all_candidates:
        score, _, should_create = score_candidate(candidate)
        if should_create:
            if create_notion_candidate(candidate, score):
                created_notion += 1
        time.sleep(0.5)
    
    logger.info(f"Guardados en Notion: {created_notion}")
    return {"status": "completed", "web_found": len(all_candidates), "notion_created": created_notion}

# ============================================================================
# MODO SEND — Leer Notion + enviar a HubSpot
# ============================================================================

def read_notion_validated():
    try:
        url = f"{NOTION_BASE_URL}/databases/{NOTION_DATA_SOURCE_ID}/query"
        payload = {"filter": {"property": "Cliente valido COPER", "checkbox": {"equals": True}}}
        response = requests.post(url, json=payload, headers=headers_notion, timeout=10)
        
        if response.status_code == 200:
            pages = response.json().get("results", [])
            candidates = []
            for page in pages:
                props = page.get("properties", {})
                candidate = {
                    "name": props.get("CLIENTE", {}).get("title", [{}])[0].get("text", {}).get("content", ""),
                    "email": props.get("Email", {}).get("email", ""),
                    "sector": props.get("Sector", {}).get("select", {}).get("name", ""),
                    "nivel": props.get("Nivel", {}).get("select", {}).get("name", ""),
                }
                candidates.append(candidate)
            logger.info(f"✅ Notion validados: {len(candidates)}")
            return candidates
        return []
    except Exception as e:
        logger.error(f"Error Notion: {e}")
        return []

def create_hubspot_contact(candidate):
    try:
        url = f"{HUBSPOT_BASE_URL}/crm/v3/objects/contacts"
        name_parts = candidate.get("name", "Unknown").split()
        payload = {
            "properties": {
                "firstname": name_parts[0] if name_parts else "Unknown",
                "lastname": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
                "email": candidate.get("email", ""),
                "lifecyclestage": "lead"
            }
        }
        response = requests.post(url, json=payload, headers=headers_hubspot, timeout=10)
        if response.status_code in [200, 201]:
            logger.info(f"✅ HubSpot: {candidate.get('name')}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error HubSpot: {e}")
        return False

def run_send_mode():
    logger.info("=" * 70)
    logger.info("MODO SEND — Lectura Notion + envío a HubSpot")
    logger.info("=" * 70)
    
    validated = read_notion_validated()
    logger.info(f"Candidatos para enviar: {len(validated)}")
    
    created_hubspot = 0
    for candidate in validated:
        if create_hubspot_contact(candidate):
            created_hubspot += 1
        time.sleep(0.5)
    
    logger.info(f"Creados en HubSpot: {created_hubspot}")
    return {"status": "completed", "notion_validated": len(validated), "hubspot_created": created_hubspot}

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    logger.info(f"Modo: {MODE.upper()}")
    
    if not NOTION_TOKEN or not HUBSPOT_API_KEY:
        logger.error("Faltan credenciales")
    elif MODE == "search":
        result = run_search_mode()
        logger.info(json.dumps(result))
    elif MODE == "send":
        result = run_send_mode()
        logger.info(json.dumps(result))
    else:
        logger.error(f"Modo desconocido: {MODE}")
