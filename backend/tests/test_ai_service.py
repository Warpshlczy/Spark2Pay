"""
Heuristic advisor + AI facade tests
"""
from datetime import datetime, timedelta

from app import db
from app.models import User, Currency, Category, Subscription, SubscriptionUsage
from app.services import ai_service
from app.services.ai_service import HeuristicAdvisor


def _context(app, user_id, subs_spec):
    with app.app_context():
        user = db.session.get(User, user_id)
        usd = user.currencies[0]
        cat = Category(user_id=user_id, name='Test', order=0)
        db.session.add(cat)
        db.session.flush()
        for spec in subs_spec:
            s = Subscription(
                user_id=user_id, name=spec['name'], price=spec['price'],
                currency_id=usd.id, cycle=spec.get('cycle', 3),
                frequency=spec.get('frequency', 1),
                next_payment=datetime.now().date(),
                category_id=cat.id,
                paypal_subscription_id=spec.get('paypal_id')
            )
            db.session.add(s)
            db.session.flush()
            db.session.add(SubscriptionUsage(
                subscription_id=s.id,
                last_used_at=(datetime.now() - timedelta(days=spec['last_used_days']))
                             if spec.get('last_used_days') is not None else None,
                usage_count_30d=spec.get('count_30d', 0)
            ))
        db.session.commit()
        return ai_service.build_context(user)


def test_build_context(app, auth_headers):
    headers, user_id = auth_headers
    context = _context(app, user_id, [
        {'name': 'X', 'price': 10.0, 'paypal_id': 'SIM-X',
         'last_used_days': 5, 'count_30d': 20}
    ])
    assert context['monthly_total'] == 10.0
    sub = context['subscriptions'][0]
    assert sub['paypal_managed'] is True
    assert sub['usage_count_30d'] == 20
    assert sub['monthly_cost'] == 10.0


def test_heuristic_flags_long_unused(app, auth_headers):
    headers, user_id = auth_headers
    context = _context(app, user_id, [
        {'name': 'Old', 'price': 15.0, 'paypal_id': 'SIM-OLD',
         'last_used_days': 90, 'count_30d': 0},
        {'name': 'Fresh', 'price': 5.0, 'last_used_days': 1, 'count_30d': 9}
    ])
    result = HeuristicAdvisor.generate(context)
    assert len(result['advice']) == 1
    advice = result['advice'][0]
    assert advice['subscription_id'] != 0
    assert 'Old' in advice['title']
    assert advice['recommended_action'] == 'cancel'
    assert advice['estimated_monthly_savings'] == 15.0
    assert advice['action_available'] is True  # PayPal-managed


def test_heuristic_action_available_false_for_card_subscriptions(app, auth_headers):
    headers, user_id = auth_headers
    context = _context(app, user_id, [
        {'name': 'CardOnly', 'price': 30.0, 'paypal_id': None,
         'last_used_days': 100, 'count_30d': 0}
    ])
    result = HeuristicAdvisor.generate(context)
    assert result['advice'][0]['action_available'] is False


def test_heuristic_duplicate_category(app, auth_headers):
    headers, user_id = auth_headers
    context = _context(app, user_id, [
        {'name': 'UsedService', 'price': 10.0, 'last_used_days': 1, 'count_30d': 20},
        {'name': 'DormantService', 'price': 14.0, 'last_used_days': 35, 'count_30d': 0}
    ])
    # Same category -> duplicate rule suggests cancelling the dormant sibling
    result = HeuristicAdvisor.generate(context)
    titles = [a['title'] for a in result['advice']]
    assert any('DormantService' in t for t in titles)


def test_heuristic_price_hike_underuse(app, auth_headers):
    headers, user_id = auth_headers
    context = _context(app, user_id, [
        {'name': 'Costly', 'price': 25.0, 'last_used_days': 33, 'count_30d': 1}
    ])
    result = HeuristicAdvisor.generate(context)
    assert len(result['advice']) == 1
    assert result['advice'][0]['estimated_monthly_savings'] == 25.0


def test_generate_advice_falls_back_to_heuristic(app, auth_headers):
    """Unknown provider name must not crash - falls back to rules engine."""
    headers, user_id = auth_headers
    with app.app_context():
        user = db.session.get(User, user_id)
        current_app = app
        current_app.config['AI_PROVIDER'] = 'openai'  # no key -> will fail HTTP
        result, engine, note = ai_service.generate_advice(user)
        assert engine == 'heuristic'
        assert note and note.startswith('llm_fallback')
        current_app.config['AI_PROVIDER'] = 'heuristic'


def test_persist_advice_replaces_previous(app, auth_headers):
    headers, user_id = auth_headers
    with app.app_context():
        user = db.session.get(User, user_id)
        result = {'summary': 's', 'advice': [{
            'subscription_id': 1, 'title': 'Cancel X',
            'recommended_action': 'cancel', 'rationale': 'r',
            'estimated_monthly_savings': 10.0, 'confidence': 0.9,
            'action_available': True
        }]}
        ai_service.persist_advice(user, result, 'heuristic')
        ai_service.persist_advice(user, result, 'heuristic')  # regenerate
        from app.models.ai_recommendation import AIRecommendation
        rows = db.session.query(AIRecommendation).filter_by(
            user_id=user_id).all()
        assert len(rows) == 1  # old un-dismissed set replaced, not appended
        assert rows[0].savings == '$10.00/month'
