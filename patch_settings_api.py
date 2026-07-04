
with open('backend/main.py', 'a', encoding='utf-8') as f:
    f.write('''

# ==========================================
# Settings API (Dynamic Filters & Cards)
# ==========================================

from backend.database import get_dynamic_filters, save_dynamic_filter, delete_dynamic_filter, get_dynamic_cards, save_dynamic_card, delete_dynamic_card

@app.get('/api/settings/filters')
async def api_get_dynamic_filters(current_user: Optional[dict] = Depends(get_optional_user)):
    try:
        module_id = current_user.get('module_id', 1) if current_user else 1
        filters = get_dynamic_filters(module_id)
        return {'success': True, 'filters': filters}
    except Exception as e:
        return {'success': False, 'message': str(e)}

@app.post('/api/settings/filters')
async def api_save_dynamic_filter(request: Request, current_user: Optional[dict] = Depends(get_optional_user)):
    try:
        data = await request.json()
        module_id = current_user.get('module_id', 1) if current_user else 1
        fid = save_dynamic_filter(
            module_id,
            data.get('field_name'),
            data.get('filter_type'),
            data.get('validation_id'),
            data.get('target_column'),
            data.get('is_active', 1),
            data.get('id')
        )
        return {'success': True, 'id': fid}
    except Exception as e:
        return {'success': False, 'message': str(e)}

@app.delete('/api/settings/filters/{filter_id}')
async def api_delete_dynamic_filter(filter_id: int, current_user: Optional[dict] = Depends(get_optional_user)):
    try:
        module_id = current_user.get('module_id', 1) if current_user else 1
        delete_dynamic_filter(filter_id, module_id)
        return {'success': True}
    except Exception as e:
        return {'success': False, 'message': str(e)}

@app.get('/api/settings/cards')
async def api_get_dynamic_cards(current_user: Optional[dict] = Depends(get_optional_user)):
    try:
        module_id = current_user.get('module_id', 1) if current_user else 1
        cards = get_dynamic_cards(module_id)
        return {'success': True, 'cards': cards}
    except Exception as e:
        return {'success': False, 'message': str(e)}

@app.post('/api/settings/cards')
async def api_save_dynamic_card(request: Request, current_user: Optional[dict] = Depends(get_optional_user)):
    try:
        data = await request.json()
        module_id = current_user.get('module_id', 1) if current_user else 1
        cid = save_dynamic_card(
            module_id,
            data.get('card_name'),
            data.get('calc_type'),
            data.get('validation_id'),
            data.get('target_column'),
            data.get('sub_calc'),
            data.get('is_active', 1),
            data.get('id')
        )
        return {'success': True, 'id': cid}
    except Exception as e:
        return {'success': False, 'message': str(e)}

@app.delete('/api/settings/cards/{card_id}')
async def api_delete_dynamic_card(card_id: int, current_user: Optional[dict] = Depends(get_optional_user)):
    try:
        module_id = current_user.get('module_id', 1) if current_user else 1
        delete_dynamic_card(card_id, module_id)
        return {'success': True}
    except Exception as e:
        return {'success': False, 'message': str(e)}
''')

