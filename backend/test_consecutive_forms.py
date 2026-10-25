import io
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_consecutive_different_forms_generate_distinct_pdfs():
    # 1. Start a session
    s_resp = client.post('/api/v1/sessions', json={'preferred_language': 'en'})
    assert s_resp.status_code == 200, s_resp.text
    sid = s_resp.json()['id']

    # 2. Verify phone OTP
    o_resp = client.post('/api/v1/auth/otp/send', json={'session_id': sid, 'phone': '9876543210'})
    assert o_resp.status_code == 200, o_resp.text
    otp_data = o_resp.json()

    v_resp = client.post('/api/v1/auth/otp/verify', json={'session_id': sid, 'otp_id': otp_data['otp_id'], 'code': '123456'})
    assert v_resp.status_code == 200, v_resp.text

    # 3. Form 1: Download PM Kisan demo template & upload
    pm_resp = client.get('/api/v1/forms/demo-templates/pm_kisan')
    assert pm_resp.status_code == 200
    form1_upload = client.post(
        '/api/v1/forms/upload',
        data={'session_id': sid, 'language': 'en'},
        files={'file': ('pm_kisan.pdf', io.BytesIO(pm_resp.content), 'application/pdf')}
    )
    assert form1_upload.status_code == 200, form1_upload.text
    f1_id = form1_upload.json()['form_id']
    f1_fields = form1_upload.json()['fields']
    assert len(f1_fields) > 0

    def get_valid_value(f_type):
        if f_type == 'phone': return '9876543210'
        if f_type == 'number': return '123456789012'
        if f_type == 'date': return '15 August 1980'
        return 'Farmer John'

    # Answer & confirm all fields of Form 1
    for f in f1_fields:
        fid = f['id']
        val = get_valid_value(f.get('field_type', 'text'))
        ans = client.post(f'/api/v1/forms/{f1_id}/fields/{fid}/answer', json={'transcribed_text': val, 'language': 'en'})
        assert ans.status_code == 200, ans.text
        nid = ans.json().get('nonce_id')
        if nid:
            conf = client.post(f'/api/v1/confirmations/{nid}/respond', json={'session_id': sid, 'transcribed_text': ans.json()['challenge_phrase']})
            assert conf.status_code == 200, conf.text

    # Final challenge & finalize Form 1
    c1 = client.post('/api/v1/confirmations', json={'session_id': sid, 'bound_action': 'submit_form', 'bound_target_id': f1_id})
    assert c1.status_code == 200
    r1 = client.post(f'/api/v1/confirmations/{c1.json()["nonce_id"]}/respond', json={'session_id': sid, 'transcribed_text': c1.json()['challenge_phrase']})
    assert r1.status_code == 200
    fin1 = client.post(f'/api/v1/forms/{f1_id}/finalize')
    assert fin1.status_code == 200, fin1.text
    dl1 = client.get(f'/forms/{f1_id}/download')
    assert dl1.status_code == 200
    assert 'no-store' in dl1.headers.get('cache-control', '')
    pdf1_bytes = dl1.content
    assert len(pdf1_bytes) > 100

    # 4. Form 2: Download Pension demo template & upload in the same session!
    pen_resp = client.get('/api/v1/forms/demo-templates/pension')
    assert pen_resp.status_code == 200
    form2_upload = client.post(
        '/api/v1/forms/upload',
        data={'session_id': sid, 'language': 'en'},
        files={'file': ('pension.pdf', io.BytesIO(pen_resp.content), 'application/pdf')}
    )
    assert form2_upload.status_code == 200, form2_upload.text
    f2_id = form2_upload.json()['form_id']
    f2_fields = form2_upload.json()['fields']
    assert len(f2_fields) > 0
    assert f1_id != f2_id, 'Second form must have a distinct form_id'

    # Answer & confirm all fields of Form 2
    for f in f2_fields:
        fid = f['id']
        val = get_valid_value(f.get('field_type', 'text'))
        ans = client.post(f'/api/v1/forms/{f2_id}/fields/{fid}/answer', json={'transcribed_text': val, 'language': 'en'})
        assert ans.status_code == 200, ans.text
        nid = ans.json().get('nonce_id')
        if nid:
            conf = client.post(f'/api/v1/confirmations/{nid}/respond', json={'session_id': sid, 'transcribed_text': ans.json()['challenge_phrase']})
            assert conf.status_code == 200

    # Final challenge & finalize Form 2
    c2 = client.post('/api/v1/confirmations', json={'session_id': sid, 'bound_action': 'submit_form', 'bound_target_id': f2_id})
    assert c2.status_code == 200
    r2 = client.post(f'/api/v1/confirmations/{c2.json()["nonce_id"]}/respond', json={'session_id': sid, 'transcribed_text': c2.json()['challenge_phrase']})
    assert r2.status_code == 200
    fin2 = client.post(f'/api/v1/forms/{f2_id}/finalize')
    assert fin2.status_code == 200, fin2.text
    dl2 = client.get(f'/forms/{f2_id}/download')
    assert dl2.status_code == 200
    assert 'no-store' in dl2.headers.get('cache-control', '')
    pdf2_bytes = dl2.content
    assert len(pdf2_bytes) > 100

    # Verify that the two PDFs are completely distinct
    assert pdf1_bytes != pdf2_bytes, 'Consecutive form PDFs must be distinct and not reused!'
