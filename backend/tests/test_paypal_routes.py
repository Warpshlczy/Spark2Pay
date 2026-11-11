"""
PayPal execution API route tests (simulation mode) - the full agentic loop.
"""


def test_begin_action_requires_auth(client):
    resp = client.post('/api/v1/paypal/actions',
                       json={'subscription_id': 1, 'action_type': 'cancel'})
    assert resp.status_code == 401


def test_begin_and_complete_cancel_closes_loop(client, seeded_user):
    headers, data = seeded_user

    # 1. Begin
    resp = client.post('/api/v1/paypal/actions', headers=headers, json={
        'subscription_id': data['netflix_id'],
        'action_type': 'cancel',
        'reason': 'Unused for 92 days',
        'origin': 'ai_recommendation'
    })
    assert resp.status_code == 201
    body = resp.get_json()['data']
    assert body['status'] == 'pending_approval'
    assert body['mode'] == 'simulation'
    assert body['estimated_monthly_savings'] == 22.99
    assert '/paypal/approve/' in body['approve_link']
    action_id = body['action_id']

    # 2. Complete
    resp = client.post(f'/api/v1/paypal/actions/{action_id}/complete',
                       headers=headers)
    assert resp.status_code == 200
    done = resp.get_json()['data']
    assert done['status'] == 'completed'
    assert done['paypal_subscription_id'] == 'SIM-SUB-NETFLIX'
    assert done['executed_at'] is not None

    # 3. Closed loop: subscription now inactive in the tracking system
    resp = client.get(f"/api/v1/subscriptions/{data['netflix_id']}",
                      headers=headers)
    sub = resp.get_json()['data']
    assert sub['inactive'] is True
    assert sub['cancellation_date'] is not None
    assert sub['auto_renew'] is False

    # 4. Audit trail shows the finished action
    resp = client.get('/api/v1/paypal/actions', headers=headers)
    trail = resp.get_json()['data']
    assert len(trail) == 1
    assert trail[0]['action_type'] == 'cancel'
    assert trail[0]['status'] == 'completed'
    assert trail[0]['payload']['origin'] == 'ai_recommendation'


def test_begin_action_rejects_card_managed_subscription(client, seeded_user):
    headers, data = seeded_user
    resp = client.post('/api/v1/paypal/actions', headers=headers, json={
        'subscription_id': data['hulu_id'],  # no paypal_subscription_id
        'action_type': 'cancel'
    })
    assert resp.status_code == 409
    assert resp.get_json()['code'] == 'not_paypal_managed'


def test_complete_twice_is_rejected(client, seeded_user):
    headers, data = seeded_user
    resp = client.post('/api/v1/paypal/actions', headers=headers, json={
        'subscription_id': data['adobe_id'], 'action_type': 'cancel'})
    action_id = resp.get_json()['data']['action_id']

    assert client.post(f'/api/v1/paypal/actions/{action_id}/complete',
                       headers=headers).status_code == 200
    resp = client.post(f'/api/v1/paypal/actions/{action_id}/complete',
                       headers=headers)
    assert resp.status_code == 409


def test_reject_keeps_audit_honest(client, seeded_user):
    headers, data = seeded_user
    resp = client.post('/api/v1/paypal/actions', headers=headers, json={
        'subscription_id': data['adobe_id'], 'action_type': 'cancel'})
    action_id = resp.get_json()['data']['action_id']

    resp = client.post(f'/api/v1/paypal/actions/{action_id}/reject',
                       headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['data']['status'] == 'rejected'

    resp = client.get(f"/api/v1/subscriptions/{data['adobe_id']}",
                      headers=headers)
    assert resp.get_json()['data']['inactive'] is False  # untouched


def test_invalid_action_type(client, seeded_user):
    headers, data = seeded_user
    resp = client.post('/api/v1/paypal/actions', headers=headers, json={
        'subscription_id': data['adobe_id'], 'action_type': 'destroy'})
    assert resp.status_code == 400


def test_pay_action_defaults_amount_and_currency(client, seeded_user):
    headers, data = seeded_user
    resp = client.post('/api/v1/paypal/actions', headers=headers, json={
        'subscription_id': data['adobe_id'], 'action_type': 'pay'})
    assert resp.status_code == 201
    body = resp.get_json()['data']
    action_id = body['action_id']
    assert body['status'] == 'pending_approval'

    resp = client.post(f'/api/v1/paypal/actions/{action_id}/complete',
                       headers=headers)
    done = resp.get_json()['data']
    assert done['status'] == 'completed'
    assert done['paypal_capture_id'].startswith('SIM-CAP-')
    assert done['amount'] == 59.99
    assert done['currency'] == 'USD'


def test_webhook_subscription_cancelled_propagates(client, seeded_user):
    headers, data = seeded_user
    resp = client.post('/api/v1/paypal/webhook', json={
        'event_type': 'BILLING.SUBSCRIPTION.CANCELLED',
        'resource': {'id': 'SIM-SUB-ADOBE'}})
    assert resp.status_code == 200
    assert resp.get_json()['handled'] is True

    resp = client.get(f"/api/v1/subscriptions/{data['adobe_id']}",
                      headers=headers)
    assert resp.get_json()['data']['inactive'] is True


def test_webhook_bad_body(client):
    resp = client.post('/api/v1/paypal/webhook', data='not json',
                       content_type='text/plain')
    assert resp.status_code == 400


def test_paypal_config_endpoint(client, seeded_user):
    headers, _ = seeded_user
    resp = client.get('/api/v1/paypal/config', headers=headers)
    data = resp.get_json()['data']
    assert data['mode'] == 'simulation'
    assert data['sandbox_configured'] is False
