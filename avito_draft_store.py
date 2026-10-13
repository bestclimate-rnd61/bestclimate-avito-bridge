"""Durable XML draft staging for Avito. Never publishes automatically."""
import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(os.getenv('AVITO_DRAFT_DIR', '/data/avito_drafts'))

def stage(task_id, action, items):
    if action not in ('bulk_edit', 'bulk_publish'):
        raise ValueError('unsupported action')
    if not items or len(items) > 100:
        raise ValueError('invalid batch size')
    root = ET.Element('Ads', {'formatVersion': '3', 'target': 'Avito.ru'})
    for item in items:
        ad = ET.SubElement(root, 'Ad')
        for tag, value in [('Id', item['id']), ('Title', item['title']), ('Price', item['price'])]:
            ET.SubElement(ad, tag).text = str(value)
    ROOT.mkdir(parents=True, exist_ok=True)
    name = ''.join(ch for ch in task_id if ch.isalnum() or ch in '-_')[:80]
    if not name:
        raise ValueError('invalid task id')
    path = ROOT / (name + '.xml')
    tmp = ROOT / (name + '.tmp')
    tmp.write_bytes(ET.tostring(root, encoding='utf-8', xml_declaration=True))
    os.replace(tmp, path)
    (ROOT / (name + '.json')).write_text(json.dumps({'action': action, 'status': 'awaiting_schema_validation', 'published': False, 'count': len(items)}), encoding='utf-8')
    return {'status': 'draft_saved', 'path': str(path), 'published': False, 'count': len(items)}
