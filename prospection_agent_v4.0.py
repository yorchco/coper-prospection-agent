#!/usr/bin/env python3
"""
PROSPECCIÓN_AGENT v4.0 — GitHub Automated Agent
Flujo: Web Search → Notion (buffer) → TÚ calificas → HubSpot automático

Ejecuta: Cada martes 6:30 am automáticamente via GitHub Actions
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
# CONFIGURACIÓN — Lee desde GitHub Secrets
# ============================================================================

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")

NOTION_BASE_URL = "https://api.notion.com/v1"
HUBSPOT_BASE_URL = "https://api.hubapi.com"

# Tu tabla Notion: CLIENTS_list
NOTION_DATA_SOURCE_ID = "34247570-dee5-80b0-89a4-000b3f770c3b"

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Headers
headers_notion = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

headers_hubspot = {
    "Authorization": f"Bearer {HUBSPOT_API_KEY}",
    "Content-Type": "application/json"
}

headers_web = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ============================================================================
# PERFIL CLIENTE IDEAL COPER — Basado en documento estratégico
# ============================================================================

SEARCH_KEYWORDS = [
    "arquitecto Guadalajara diseño interior proyectos",
    "despacho arquitectura Jalisco residencial",
    "interiorista Guadalajara contacto",
    "diseñador interiores profesional Guadalajara",
    "estudio arquitectura pequeño Jalisco",
    "arquitecto independiente Guadalajara proyectos activos",
    "diseño interior comercial Guadalajara",
    "interiorismo proyectos arquitectónicos Jalisco",
    "despacho de diseño Guadalajara",
    "profesional arquitectura interiores México"
]

# Criterios de cliente ideal (Segmento A prioritario)
CLIENT_IDEAL_CRITERIA = {
    "roles": ["arquitecto", "diseñador", "interiorista", "director", "jefe", "propietario", "consultor"],
    "sectors": ["arquitectura", "diseño", "interior", "construcción", "muebles", "interiorismo"],
    "locations": ["guadalajara", "jalisco", "cdmx", "méxico", "zapopan", "tonalá"],
    "signals": ["proyecto", "presupuesto", "cliente", "ejecución", "desarrollo"]
}

# ============================================================================
# FUNCIONES DE VALIDACIÓN Y CALIFICACIÓN
# ============================================================================

def validate_email(email):
    """Valida que un email parece real"""
    if not email or "@" not in email:
        return False
    
    bad_domains = ["example.com", "test.com", "mail.com", "placeholder", "noreply"]
    domain = email.split("@")[1].lower()
    
    if any(bad in domain for bad in bad_domains):
        return False
    
    if re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
        return True
    
    return False

def score_candidate(candidate):
    """Califica candidato según criterios COPER (0-100 puntos)"""
    score = 0
    reasons = []
    
    # Email válido (20 pts)
    if validate_email(candidate.get("email", "")):
        score += 20
        reasons.append("Email válido")
    else:
        return 0, "Email inválido", False
    
    # Presencia web (15 pts)
    if candidate.get("website"):
        score += 15
        reasons.append("Website profesional")
    
    # Rol alineado (25 pts)
    role = candidate.get("role", "").lower()
    if any(r in role for r in CLIENT_IDEAL_CRITERIA["roles"]):
        score += 25
        reasons.append(f"Rol: {role}")
    
    # Sector alineado (20 pts)
    sector = candidate.get("sector", "").lower()
    if any(s in sector for s in CLIENT_IDEAL_CRITERIA["sectors"]):
        score += 20
        reasons.append("Sector alineado")
    
    # Ubicación COPER (10 pts)
    location = candidate.get("location", "").lower()
    if any(loc in location for loc in CLIENT_IDEAL_CRITERIA["locations"]):
        score += 10
        reasons.append("Ubicación COPER")
    
    # Señales de proyecto/presupuesto (10 pts)
    notas = (candidate.get("notas", "") + " " + candidate.get("company", "")).lower()
    if any(sig in notas for sig in CLIENT_IDEAL_CRITERIA["signals"]):
        score += 10
        reasons.append("Señales de proyecto activo")
    
    # Teléfono disponible (bonus 5 pts)
    if candidate.get("phone"):
        score += 5
        reasons.append("Teléfono disponible")
    
    should_create = score >= 60  # Umbral mínimo
    
    return score, " | ".join(reasons), should_create

# ============================================================================
# WEB SCRAPING — Búsqueda en Google
# ============================================================================

def search_web(keyword):
    """Busca candidatos reales en Google"""
    logger.info(f"🔍 Buscando: {keyword}")
    
    candidates = []
    
    try:
        search_url = f"https://www.google.com/search?q={quote(keyword)}"
        response = requests.get(search_url, headers=headers_web, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extraer primeros 5 resultados
        for link in soup.find_all('a', href=True)[:5]:
            href = link['href']
            text = link.get_text()
            
            if href.startswith('/url?q=') and 'google' not in href:
                try:
                    url = href.split('/url?q=')[1].split('&')[0]
                    
                    # Detectar si es relevante
                    if any(word in text.lower() for word in ["arquitecto", "diseñador", "despacho", "interiorista"]):
                        candidate = {
                            "name": text[:60],
                            "company": text[:40],
                            "email": None,
                            "phone": None,
                            "role": "Profesional Arquitectura/Diseño",
                            "sector": "Arquitectura/Interiorismo",
                            "location": keyword,
                            "website": url,
                            "notas": f"Encontrado en búsqueda: {keyword}"
                        }
                        
                        # Intentar extraer email y teléfono de la URL
                        try:
                            page_response = requests.get(url, headers=headers_web, timeout=5)
                            page_soup = BeautifulSoup(page_response.content, 'html.parser')
                            page_text = page_soup.get_text()
                            
                            # Buscar emails
                            emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', page_text)
                            if emails:
                                candidate["email"] = emails[0]
                            
                            # Buscar teléfonos (formato: +52 o 10+ dígitos)
                            phones = re.findall(r'\+?[\d\s\-\(\)]{10,}', page_text)
                            if phones:
                                candidate["phone"] = phones[0].strip()
                        except:
                            pass
                        
                        candidates.append(candidate)
                except:
                    pass
        
        logger.info(f"✅ {len(candidates)} candidatos encontrados")
    
    except Exception as e:
        logger.warning(f"⚠️ Error buscando '{keyword}': {e}")
    
    return candidates

# ============================================================================
# NOTION — Crear registros en CLIENTS_list
# ============================================================================

def create_notion_candidate(candidate, score, reasoning):
    """Crea página en Notion tabla CLIENTS_list"""
    try:
        url = f"{NOTION_BASE_URL}/pages"
        
        payload = {
            "parent": {"database_id": NOTION_DATA_SOURCE_ID},
            "properties": {
                "CLIENTE": {
                    "title": [
                        {
                            "text": {
                                "content": candidate.get("name", "Unknown")[:100]
                            }
                        }
                    ]
                },
                "Email": {
                    "email": candidate.get("email", "")
                },
                "Sector": {
                    "select": {
                        "name": candidate.get("sector", "Otro")
                    }
                },
                "Nivel": {
                    "select": {
                        "name": "N2" if score >= 75 else "N1"
                    }
                },
                "Notas": {
                    "rich_text": [
                        {
                            "text": {
                                "content": f"SCORE: {score}/100 | {reasoning}"
                            }
                        }
                    ]
                }
            }
        }
        
        response = requests.post(url, json=payload, headers=headers_notion, timeout=10)
        
        if response.status_code in [200, 201]:
            page_id = response.json().get("id")
            logger.info(f"✅ Notion: {candidate.get('name')} (Score: {score})")
            return True
        else:
            logger.warning(f"⚠️ Notion {response.status_code}: {response.text[:100]}")
            return False
    except Exception as e:
        logger.error(f"❌ Notion error: {e}")
        return False

# ============================================================================
# LEER NOTION — Obtener candidatos VALIDADOS
# ============================================================================

def read_notion_validated():
    """Lee Notion y retorna candidatos marcados como válidos"""
    try:
        url = f"{NOTION_BASE_URL}/databases/{NOTION_DATA_SOURCE_ID}/query"
        
        payload = {
            "filter": {
                "property": "Cliente valido COPER",
                "checkbox": {
                    "equals": True
                }
            }
        }
        
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
                    "notas": props.get("Notas", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
                }
                candidates.append(candidate)
            
            logger.info(f"✅ Notion: {len(candidates)} candidatos válidos encontrados")
            return candidates
        else:
            logger.warning(f"⚠️ Notion error {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"❌ Error leyendo Notion: {e}")
        return []

# ============================================================================
# HUBSPOT — Crear contactos validados
# ============================================================================

def create_hubspot_contact(candidate):
    """Crea contacto en HubSpot"""
    try:
        url = f"{HUBSPOT_BASE_URL}/crm/v3/objects/contacts"
        
        name_parts = candidate.get("name", "Unknown").split()
        firstname = name_parts[0] if name_parts else "Unknown"
        lastname = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        payload = {
            "properties": {
                "firstname": firstname,
                "lastname": lastname,
                "email": candidate.get("email", ""),
                "sector_cliente": candidate.get("sector", "Otro"),
                "nivel_potencial_coper": candidate.get("nivel", "N1"),
                "donde_encontrado": "Web Search via Notion",
                "notas_prospersion_coper": candidate.get("notas", ""),
                "cliente_valido_coper": "true",
                "lifecyclestage": "lead"
            }
        }
        
        response = requests.post(url, json=payload, headers=headers_hubspot, timeout=10)
        
        if response.status_code in [200, 201]:
            contact_id = response.json().get("id")
            logger.info(f"✅ HubSpot: {candidate.get('name')} (ID: {contact_id})")
            return True
        else:
            logger.warning(f"⚠️ HubSpot {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ HubSpot error: {e}")
        return False

# ============================================================================
# AGENTE PRINCIPAL
# ============================================================================

def run_prospection_agent():
    """Ejecuta el agente completo"""
    logger.info("=" * 70)
    logger.info("PROSPECCIÓN_AGENT v4.0 — GitHub Automated")
    logger.info("=" * 70)
    
    start_time = datetime.now()
    
    # VALIDAR CREDENCIALES
    if not NOTION_TOKEN or not HUBSPOT_API_KEY:
        logger.error("❌ Faltan credenciales. Configura NOTION_TOKEN y HUBSPOT_API_KEY en GitHub Secrets")
        return {"status": "error", "message": "Missing credentials"}
    
    # FASE 1: Buscar en web
    logger.info("\n📋 FASE 1: Buscando candidatos en web...")
    all_candidates = []
    
    for keyword in SEARCH_KEYWORDS:
        candidates = search_web(keyword)
        all_candidates.extend(candidates)
        time.sleep(1)
    
    logger.info(f"Total encontrados: {len(all_candidates)}")
    
    # FASE 2: Calificar y guardar en Notion
    logger.info("\n⚖️ FASE 2: Calificando y guardando en Notion...")
    created_notion = 0
    
    for candidate in all_candidates:
        score, reasoning, should_create = score_candidate(candidate)
        
        if should_create:
            if create_notion_candidate(candidate, score, reasoning):
                created_notion += 1
        
        time.sleep(0.5)
    
    logger.info(f"Guardados en Notion: {created_notion}")
    
    # FASE 3: Leer validados de Notion
    logger.info("\n🔄 FASE 3: Leyendo candidatos validados de Notion...")
    time.sleep(2)
    
    validated = read_notion_validated()
    logger.info(f"Validados para HubSpot: {len(validated)}")
    
    # FASE 4: Crear en HubSpot
    logger.info("\n📤 FASE 4: Creando en HubSpot...")
    created_hubspot = 0
    
    for candidate in validated:
        if create_hubspot_contact(candidate):
            created_hubspot += 1
        time.sleep(0.5)
    
    # Reporte final
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ EJECUCIÓN COMPLETADA")
    logger.info("=" * 70)
    logger.info(f"Duración: {duration:.2f}s")
    logger.info(f"Encontrados en web: {len(all_candidates)}")
    logger.info(f"Guardados en Notion: {created_notion}")
    logger.info(f"Validados: {len(validated)}")
    logger.info(f"Creados en HubSpot: {created_hubspot}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}\n")
    
    return {
        "status": "completed",
        "web_found": len(all_candidates),
        "notion_created": created_notion,
        "notion_validated": len(validated),
        "hubspot_created": created_hubspot,
        "duration_seconds": duration,
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    try:
        result = run_prospection_agent()
        logger.info(f"Resultado final: {json.dumps(result, indent=2)}")
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
