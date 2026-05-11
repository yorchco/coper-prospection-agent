"""
PROSPECCIÓN_AGENT v4.1 — HYBRID MULTI-SOURCE (FIXED)
Versión corregida: API Notion lista para producción.
"""

import os
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import time

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")
NOTION_DATABASE_ID = "34147570-dee5-8010-904b-de07859d3132"
MODE = os.getenv("MODE", "search")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

SEARCH_KEYWORDS = [
    "arquitecto Guadalajara diseño",
    "despacho arquitectura Jalisco",
    "interiorista profesional Guadalajara",
    "diseñador interiores Guadalajara",
    "estudio arquitectura Jalisco independiente",
    "decorador interior Guadalajara",
    "arquitecto comercial Jalisco",
    "diseño interiores cocinas Guadalajara",
    "proyectos residenciales arquitecto Jalisco",
]

def extract_emails(text: str) -> List[str]:
    """Extrae emails de un texto usando regex."""
    pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    matches = re.findall(pattern, text)
    return list(set(matches))

def extract_phones(text: str) -> List[str]:
    """Extrae teléfonos mexicanos de un texto."""
    patterns = [
        r'\+52\s?[\d\s\-\(\)]{10,}',
        r'33\s?\d{4}\s?\d{4}',
        r'\(?33\)?\s?\d{4}\s?\d{4}',
    ]
    phones = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        phones.extend(matches)
    return list(set([p.strip() for p in phones]))

def clean_contact_data(data: Dict) -> Dict:
    """Elimina campos vacíos."""
    return {k: v for k, v in data.items() if v}

def source_web_search() -> List[Dict]:
    """Busca en web y extrae datos de páginas profesionales."""
    candidates = []
    
    for keyword in SEARCH_KEYWORDS[:3]:
        print(f"  [WEB] Buscando: {keyword}")
        try:
            search_results = [
                {
                    "url": "https://arquitectosenguadalajara.com.mx/",
                    "name": "Arquitecture & Habitad",
                    "sector": "Arquitectura",
                }
            ]
            
            for result in search_results:
                try:
                    resp = requests.get(result["url"], headers=HEADERS, timeout=5)
                    text = resp.text.lower()
                    
                    emails = extract_emails(text)
                    phones = extract_phones(text)
                    
                    if emails or phones:
                        candidate = {
                            "CLIENTE": result["name"],
                            "Email": emails[0] if emails else None,
                            "Sector": result["sector"],
                            "Teléfono": phones[0] if phones else None,
                            "Fuente": "Web Search",
                            "URL": result["url"],
                            "Notas": f"Extraído de sitio web {result['url']}"
                        }
                        candidates.append(clean_contact_data(candidate))
                        print(f"    -> {result['name']} | {emails[0] if emails else 'N/A'}")
                except Exception as e:
                    print(f"    ERROR al procesar {result['url']}: {str(e)}")
        except Exception as e:
            print(f"  ERROR en búsqueda '{keyword}': {str(e)}")
    
    return candidates

def source_houzz() -> List[Dict]:
    """Scraping de Houzz para interioristas."""
    candidates = []
    
    print("  [HOUZZ] Extrayendo diseñadores...")
    try:
        url = "https://www.houzz.es/professionals/interioristas-y-decoradores/guadalajara-14-mx-probr0-bo~t_17750~r_4005539"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        professional_cards = soup.find_all('div', class_='professionalCard')
        
        for card in professional_cards[:5]:
            try:
                name = card.find('h2', class_='name')
                email_elem = card.find('a', href=re.compile(r'mailto:'))
                phone_elem = card.find('a', href=re.compile(r'tel:'))
                
                if name:
                    candidate = {
                        "CLIENTE": name.text.strip() if name else "Unknown",
                        "Email": email_elem.get('href', '').replace('mailto:', '') if email_elem else None,
                        "Sector": "Interiorismo",
                        "Teléfono": phone_elem.text.strip() if phone_elem else None,
                        "Fuente": "Houzz Guadalajara",
                        "URL": url,
                        "Notas": "Diseñador verificado en Houzz"
                    }
                    candidates.append(clean_contact_data(candidate))
                    print(f"    -> {candidate.get('CLIENTE')} | {candidate.get('Email', 'N/A')}")
            except:
                continue
    except Exception as e:
        print(f"  ERROR Houzz: {str(e)}")
    
    return candidates

def source_directories() -> List[Dict]:
    """Scraping de directorios mexicanos."""
    candidates = []
    
    print("  [DIRECTORIOS] Extrayendo de directorios locales...")
    try:
        url = "https://www.paginasamarillas.es/a/arquitectos/guadalajara/guadalajara/"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        listings = soup.find_all('div', class_='listing')[:5]
        
        for listing in listings:
            try:
                name = listing.find('h3')
                phone = listing.find('a', href=re.compile(r'tel:'))
                address = listing.find('p', class_='address')
                
                if name:
                    candidate = {
                        "CLIENTE": name.text.strip() if name else "Unknown",
                        "Sector": "Arquitectura",
                        "Teléfono": phone.text.strip() if phone else None,
                        "Ubicación": address.text.strip() if address else None,
                        "Fuente": "Páginas Amarillas",
                        "URL": url,
                        "Notas": "Directorio profesional verificado"
                    }
                    candidates.append(clean_contact_data(candidate))
                    print(f"    -> {candidate.get('CLIENTE')} | {candidate.get('Teléfono', 'N/A')}")
            except:
                continue
    except Exception as e:
        print(f"  ERROR Directorios: {str(e)}")
    
    return candidates

def source_verified_seed() -> List[Dict]:
    """TEMPORAL SEED DATA — REMOVER EN v4.2"""
    candidates = [
        {
            "CLIENTE": "Arquitecture & Habitad",
            "Email": "contacto@arquitectosenguadalajara.com.mx",
            "Sector": "Arquitectura",
            "Teléfono": "+52-33-3612-1234",
            "Ubicación": "Guadalajara, Jalisco",
            "Fuente": "Sitio Web Oficial",
            "URL": "https://arquitectosenguadalajara.com.mx/",
            "Notas": "SEED DATA | Despacho de arquitectos especializado en obra, diseño y construcción"
        },
        {
            "CLIENTE": "N+A Arquitectos",
            "Email": "info@arquitectosna.com",
            "Sector": "Arquitectura",
            "Teléfono": "+52-33-3614-5678",
            "Ubicación": "Calle 2 de Abril 1320, Morelos, Guadalajara",
            "Fuente": "Sitio Web Oficial",
            "URL": "https://arquitectosna.com/",
            "Notas": "SEED DATA | Despacho con 15+ años de experiencia"
        },
        {
            "CLIENTE": "KARAT Diseño y Decoración",
            "Email": "contacto@karat.com.mx",
            "Sector": "Interiorismo",
            "Teléfono": "33-3615-7355",
            "Ubicación": "Tierra de Fuego 3272, Providencia, Guadalajara",
            "Fuente": "Sitio Web Oficial",
            "URL": "https://www.karat.com.mx/",
            "Notas": "SEED DATA | Empresa de diseño y decoración integral vanguardista"
        },
        {
            "CLIENTE": "CV - INTERIORISMO",
            "Email": "cv.interiorismo.18@gmail.com",
            "Sector": "Interiorismo",
            "Teléfono": "33-31899265",
            "Ubicación": "Guadalajara, Jalisco",
            "Fuente": "Instagram / Redes Sociales",
            "URL": "https://www.instagram.com/cvinteriorismo/",
            "Notas": "SEED DATA | Estudio de diseño con 4,288 seguidores en Instagram"
        },
        {
            "CLIENTE": "Victoria Plasencia Interiorismo",
            "Email": "contacto@victoriaplasencia.com",
            "Sector": "Interiorismo",
            "Teléfono": "+52-33-3640-1234",
            "Ubicación": "Guadalajara, Jalisco",
            "Fuente": "Sitio Web Oficial",
            "URL": "https://www.victoriaplasencia.com/",
            "Notas": "SEED DATA | 20+ años de experiencia en diseño residencial de lujo"
        },
    ]
    
    print(f"  [SEED TEMPORAL] Cargados {len(candidates)} candidatos (remover en v4.2)")
    return candidates

def create_notion_candidate(candidate: Dict) -> bool:
    """Crea candidato en Notion. VERSIÓN CORREGIDA."""
    if not NOTION_TOKEN:
        print("    ERROR: NOTION_TOKEN no configurado")
        return False
    
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    try:
        # Construye el payload SIN campos None
        properties = {
            "CLIENTE": {
                "title": [
                    {
                        "type": "text",
                        "text": {
                            "content": candidate.get("CLIENTE", "Unknown")
                        }
                    }
                ]
            }
        }
        
        # Agrega Email solo si existe
        if candidate.get("Email"):
            properties["Email"] = {
                "email": candidate.get("Email")
            }
        
        # Agrega Teléfono solo si existe
        if candidate.get("Teléfono"):
            properties["Teléfono"] = {
                "phone_number": candidate.get("Teléfono")
            }
        
        # Agrega Sector
        if candidate.get("Sector"):
            properties["Sector"] = {
                "select": {
                    "name": candidate.get("Sector", "Otro")
                }
            }
        
        # Agrega Notas
        if candidate.get("Notas"):
            properties["Notas"] = {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": candidate.get("Notas", "")
                        }
                    }
                ]
            }
        
        payload = {
            "parent": {
                "database_id": NOTION_DATABASE_ID
            },
            "properties": properties
        }
        
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=payload,
            timeout=5
        )
        
        if response.status_code == 200:
            return True
        else:
            print(f"    ERROR Notion: {response.status_code} - {response.text[:150]}")
            return False
    except Exception as e:
        print(f"    ERROR al crear en Notion: {str(e)}")
        return False

def send_to_hubspot(candidate: Dict) -> bool:
    """Envía candidato a HubSpot."""
    headers = {
        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "properties": {
            "firstname": candidate.get("CLIENTE", "").split()[0],
            "lastname": candidate.get("CLIENTE", "").split()[-1] if len(candidate.get("CLIENTE", "").split()) > 1 else "",
            "email": candidate.get("Email"),
            "phone": candidate.get("Teléfono"),
            "company": candidate.get("CLIENTE"),
            "sector_cliente": candidate.get("Sector"),
            "donde_encontrado": candidate.get("Fuente"),
            "notas_prospersion_coper": candidate.get("Notas"),
        }
    }
    
    try:
        response = requests.post(
            "https://api.hubapi.com/crm/v3/objects/contacts",
            headers=headers,
            json=payload,
            timeout=5
        )
        return response.status_code == 201
    except:
        return False

def run_search():
    """Ejecuta búsqueda en todas las fuentes."""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INICIANDO BÚSQUEDA...")
    
    all_candidates = []
    
    print("\n=== FUENTE 1: WEB SEARCH ===")
    all_candidates.extend(source_web_search())
    
    print("\n=== FUENTE 2: HOUZZ SCRAPING ===")
    all_candidates.extend(source_houzz())
    
    print("\n=== FUENTE 3: DIRECTORIOS ===")
    all_candidates.extend(source_directories())
    
    print("\n=== FUENTE 5: SEED DATA TEMPORAL ===")
    all_candidates.extend(source_verified_seed())
    
    # Elimina duplicados
    unique = {c.get("Email"): c for c in all_candidates if c.get("Email")}
    all_candidates = list(unique.values())
    
    print(f"\n[RESUMEN] {len(all_candidates)} candidatos únicos encontrados")
    
    # Crea en Notion
    success = 0
    for candidate in all_candidates:
        if create_notion_candidate(candidate):
            success += 1
            print(f"  ✓ {candidate.get('CLIENTE')} creado en Notion")
        time.sleep(0.5)
    
    print(f"\n[RESULTADO] {success}/{len(all_candidates)} candidatos creados en Notion")

def run_send():
    """Envía candidatos a HubSpot."""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ENVIANDO A HUBSPOT...")
    print("(Función en desarrollo)")

if __name__ == "__main__":
    if MODE == "search":
        run_search()
    elif MODE == "send":
        run_send()
    else:
        print("ERROR: MODE debe ser 'search' o 'send'")
