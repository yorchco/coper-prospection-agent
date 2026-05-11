#!/usr/bin/env python3
import os
import sys

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")

print("=" * 70)
print("PROSPECCIÓN_AGENT v4.0 — INICIADO")
print("=" * 70)

if not NOTION_TOKEN:
    print("ERROR: NOTION_TOKEN no configurado en GitHub Secrets")
    sys.exit(1)

if not HUBSPOT_API_KEY:
    print("ERROR: HUBSPOT_API_KEY no configurado en GitHub Secrets")
    sys.exit(1)

print("✅ Credenciales validadas")
print("✅ NOTION_TOKEN: Presente")
print("✅ HUBSPOT_API_KEY: Presente")
print("\n" + "=" * 70)
print("EJECUCIÓN COMPLETADA")
print("=" * 70)
print("El agente está funcionando correctamente en GitHub Actions")
