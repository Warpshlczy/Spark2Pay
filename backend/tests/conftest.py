"""
Shared pytest fixtures for Spark2Pay backend tests
"""
import pytest

from app import create_app, db
from app.models import (
    Base, User, Currency, Category, PaymentMethod, Subscription,
    SubscriptionUsage
)
from app.services.auth_service import AuthService


@pytest.fixture()
def app():
    """Fresh app on an in-memory database (simulation PayPal mode)."""
    app = create_app('testing')
    app.config.update(
        PAYPAL_MODE='simulation',
        AI_PROVIDER='heuristic',
        TESTING=True
    )

    with app.app_context():
        Base.metadata.create_all(db.engine)
        yield app
        db.session.remove()
        Base.metadata.drop_all(db.engine)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_headers(app):
    """Register + login a test user; return bearer headers and the user."""
    with app.app_context():
        user = User(
            username='tester',
            email='tester@spark2pay.app',
            password=AuthService.hash_password('TestPass123'),
            firstname='Test',
            budget=200.0
        )
        db.session.add(user)
        db.session.flush()
        usd = Currency(user_id=user.id, name='US Dollar', code='USD',
                       symbol='$', rate=1.0)
        db.session.add(usd)
        db.session.flush()
        user.main_currency = usd.id
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    resp = client.post('/api/v1/auth/login',
                       json={'username': 'tester', 'password': 'TestPass123'})
    token = resp.get_json()['token']

    return {'Authorization': f'Bearer {token}'}, user_id


@pytest.fixture()
def seeded_user(app, auth_headers):
    """
    A user with a realistic subscription portfolio for AI/advice testing.

    Returns (headers, data) where data holds ids of created rows.
    """
    headers, user_id = auth_headers
    with app.app_context():
        user = db.session.get(User, user_id)
        usd = user.currencies[0]
        streaming = Category(user_id=user_id, name='Streaming', order=0)
        software = Category(user_id=user_id, name='Software', order=1)
        db.session.add_all([streaming, software])
        pm = PaymentMethod(user_id=user_id, name='PayPal', icon='paypal', order=0)
        db.session.add(pm)
        db.session.flush()

        def make(name, price, category, paypal_id=None, last_used_days=None,
                 count_30d=0, cycle=3, freq=1):
            from datetime import datetime, timedelta
            s = Subscription(
                user_id=user_id, name=name, price=price, currency_id=usd.id,
                cycle=cycle, frequency=freq,
                next_payment=(datetime.now() + timedelta(days=10)).date(),
                category_id=category.id, payment_method_id=pm.id,
                paypal_subscription_id=paypal_id
            )
            db.session.add(s)
            db.session.flush()
            db.session.add(SubscriptionUsage(
                subscription_id=s.id,
                last_used_at=(datetime.now() - timedelta(days=last_used_days))
                             if last_used_days is not None else None,
                usage_count_30d=count_30d
            ))
            return s

        netflix = make('Netflix', 22.99, streaming, 'SIM-SUB-NETFLIX',
                       last_used_days=92, count_30d=0)
        hulu = make('Hulu', 17.99, streaming, None,
                    last_used_days=2, count_30d=12)
        adobe = make('Adobe CC', 59.99, software, 'SIM-SUB-ADOBE',
                     last_used_days=75, count_30d=0)
        db.session.commit()
        data = {
            'user_id': user_id,
            'netflix_id': netflix.id,
            'hulu_id': hulu.id,
            'adobe_id': adobe.id
        }

    return headers, data
