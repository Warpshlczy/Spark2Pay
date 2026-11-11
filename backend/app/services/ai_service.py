"""
AI Savings Engine for Spark2Pay
===============================

The "perception -> analysis" brain whose advice the PayPal execution layer
carries out. Two interchangeable advisors behind one interface:

- HeuristicAdvisor: deterministic rules over usage + billing data. Zero
  network, zero keys - always available, and the fallback whenever an LLM
  call fails.

- LLMAdvisor: OpenAI-compatible chat completions with function calling.
  One client covers OpenAI, Gemini (OpenAI-compatible endpoint) and Ollama
  (OpenAI-compatible endpoint). The LLM may call `manage_with_paypal` to
  PROPOSE an execution; proposals are rendered as "Manage with PayPal"
  buttons in the UI and never auto-execute (human-in-the-loop gate).

Output contract (both advisors):
    {
      "summary": str,
      "advice": [
        {
          "subscription_id": int,
          "title": str,
          "recommended_action": "cancel" | "optimize",
          "rationale": str,
          "estimated_monthly_savings": float,
          "confidence": float,
          "action_available": bool     # can PayPal execute it end-to-end?
        }
      ]
    }
"""
import json
from datetime import datetime, timedelta

import requests
from flask import current_app

from app import db
from app.models.subscription import Subscription
from app.models.subscription_usage import SubscriptionUsage
from app.models.ai_recommendation import AIRecommendation
from app.services.billing_cycle import BillingCycleCalculator


class AIServiceError(Exception):
    """Raised when the LLM engine fails; callers fall back to heuristics."""


# --------------------------------------------------------------------- #
# Context builder - the facts both advisors reason over
# --------------------------------------------------------------------- #

def build_context(user):
    """Assemble everything the advisor needs about a user's subscriptions."""
    subs = db.session.query(Subscription).filter_by(
        user_id=user.id, inactive=False
    ).all()
    usage_by_sub = {
        u.subscription_id: u
        for u in db.session.query(SubscriptionUsage).join(
            Subscription, SubscriptionUsage.subscription_id == Subscription.id
        ).filter(Subscription.user_id == user.id).all()
    }

    currency_symbol = '$'
    if subs and subs[0].currency:
        currency_symbol = subs[0].currency.symbol

    items, monthly_total = [], 0.0
    for s in subs:
        monthly = round(BillingCycleCalculator.calculate_monthly_cost(
            s.price, s.cycle, s.frequency), 2)
        monthly_total += monthly
        usage = usage_by_sub.get(s.id)
        items.append({
            'id': s.id,
            'name': s.name,
            'price': round(s.price, 2),
            'currency': s.currency.code if s.currency else 'USD',
            'billing': BillingCycleCalculator.get_cycle_name(s.cycle, s.frequency),
            'monthly_cost': monthly,
            'next_payment': s.next_payment.isoformat() if s.next_payment else None,
            'category': s.category.name if s.category else None,
            'last_used_at': (usage.last_used_at.isoformat()
                             if usage and usage.last_used_at else None),
            'usage_count_30d': usage.usage_count_30d if usage else 0,
            'created_at': s.created_at.isoformat() if s.created_at else None,
            'paypal_managed': bool(s.paypal_subscription_id)
        })

    return {
        'currency_symbol': currency_symbol,
        'monthly_total': round(monthly_total, 2),
        'monthly_budget': user.budget,
        'subscriptions': items
    }


# --------------------------------------------------------------------- #
# Advisor 1: deterministic heuristics (always works, no keys)
# --------------------------------------------------------------------- #

UNUSED_DAYS = 60
UNDERUSE_MIN_MONTHLY = 10.0
UNDERUSE_MAX_30D_USES = 1


class HeuristicAdvisor:

    @staticmethod
    def generate(context, now=None):
        now = now or datetime.now()
        advice = []
        by_id = {s['id']: s for s in context['subscriptions']}

        claimed = set()

        def add(sub, title, action, rationale, savings, confidence):
            if sub['id'] in claimed:
                return
            claimed.add(sub['id'])
            advice.append({
                'subscription_id': sub['id'],
                'title': title,
                'recommended_action': action,
                'rationale': rationale,
                'estimated_monthly_savings': round(savings, 2),
                'confidence': confidence,
                # PayPal can execute end-to-end only for PayPal-managed subs
                'action_available': bool(sub['paypal_managed'])
            })

        # Rule 1 - long-term unused -> cancel
        for s in context['subscriptions']:
            last_used = s['last_used_at']
            created = s['created_at']
            stale_since = None
            if last_used:
                used_at = datetime.fromisoformat(last_used)
                if (now - used_at).days >= UNUSED_DAYS:
                    stale_since = used_at
            elif created:
                created_at = datetime.fromisoformat(created)
                if (now - created_at).days >= UNUSED_DAYS and not s['usage_count_30d']:
                    stale_since = created_at
            if stale_since:
                days = (now - stale_since).days
                add(
                    s,
                    f"Cancel {s['name']} - unused for {days} days",
                    'cancel',
                    f"No recorded activity for {days} days "
                    f"({s['usage_count_30d']} opens in the last 30 days). "
                    f"Cancelling frees {context['currency_symbol']}"
                    f"{s['monthly_cost']:.2f}/month.",
                    s['monthly_cost'],
                    0.9
                )

        # Rule 2 - duplicate category, one of them unused -> cancel the
        # most expensive underused sibling
        by_category = {}
        for s in context['subscriptions']:
            if s['category']:
                by_category.setdefault(s['category'], []).append(s)
        for category, group in by_category.items():
            if len(group) < 2:
                continue
            candidates = [s for s in group if s['usage_count_30d'] <= 1
                          and s['id'] not in claimed]
            kept = [s for s in group if s['usage_count_30d'] > 1]
            if candidates and kept:
                target = max(candidates, key=lambda x: x['monthly_cost'])
                keep_names = ', '.join(k['name'] for k in kept)
                add(
                    target,
                    f"{target['name']} duplicates your {category} coverage",
                    'cancel',
                    f"You keep {keep_names} in {category} and used "
                    f"{target['name']} at most once in 30 days. Consolidating "
                    f"saves {context['currency_symbol']}"
                    f"{target['monthly_cost']:.2f}/month.",
                    target['monthly_cost'],
                    0.75
                )

        # Rule 3 - costly and barely used -> cancel
        for s in context['subscriptions']:
            if (s['monthly_cost'] >= UNDERUSE_MIN_MONTHLY
                    and s['usage_count_30d'] <= UNDERUSE_MAX_30D_USES):
                add(
                    s,
                    f"{s['name']} costs "
                    f"{context['currency_symbol']}{s['monthly_cost']:.2f}/month "
                    f"but is barely used",
                    'cancel',
                    f"Only {s['usage_count_30d']} opens in the last 30 days at "
                    f"{context['currency_symbol']}{s['monthly_cost']:.2f}/month "
                    f"({context['currency_symbol']}"
                    f"{s['monthly_cost'] * 12:.2f}/year).",
                    s['monthly_cost'],
                    0.7
                )

        advice.sort(key=lambda a: a['estimated_monthly_savings'], reverse=True)
        total = round(sum(a['estimated_monthly_savings'] for a in advice), 2)
        summary = (f"{len(advice)} opportunity(ies) found - cancelling all "
                   f"saves about {context['currency_symbol']}{total:.2f}/month"
                   ) if advice else 'No savings opportunities detected.'
        return {'summary': summary, 'advice': advice}


# --------------------------------------------------------------------- #
# Advisor 2: LLM with PayPal function calling (OpenAI-compatible)
# --------------------------------------------------------------------- #

MANAGE_WITH_PAYPAL_TOOL = {
    'type': 'function',
    'function': {
        'name': 'manage_with_paypal',
        'description': (
            'Propose managing a subscription through the PayPal execution '
            'layer (cancel, suspend, or activate). The proposal is shown to '
            'the user as a "Manage with PayPal" button and only executes '
            'after the user approves it. Never call it for subscriptions the '
            'user did not ask about or that are not paypal_managed.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'subscription_id': {
                    'type': 'integer',
                    'description': 'Subscription id from the provided context'
                },
                'action': {
                    'type': 'string',
                    'enum': ['cancel', 'suspend', 'activate']
                },
                'reason': {
                    'type': 'string',
                    'description': 'Short human-readable reason'
                }
            },
            'required': ['subscription_id', 'action', 'reason']
        }
    }
}

SYSTEM_PROMPT = """You are Spark2Pay's savings agent for subscription expenses.

Rules:
- Reason only over the JSON context provided. Never invent subscriptions,
  prices, usage numbers, or savings.
- When you judge a subscription should be cancelled, suspended, or
  reactivated, call the manage_with_paypal tool. The call is a PROPOSAL:
  execution only happens after the user clicks "Manage with PayPal" and
  approves it, so never claim an action was executed.
- Prefer fewer, well-justified proposals over many weak ones.
- End with a single JSON object (no markdown fence) shaped exactly:
  {"summary": "<one sentence>", "recommendations": [
    {"subscription_id": <int>, "title": "<short title>",
     "recommended_action": "cancel"|"optimize", "rationale": "<why>",
     "estimated_monthly_savings": <number>, "confidence": <0..1>}
  ]}
- recommended_action must be "cancel" or "optimize". estimated_monthly_savings
  must be a number in the currency of the context (monthly equivalent).
"""


class LLMAdvisor:

    TIMEOUT = 30
    MAX_ROUNDS = 3

    def __init__(self, user):
        cfg = current_app.config
        self.provider = cfg.get('AI_PROVIDER', 'auto')
        if self.provider == 'auto':
            self.provider = 'openai' if cfg.get('OPENAI_API_KEY') else 'heuristic'
        self.model = cfg.get('AI_MODEL', 'gpt-4o-mini')
        self.base_url, self.api_key = self._resolve_endpoint(cfg, self.provider)

    @staticmethod
    def _resolve_endpoint(cfg, provider):
        if provider == 'openai':
            return cfg.get('OPENAI_BASE_URL'), cfg.get('OPENAI_API_KEY')
        if provider == 'gemini':
            return cfg.get('GEMINI_BASE_URL'), cfg.get('GOOGLE_GEMINI_API_KEY')
        if provider == 'ollama':
            return (cfg.get('OLLAMA_HOST', 'http://localhost:11434').rstrip('/')
                    + '/v1', None)
        raise AIServiceError(f'Unknown AI provider: {provider}')

    # -- low-level chat call ------------------------------------------- #

    def _chat(self, messages, tools=None):
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        body = {'model': self.model, 'messages': messages}
        if tools:
            body['tools'] = tools
            body['tool_choice'] = 'auto'

        try:
            resp = requests.post(
                f'{self.base_url}/chat/completions',
                headers=headers, json=body, timeout=self.TIMEOUT
            )
        except requests.RequestException as exc:
            raise AIServiceError(f'LLM request failed: {exc}') from exc

        if resp.status_code != 200:
            raise AIServiceError(
                f'LLM returned {resp.status_code}',
                details=resp.text[:300]
            )
        return resp.json()['choices'][0]['message']

    # -- agent loop ----------------------------------------------------- #

    def generate(self, context):
        if self.provider != 'ollama' and not self.api_key:
            raise AIServiceError(
                f'No API key configured for provider {self.provider}'
            )
        if not context['subscriptions']:
            return {'summary': 'No active subscriptions to analyze.',
                    'advice': []}

        messages = [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': json.dumps(context, default=str)}
        ]

        proposals = []
        for _ in range(self.MAX_ROUNDS):
            message = self._chat(messages, tools=[MANAGE_WITH_PAYPAL_TOOL])
            messages.append(message)

            tool_calls = message.get('tool_calls') or []
            if not tool_calls:
                break

            for call in tool_calls:
                proposal = self._validate_tool_call(call, context)
                proposals.append(proposal)  # rejected ones stay visible too
                messages.append({
                    'role': 'tool',
                    'tool_call_id': call.get('id', 'tool'),
                    'content': json.dumps({
                        'status': 'PROPOSED' if proposal['valid'] else 'REJECTED',
                        'detail': proposal['note'],
                        'note': 'This is a proposal only. Execution requires '
                                'explicit user approval in the Spark2Pay UI.'
                    })
                })
            # After tool round(s), nudge for the final JSON answer
            messages.append({
                'role': 'user',
                'content': ('All proposals are recorded and awaiting user '
                            'approval. Now return the final JSON object with '
                            'your summary and recommendations.')
            })
        else:
            raise AIServiceError('LLM exceeded the tool-call round limit')

        recommendations = self._parse_final_json(message)
        advice = self._merge(recommendations, context)
        return {
            'summary': recommendations.get('summary')
                       or f"{len(advice)} recommendation(s) generated.",
            'advice': advice,
            'tool_proposals': proposals
        }

    # -- helpers -------------------------------------------------------- #

    def _validate_tool_call(self, call, context):
        try:
            args = call.get('function', {}).get('arguments', '{}')
            args = json.loads(args) if isinstance(args, str) else args
        except (ValueError, TypeError):
            args = {}
        sub_id = args.get('subscription_id')
        action = args.get('action')
        sub = next((s for s in context['subscriptions'] if s['id'] == sub_id),
                   None)
        valid = bool(sub) and action in ('cancel', 'suspend', 'activate')
        note = 'ok' if valid else 'unknown subscription_id or invalid action'
        return {
            'subscription_id': sub_id,
            'action': action,
            'reason': args.get('reason'),
            'valid': valid,
            'note': note
        }

    def _parse_final_json(self, message):
        content = message.get('content') or ''
        content = content.strip()
        if content.startswith('```'):
            content = content.strip('`')
            if content.startswith('json'):
                content = content[4:]
        try:
            data = json.loads(content)
        except ValueError:
            raise AIServiceError('LLM final answer was not valid JSON')
        if not isinstance(data.get('recommendations', []), list):
            raise AIServiceError('LLM JSON missing recommendations list')
        return data

    def _merge(self, recommendations, context):
        by_id = {s['id']: s for s in context['subscriptions']}
        advice = []
        for rec in recommendations.get('recommendations', []):
            sub = by_id.get(rec.get('subscription_id'))
            if not sub:
                continue  # never surface advice about unknown subscriptions
            try:
                savings = float(rec.get('estimated_monthly_savings')
                                or sub['monthly_cost'])
            except (TypeError, ValueError):
                savings = sub['monthly_cost']
            advice.append({
                'subscription_id': sub['id'],
                'title': rec.get('title') or f"Review {sub['name']}",
                'recommended_action': rec.get('recommended_action', 'cancel'),
                'rationale': rec.get('rationale', ''),
                'estimated_monthly_savings': round(max(savings, 0), 2),
                'confidence': min(max(float(rec.get('confidence', 0.6)), 0), 1),
                'action_available': bool(sub['paypal_managed'])
            })
        advice.sort(key=lambda a: a['estimated_monthly_savings'], reverse=True)
        return advice


# --------------------------------------------------------------------- #
# Facade + persistence
# --------------------------------------------------------------------- #

def resolve_provider():
    """Effective provider name after 'auto' resolution."""
    cfg = current_app.config
    provider = cfg.get('AI_PROVIDER', 'auto')
    if provider == 'auto':
        return 'openai' if cfg.get('OPENAI_API_KEY') else 'heuristic'
    return provider


def generate_advice(user):
    """
    Generate advice with the best available engine, falling back to the
    heuristic advisor whenever the LLM path fails. Returns
    (result, engine, note).
    """
    context = build_context(user)
    provider = resolve_provider()

    if provider in ('openai', 'gemini', 'ollama'):
        try:
            result = LLMAdvisor(user).generate(context)
            return result, provider, None
        except AIServiceError as exc:
            result = HeuristicAdvisor.generate(context)
            result['advice'] = result['advice']
            return result, 'heuristic', f'llm_fallback: {exc}'

    return HeuristicAdvisor.generate(context), 'heuristic', None


def persist_advice(user, result, engine):
    """Replace the user's un-dismissed recommendations with a fresh set."""
    db.session.query(AIRecommendation).filter_by(
        user_id=user.id, dismissed=False
    ).delete()
    rows = []
    for item in result.get('advice', []):
        row = AIRecommendation(
            user_id=user.id,
            title=item['title'][:255],
            description=item['rationale'],
            savings=f"${item['estimated_monthly_savings']:.2f}/month",
            recommendation_type=item['recommended_action'],
            related_subscription_ids=json.dumps([item['subscription_id']])
        )
        db.session.add(row)
        rows.append(row)
    db.session.commit()
    return rows


def status_payload(user):
    """Engine + PayPal layer status for the Settings page."""
    provider = resolve_provider()
    cfg = current_app.config
    return {
        'ai': {
            'configured_provider': cfg.get('AI_PROVIDER', 'auto'),
            'effective_provider': provider,
            'model': cfg.get('AI_MODEL') if provider != 'heuristic' else 'rules-engine-v1',
            'openai': bool(cfg.get('OPENAI_API_KEY')),
            'gemini': bool(cfg.get('GOOGLE_GEMINI_API_KEY')),
            'ollama_host': cfg.get('OLLAMA_HOST'),
        },
        'paypal': {
            'mode': cfg.get('PAYPAL_MODE'),
            'sandbox_configured': bool(cfg.get('PAYPAL_CLIENT_ID')
                                       and cfg.get('PAYPAL_CLIENT_SECRET'))
        }
    }
