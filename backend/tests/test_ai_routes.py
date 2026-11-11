"""
AI advice API + LLM function-calling tests.
"""
import json
from unittest import mock


def test_recommendations_endpoint_heuristic(client, seeded_user):
    headers, data = seeded_user
    resp = client.get('/api/v1/ai/recommendations', headers=headers)
    assert resp.status_code == 200
    body = resp.get_json()['data']

    assert body['engine'] == 'heuristic'
    assert body['paypal_mode'] == 'simulation'
    assert len(body['advice']) >= 1

    netflix_advice = next(a for a in body['advice']
                          if a['subscription_id'] == data['netflix_id'])
    assert netflix_advice['action_available'] is True
    assert netflix_advice['estimated_monthly_savings'] == 22.99
    assert netflix_advice['subscription']['name'] == 'Netflix'

    hulu_advice = next((a for a in body['advice']
                        if a['subscription_id'] == data['hulu_id']), None)
    # Hulu is actively used -> no advice, or if present it must be honest
    if hulu_advice:
        assert hulu_advice['action_available'] is False


def test_ai_status_endpoint(client, seeded_user):
    headers, _ = seeded_user
    resp = client.get('/api/v1/ai/status', headers=headers)
    data = resp.get_json()['data']
    assert data['paypal']['mode'] == 'simulation'
    assert 'effective_provider' in data['ai']


SYSTEM_FINAL_JSON = {
    'content': json.dumps({
        'summary': 'Cancel Netflix to save $22.99/month.',
        'recommendations': [{
            'subscription_id': 1,
            'title': 'Cancel Netflix',
            'recommended_action': 'cancel',
            'rationale': 'Unused for 92 days.',
            'estimated_monthly_savings': 22.99,
            'confidence': 0.95
        }]
    }),
    'tool_calls': None
}


def _llm_message(content, tool_calls=None):
    return {'content': content, 'tool_calls': tool_calls}


def test_llm_advisor_tool_call_loop(app, seeded_user):
    """
    Simulated LLM: first answers with a manage_with_paypal tool call, then
    (after the proposal is fed back) returns the final JSON. The tool
    proposal must be validated and recorded, and advice must be merged.
    """
    headers, data = seeded_user
    netflix_id = data['netflix_id']

    tool_call_msg = _llm_message(None, tool_calls=[{
        'id': 'call_1',
        'function': {
            'name': 'manage_with_paypal',
            'arguments': json.dumps({
                'subscription_id': netflix_id,
                'action': 'cancel',
                'reason': 'Unused 92 days'
            })
        }
    }])
    final_json = {
        'content': json.dumps({
            'summary': 'Cancel Netflix.',
            'recommendations': [{
                'subscription_id': netflix_id,
                'title': 'Cancel Netflix',
                'recommended_action': 'cancel',
                'rationale': 'Unused for 92 days.',
                'estimated_monthly_savings': 22.99,
                'confidence': 0.95
            }]
        }),
        'tool_calls': None
    }

    with app.app_context():
        from app.services.ai_service import LLMAdvisor, AIServiceError
        advisor = LLMAdvisor.__new__(LLMAdvisor)  # skip __init__ config probe
        advisor.provider = 'openai'
        advisor.model = 'gpt-4o-mini'
        advisor.base_url = 'https://mock'
        advisor.api_key = 'sk-test'

        with mock.patch.object(LLMAdvisor, '_chat',
                               side_effect=[tool_call_msg, final_json]):
            context = {
                'currency_symbol': '$', 'monthly_total': 100.0,
                'monthly_budget': 200.0,
                'subscriptions': [{
                    'id': netflix_id, 'name': 'Netflix', 'price': 22.99,
                    'currency': 'USD', 'billing': 'Monthly',
                    'monthly_cost': 22.99, 'next_payment': '2026-11-21',
                    'category': 'Streaming',
                    'last_used_at': '2026-08-12T00:00:00',
                    'usage_count_30d': 0, 'created_at': '2026-01-01T00:00:00',
                    'paypal_managed': True
                }]
            }
            result = advisor.generate(context)

    assert result['summary'] == 'Cancel Netflix.'
    assert len(result['tool_proposals']) == 1
    assert result['tool_proposals'][0]['valid'] is True
    assert result['advice'][0]['estimated_monthly_savings'] == 22.99
    assert result['advice'][0]['action_available'] is True


def test_llm_advisor_rejects_unknown_subscription(app, seeded_user):
    """A hallucinated subscription_id must be flagged invalid, never merged."""
    tool_call_msg = _llm_message(None, tool_calls=[{
        'id': 'call_1',
        'function': {
            'name': 'manage_with_paypal',
            'arguments': json.dumps({
                'subscription_id': 99999,
                'action': 'cancel',
                'reason': 'hallucination'
            })
        }
    }])
    final_json = {'content': json.dumps({'summary': '', 'recommendations': []}),
                  'tool_calls': None}

    with app.app_context():
        from app.services.ai_service import LLMAdvisor
        advisor = LLMAdvisor.__new__(LLMAdvisor)
        advisor.provider = 'openai'
        advisor.model = 'gpt-4o-mini'
        advisor.base_url = 'https://mock'
        advisor.api_key = 'sk-test'

        with mock.patch.object(LLMAdvisor, '_chat',
                               side_effect=[tool_call_msg, final_json]):
            result = advisor.generate({
                'currency_symbol': '$', 'monthly_total': 22.99,
                'monthly_budget': None,
                'subscriptions': [{
                    'id': 1, 'name': 'Netflix', 'price': 22.99,
                    'currency': 'USD', 'billing': 'Monthly',
                    'monthly_cost': 22.99, 'next_payment': None,
                    'category': 'Streaming', 'last_used_at': None,
                    'usage_count_30d': 0, 'created_at': '2026-01-01T00:00:00',
                    'paypal_managed': True
                }]
            })

    assert result['tool_proposals'][0]['valid'] is False
    assert result['advice'] == []


def test_llm_final_answer_must_be_json(app, seeded_user):
    with app.app_context():
        from app.services.ai_service import LLMAdvisor, AIServiceError
        advisor = LLMAdvisor.__new__(LLMAdvisor)
        advisor.provider = 'openai'
        advisor.model = 'gpt-4o-mini'
        advisor.base_url = 'https://mock'
        advisor.api_key = 'sk-test'

        with mock.patch.object(LLMAdvisor, '_chat',
                               return_value=_llm_message('I recommend '
                                                         'cancelling things!')):
            try:
                advisor.generate({
                    'currency_symbol': '$', 'monthly_total': 0,
                    'monthly_budget': None,
                    'subscriptions': [{'id': 1, 'name': 'X', 'price': 1,
                                       'currency': 'USD', 'billing': 'Monthly',
                                       'monthly_cost': 1, 'next_payment': None,
                                       'category': None,
                                       'last_used_at': None,
                                       'usage_count_30d': 0,
                                       'created_at': '2026-01-01T00:00:00',
                                       'paypal_managed': False}]
                })
                assert False, 'expected AIServiceError'
            except AIServiceError as exc:
                assert 'JSON' in str(exc)
