import os
os.environ['ZAP_DB_MEMORY'] = '1'

import pytest
import openpyxl
from database import init_db
from database.services.campaign_service import create_campaign, import_contacts_from_xlsx, get_pending_contacts, update_contact_status, get_campaign_stats, get_campaign_history, export_campaign_to_xlsx, reset_processing_contacts
from database.services.blacklist_service import add_to_blacklist, is_blacklisted, detect_optout_keywords, get_blacklist, remove_from_blacklist
from database.services.template_service import create_template, render_template, get_all_templates
from database.services.config_service import set_config, get_config

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    db_path = os.path.join(os.getcwd(), 'data', 'test_app.db')
    if os.path.exists(db_path):
        try: os.remove(db_path)
        except: pass
    init_db()

def test_config():
    set_config('test_key', 'test_value')
    assert get_config('test_key') == 'test_value'
    
    set_config('json_key', {'a': 1, 'b': 2})
    val = get_config('json_key')
    assert type(val) == dict
    assert val['a'] == 1

def test_blacklist():
    add_to_blacklist('5511999999999', 'MANUAL')
    assert is_blacklisted('5511999999999') == True
    assert is_blacklisted('5511888888888') == False
    
    assert detect_optout_keywords("Gostaria de SAIR da lista") == True
    assert detect_optout_keywords("Nao quero receber") == True
    assert detect_optout_keywords("Olá tudo bem") == False

def test_template():
    t_id = create_template('Promo', 'Olá {nome}, temos promo para {empresa}. Seu ticket: {ticket}')
    assert t_id > 0
    
    res = render_template('Olá {nome}, temos promo para {empresa}. Seu ticket: {ticket}', {
        'name': 'João',
        'company': 'Tech',
        'extra_fields': '{"ticket": "1234"}'
    })
    
    assert "Olá João, temos promo para Tech. Seu ticket: 1234" in res
    
    res_missing = render_template('Promo: {desconto}.', {})
    assert "{desconto}" in res_missing

def test_campaign():
    c_id = create_campaign('Black Friday', 'Olá {nome}')
    assert c_id > 0
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Nome", "Telefone", "Empresa", "Vendedor"])
    ws.append(["Joao", "5511888888888", "Tech", "Carlos"])
    ws.append(["Maria", "5511999999999", "Dev", "Ana"]) 
    ws.append(["Jose", "", "", ""]) 
    
    test_xlsx = "test_import.xlsx"
    wb.save(test_xlsx)
    
    res = import_contacts_from_xlsx(c_id, test_xlsx)
    if os.path.exists(test_xlsx):
        os.remove(test_xlsx)
    
    assert res['total'] == 3 
    assert res['imported'] == 1 
    assert res['skipped_blacklist'] == 1 
    
    pending = get_pending_contacts(c_id)
    assert len(pending) == 1
    
    contact_id = pending[0]['id']
    
    update_contact_status(contact_id, 'EM_PROCESSAMENTO')
    reset_count = reset_processing_contacts(c_id)
    assert reset_count == 1
    
    update_contact_status(contact_id, 'ENVIADO')
    
    stats = get_campaign_stats(c_id)
    assert stats['sent'] == 1
    assert stats['pending'] == 0
