import requests

BASE = 'http://127.0.0.1:8000'

def test_api():
    print('Testing GET /api/dashboard/stats ...')
    res = requests.get(f'{BASE}/api/dashboard/stats')
    assert res.status_code == 200, f'Stats failed: {res.text}'
    stats = res.json()
    print('Stats:', stats)

    print('Testing GET /api/leads ...')
    res = requests.get(f'{BASE}/api/leads')
    assert res.status_code == 200
    leads = res.json()
    print(f'Retrieved {len(leads)} leads.')
    assert len(leads) >= 4

    print('Testing POST /api/leads (New customer workflow) ...')
    new_lead_payload = {
        'name': 'Hiteshbhai Soni',
        'company': 'Soni Jewellers (Rajkot)',
        'phone': '+919924098765',
        'email': 'hitesh@sonijewellers.in',
        'budget': 95000,
        'source': 'Instagram',
        'requirement': 'Urgent requirement for CRM software to track high net-worth jewellery buyers with WhatsApp catalog delivery.'
    }
    res = requests.post(f'{BASE}/api/leads', json=new_lead_payload)
    assert res.status_code == 200
    created = res.json()
    lead_id = created['id']
    print(f'Lead created successfully with ID {lead_id}!')
    print('AI Score:', created['latest_analysis']['lead_score'])
    print('AI Sentiment:', created['latest_analysis']['sentiment'])
    print('AI Priority:', created['latest_analysis']['priority'])
    print('AI Suggested Action:', created['latest_analysis']['suggested_action'])

    print('Testing POST /api/leads/{id}/interactions (Adding customer message) ...')
    note_payload = {
        'type': 'WhatsApp',
        'direction': 'Inbound',
        'content': 'We saw your demo preview on Instagram and we are very interested. Can you send price quotation today?'
    }
    res = requests.post(f'{BASE}/api/leads/{lead_id}/interactions', json=note_payload)
    assert res.status_code == 200
    updated = res.json()
    print('Updated AI Lead Score:', updated['latest_analysis']['lead_score'])
    print('Updated AI Draft Reply preview:', updated['latest_analysis']['draft_reply'][:120])

    print('Testing POST /api/leads/{id}/close-deal (Won) ...')
    close_payload = {
        'status': 'Won',
        'deal_value': 95000
    }
    res = requests.post(f'{BASE}/api/leads/{lead_id}/close-deal', json=close_payload)
    assert res.status_code == 200
    closed = res.json()
    assert closed['status'] == 'Won'
    assert closed['is_customer'] == True
    print('Deal successfully Won and converted to active customer!')

    print('All API tests passed with 100% success!')

if __name__ == '__main__':
    test_api()
