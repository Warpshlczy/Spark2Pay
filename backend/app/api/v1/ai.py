"""
AI Advice API Endpoints
"""
from flask import Blueprint, jsonify, g

from app import db
from app.models.ai_recommendation import AIRecommendation
from app.models.subscription import Subscription
from app.services import ai_service
from app.utils.decorators import require_auth

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/recommendations', methods=['GET'])
@require_auth
def recommendations():
    """
    Generate (or regenerate) AI savings advice for the current user.

    Engine selection: AI_PROVIDER env (auto -> OpenAI if a key exists,
    otherwise the deterministic heuristic engine). Any LLM failure falls
    back to heuristics so the demo always works.

    Response:
    {
      "status": "success",
      "data": {
        "engine": "openai" | "heuristic",
        "note": null | "llm_fallback: ...",
        "summary": "...",
        "paypal_mode": "simulation" | "sandbox",
        "advice": [
          {
            "subscription_id": 3,
            "title": "Cancel Netflix - unused for 92 days",
            "recommended_action": "cancel",
            "rationale": "...",
            "estimated_monthly_savings": 15.49,
            "confidence": 0.9,
            "action_available": true,
            "subscription": { ...compact subscription dict... }
          }
        ]
      }
    }
    """
    result, engine, note = ai_service.generate_advice(g.user)
    ai_service.persist_advice(g.user, result, engine)

    # Attach compact subscription info so the UI renders cards in one shot
    sub_ids = {a['subscription_id'] for a in result.get('advice', [])}
    subs = {s.id: s for s in db.session.query(Subscription)
            .filter(Subscription.id.in_(sub_ids)).all()} if sub_ids else {}

    advice = []
    for item in result.get('advice', []):
        sub = subs.get(item['subscription_id'])
        enriched = dict(item)
        if sub:
            enriched['subscription'] = {
                'id': sub.id,
                'name': sub.name,
                'price': sub.price,
                'currency': sub.currency.code if sub.currency else 'USD',
                'currency_symbol': sub.currency.symbol if sub.currency else '$',
                'category': sub.category.name if sub.category else None,
                'next_payment': (sub.next_payment.isoformat()
                                 if sub.next_payment else None),
                'paypal_managed': bool(sub.paypal_subscription_id)
            }
        advice.append(enriched)

    from flask import current_app
    return jsonify({
        'status': 'success',
        'data': {
            'engine': engine,
            'note': note,
            'summary': result.get('summary'),
            'paypal_mode': current_app.config.get('PAYPAL_MODE'),
            'advice': advice
        }
    }), 200


@ai_bp.route('/recommendations/persisted', methods=['GET'])
@require_auth
def persisted_recommendations():
    """Previously generated recommendations (the ai_recommendations table)."""
    rows = db.session.query(AIRecommendation).filter_by(
        user_id=g.user_id
    ).order_by(AIRecommendation.created_at.desc()).limit(50).all()
    return jsonify({
        'status': 'success',
        'data': [r.to_dict() for r in rows],
        'total': len(rows)
    }), 200


@ai_bp.route('/recommendations/<int:rec_id>/dismiss', methods=['POST'])
@require_auth
def dismiss_recommendation(rec_id):
    row = db.session.query(AIRecommendation).filter_by(
        id=rec_id, user_id=g.user_id
    ).first()
    if not row:
        return jsonify({'status': 'error',
                        'message': 'Recommendation not found'}), 404
    row.dismissed = True
    db.session.commit()
    return jsonify({'status': 'success', 'data': row.to_dict()}), 200


@ai_bp.route('/status', methods=['GET'])
@require_auth
def ai_status():
    """AI engine + PayPal layer configuration status (no secrets)."""
    return jsonify({'status': 'success',
                    'data': ai_service.status_payload(g.user)}), 200
