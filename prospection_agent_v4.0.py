#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import json
import logging
from datetime import datetime
import time
import os
import re
from urllib.parse import quote

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")
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

SEARCH_KEYWORDS = ["arquitecto Guadalajara diseño", "interiorista Jalisco", "despacho arquitectura"]

def validate_email(email):
    if not email or "@" not in email:
        return False
    bad_domains = ["example.com", "test.com"]
    domain = email.split("@")[1].lower()
    if any(bad in domain for bad in bad_domains):
        return False
    return re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email) is not None

def score_candidate(candidate):
    score = 0
    if validate_email(candidate.get("email", "")):
        score += 20
    else:
        return 0, "Email invalido", False
    if candidate.get("website"):
        score += 15
    role = candidate.get("role", "").lower()
    if any(r in role for r in ["arquitecto", "diseñador"]):
        score += 25
    sector = candidate.get("sector", "").lower()
    if any(s in sector for s in ["arquitectura", "diseño"]):
        score += 20
    return score, "Valido", score >= 60

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
                if any(w in text.lower() for w in ["arquitecto", "diseño"]):
                    candidate = {"name": text[:60], "email": "info@example.com", "role": "Profesional", "sector": "Arquitectura", "website": url, "company": text[:40]}
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
            logger.info(f"Notion: {candidate.get('name')} creado")
            return True
        return False
    except Exception as e:
        logger.error(f"Error Notion: {e}")
        return False

def read_notion_validated():
    try:
        url = f"{NOTION_BASE_URL}/databases/{NOTION_DATA_SOURCE_ID}/query"
        payload = {"filter": {"property": "Cliente valido COPER", "checkbox": {"equals": True}}}
        response = requests.post(url, json=payload, headers=headers_notion, timeout=10)
        if response.status_code == 200:
            pages = response.json().get("results", [])
            return len(pages)
        return 0
    except:
        return 0

def create_hubspot_contact(candidate):
    try:
        url = f"{HUBSPOT_BASE_URL}/crm/v3/objects/contacts"
        payload = {
            "properties": {
                "firstname": candidate.get("name", "Unknown")[:30],
                "email": candidate.get("email", ""),
                "lifecyclestage": "lead"
            }
        }
        response = requests.post(url, json=payload, headers=headers_hubspot, timeout=10)
        if response.status_code in [200, 201]:
            logger.info(f"HubSpot: {
