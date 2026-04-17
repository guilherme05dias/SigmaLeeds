import json
import sqlite3
import openpyxl
from database.schema import get_connection
from database.services.blacklist_service import is_blacklisted

def create_campaign(name: str, message_template: str, attachment_path: str = None, account_id: int = None) -> int:
    """Cria campanha e retorna o ID."""
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO campaigns (name, message_template, attachment_path, account_id)
                VALUES (?, ?, ?, ?)
            ''', (name, message_template, attachment_path, account_id))
            return cursor.lastrowid
    except Exception:
        return -1
    finally:
        conn.close()

def import_contacts_from_xlsx(campaign_id: int, xlsx_path: str) -> dict:
    """
    Lê o .xlsx, mapeia colunas automaticamente e insere contatos.
    """
    results = {"total": 0, "imported": 0, "skipped_blacklist": 0, "errors": []}
    
    try:
        wb = openpyxl.load_workbook(xlsx_path, data_only=True)
        sheet = wb.active
        headers = [str(cell.value).strip().lower() if cell.value else f"col_{i}" for i, cell in enumerate(sheet[1])]
        
        name_col = -1
        phone_col = -1
        company_col = -1
        
        for i, header in enumerate(headers):
            if header in ['nome', 'cliente', 'contato']:
                name_col = i
            elif header in ['numero', 'whatsapp', 'telefone', 'celular']:
                phone_col = i
            elif header in ['empresa', 'razao_social', 'fantasia']:
                company_col = i
                
        if phone_col == -1:
            results["errors"].append("Coluna de telefone não encontrada.")
            return results
        
        conn = get_connection()
        rows_to_insert = []
        for index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            if not row or not any(row):
                continue
            
            results["total"] += 1
            
            phone = str(row[phone_col]).strip() if len(row) > phone_col and row[phone_col] else ""
            if not phone:
                results["errors"].append(f"Linha {index}: Telefone vazio")
                continue
                
            name = str(row[name_col]).strip() if name_col != -1 and len(row) > name_col and row[name_col] else ""
            company = str(row[company_col]).strip() if company_col != -1 and len(row) > company_col and row[company_col] else ""
            
            if is_blacklisted(phone):
                results["skipped_blacklist"] += 1
                continue
                
            extra_fields = {}
            for i, header in enumerate(headers):
                if i not in [name_col, phone_col, company_col] and len(row) > i:
                    val = str(row[i]).strip() if row[i] is not None else ""
                    if val:
                        extra_fields[header] = val
                        
            rows_to_insert.append((
                campaign_id, name, phone, company, json.dumps(extra_fields)
            ))
            
        with conn:
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT INTO campaign_contacts (campaign_id, name, phone, company, extra_fields)
                VALUES (?, ?, ?, ?, ?)
            ''', rows_to_insert)
            
            results["imported"] = len(rows_to_insert)
            
            cursor.execute("UPDATE campaigns SET total_contacts = total_contacts + ? WHERE id = ?", (results["imported"], campaign_id))
            
        conn.close()
    except Exception as e:
        results["errors"].append(str(e))
        
    return results

def get_pending_contacts(campaign_id: int, limit: int = None) -> list:
    """Retorna contatos com status PENDENTE."""
    conn = get_connection()
    try:
        query = "SELECT * FROM campaign_contacts WHERE campaign_id = ? AND status = 'PENDENTE' ORDER BY id ASC"
        params = [campaign_id]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
            
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()

def update_contact_status(contact_id: int, status: str, error_message: str = None) -> None:
    """Atualiza status de um contato. Status: ENVIADO | INVÁLIDO | ERRO | EM_PROCESSAMENTO"""
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            query = "UPDATE campaign_contacts SET status = ?"
            params = [status]
            
            if status == "ENVIADO":
                query += ", sent_at = CURRENT_TIMESTAMP"
                
            if error_message is not None:
                query += ", error_message = ?"
                params.append(error_message)
                
            query += " WHERE id = ?"
            params.append(contact_id)
            
            cursor.execute(query, params)
            
            cursor.execute("SELECT campaign_id FROM campaign_contacts WHERE id = ?", (contact_id,))
            row = cursor.fetchone()
            if row:
                c_id = row['campaign_id']
                if status == "ENVIADO":
                    cursor.execute("UPDATE campaigns SET sent = sent + 1 WHERE id = ?", (c_id,))
                elif status == "ERRO":
                    cursor.execute("UPDATE campaigns SET failed = failed + 1 WHERE id = ?", (c_id,))
                elif status == "INVÁLIDO":
                    cursor.execute("UPDATE campaigns SET invalid = invalid + 1 WHERE id = ?", (c_id,))
    except Exception:
        pass
    finally:
        conn.close()

def get_campaign_stats(campaign_id: int) -> dict:
    """Retorna estatísticas."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT total_contacts, sent, failed, invalid 
            FROM campaigns WHERE id = ?
        ''', (campaign_id,))
        row = cursor.fetchone()
        if not row:
            return {"total": 0, "sent": 0, "failed": 0, "invalid": 0, "pending": 0}
            
        cursor.execute("SELECT COUNT(*) as pending FROM campaign_contacts WHERE campaign_id = ? AND status = 'PENDENTE'", (campaign_id,))
        pending = cursor.fetchone()['pending']
        
        return {
            "total": row['total_contacts'],
            "sent": row['sent'],
            "failed": row['failed'],
            "invalid": row['invalid'],
            "pending": pending
        }
    except Exception:
        return {"total": 0, "sent": 0, "failed": 0, "invalid": 0, "pending": 0}
    finally:
        conn.close()

def get_campaign_history() -> list:
    """Retorna todas as campanhas com suas estatísticas para o histórico."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()

def export_campaign_to_xlsx(campaign_id: int, output_path: str) -> str:
    """Exporta resultado da campanha para .xlsx. Retorna o caminho do arquivo."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaign_contacts WHERE campaign_id = ? ORDER BY id ASC", (campaign_id,))
        rows = cursor.fetchall()
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["ID", "Name", "Phone", "Company", "Status", "Sent At", "Error Message"])
        
        for r in rows:
            ws.append([
                r['id'], r['name'], r['phone'], r['company'],
                r['status'], r['sent_at'], r['error_message']
            ])
            
        wb.save(output_path)
        return output_path
    except Exception:
        return ""
    finally:
        conn.close()

def reset_processing_contacts(campaign_id: int) -> int:
    """Reseta EM_PROCESSAMENTO → PENDENTE. Retorna quantidade resetada."""
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE campaign_contacts 
                SET status = 'PENDENTE' 
                WHERE campaign_id = ? AND status = 'EM_PROCESSAMENTO'
            ''', (campaign_id,))
            return cursor.rowcount
    except Exception:
        return 0
    finally:
        conn.close()
