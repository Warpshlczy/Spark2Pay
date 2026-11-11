#!/usr/bin/env python3
"""
Spark2Pay demo seed
Creates the tables and a demo account whose subscription portfolio is shaped
so the AI savings engine surfaces the three signature recommendations:
  1. long-term unused  (Netflix, Adobe - cancel via PayPal)
  2. duplicate category (The Athletic duplicating NYT - one PayPal-managed,
     one not, so judges see both the executable and the manual path)
  3. costly underuse    (FitGym Elite - cancel via PayPal)

Usage:  cd backend && python seed_demo.py
Login:  demo / Spark2Pay2026
"""
import sys
from datetime import datetime, timedelta

from app import create_app, db
from app.models import (
    User, Currency, Category, HouseholdMember, PaymentMethod,
    Subscription, SubscriptionUsage
)
from app.services.auth_service import AuthService


def days_ago(n):
    return datetime.now() - timedelta(days=n)


def seed():
    app = create_app('development')

    with app.app_context():
        # Spark2Pay models bind to app.models.Base (not Flask-SQLAlchemy's
        # db.Model), so schema creation must use that metadata.
        from app.models import Base
        print('Creating tables (if missing)...')
        Base.metadata.create_all(db.engine)

        existing = db.session.query(User).filter_by(username='demo').first()
        if existing:
            print('Demo user already exists - nothing to do. '
                  'Delete backend/spark2pay.db to reseed.')
            return

        print('Seeding demo data...')
        user = User(
            username='demo',
            email='demo@spark2pay.app',
            password=AuthService.hash_password('Spark2Pay2026'),
            firstname='Alex',
            budget=250.0
        )
        db.session.add(user)
        db.session.flush()

        # Currency (main first)
        usd = Currency(user_id=user.id, name='US Dollar', code='USD',
                       symbol='$', rate=1.0, last_updated=datetime.now())
        eur = Currency(user_id=user.id, name='Euro', code='EUR',
                       symbol='€', rate=0.92, last_updated=datetime.now())
        db.session.add_all([usd, eur])
        db.session.flush()
        user.main_currency = usd.id

        # Categories
        names = ['Streaming', 'Music', 'Software', 'News', 'Fitness', 'Cloud']
        categories = {name: Category(user_id=user.id, name=name, order=i)
                      for i, name in enumerate(names)}
        db.session.add_all(categories.values())

        # Payment methods
        pm_paypal = PaymentMethod(user_id=user.id, name='PayPal', icon='paypal', order=0)
        pm_visa = PaymentMethod(user_id=user.id, name='Visa •• 4242', icon='visa', order=1)
        db.session.add_all([pm_paypal, pm_visa])

        # Household member (payer)
        payer = HouseholdMember(user_id=user.id, name='Alex')
        db.session.add(payer)
        db.session.flush()

        def sub(name, price, cycle, freq, next_pay, category, pm, paypal_id=None,
                inactive=False, notes=None):
            s = Subscription(
                user_id=user.id, name=name, price=price, currency_id=usd.id,
                cycle=cycle, frequency=freq, next_payment=next_pay,
                auto_renew=True, category_id=category.id, payment_method_id=pm.id,
                payer_user_id=payer.id, paypal_subscription_id=paypal_id,
                inactive=inactive, notes=notes
            )
            db.session.add(s)
            return s

        today = datetime.now().date()
        def in_days(n):
            return today + timedelta(days=n)

        # --- portfolio (cycle: 3=months, 4=years) ----------------------- #
        netflix = sub(
            'Netflix Premium', 22.99, 3, 1, in_days(9),
            categories['Streaming'], pm_paypal,
            paypal_id='SIM-SUB-NETFLIX-001',
            notes='4K streaming plan, billed monthly through PayPal'
        )
        hulu = sub(
            'Hulu', 17.99, 3, 1, in_days(21),
            categories['Streaming'], pm_visa,
            notes='Paid directly by card - cancel manually on hulu.com'
        )
        adobe = sub(
            'Adobe Creative Cloud', 59.99, 3, 1, in_days(4),
            categories['Software'], pm_paypal,
            paypal_id='SIM-SUB-ADOBE-001',
            notes='All-apps plan billed through PayPal Subscriptions'
        )
        spotify = sub(
            'Spotify Duo', 16.99, 3, 1, in_days(14),
            categories['Music'], pm_paypal,
            paypal_id='SIM-SUB-SPOTIFY-001'
        )
        athletic = sub(
            'The Athletic', 12.00, 3, 1, in_days(18),
            categories['News'], pm_visa,
            notes='Sports journalism, paid directly by card'
        )
        fitgym = sub(
            'FitGym Elite', 45.00, 3, 1, in_days(7),
            categories['Fitness'], pm_paypal,
            paypal_id='SIM-SUB-FITGYM-001'
        )
        icloud = sub(
            'iCloud+ 2TB', 9.99, 3, 1, in_days(26),
            categories['Cloud'], pm_visa
        )
        nyt = sub(
            'NYT Digital', 17.00, 3, 1, in_days(11),
            categories['News'], pm_paypal,
            paypal_id='SIM-SUB-NYT-001'
        )
        onedrive = sub(
            'OneDrive 1TB (annual)', 69.99, 4, 1, in_days(120),
            categories['Cloud'], pm_visa
        )
        db.session.flush()

        # --- usage telemetry driving the heuristic rules ---------------- #
        def usage(s, last_used_days, count_30d, note=None):
            db.session.add(SubscriptionUsage(
                subscription_id=s.id,
                last_used_at=days_ago(last_used_days) if last_used_days is not None else None,
                usage_count_30d=count_30d,
                notes=note
            ))

        usage(netflix, 92, 0, 'Last opened on the living-room TV, 3 months ago')
        usage(hulu, 2, 12, 'Daily evening watcher')
        usage(adobe, 75, 0, 'Figma replaced the design workflow')
        usage(spotify, 0, 25, 'Commute playlist')
        usage(athletic, 29, 1, 'Opened once after the draft')
        usage(fitgym, 40, 1, 'Visited once this month')
        usage(icloud, 0, 30, 'Photo sync runs daily')
        usage(nyt, 1, 8, 'Morning briefing reader')
        usage(onedrive, 5, 20, 'File backup')

        db.session.commit()

        total = 0.0
        for s in db.session.query(Subscription).filter_by(user_id=user.id,
                                                          inactive=False).all():
            from app.services.billing_cycle import BillingCycleCalculator
            total += BillingCycleCalculator.calculate_monthly_cost(
                s.price, s.cycle, s.frequency)

        print(f"""
    ✔ Seed complete

    Login (frontend):  demo / Spark2Pay2026
    Monthly total:     ${total:.2f}
    PayPal-managed:    Netflix, Adobe, Spotify, FitGym, NYT
    Card-managed:      Hulu, The Athletic, iCloud, OneDrive
    Expected advice:   cancel Netflix ($22.99) + Adobe ($59.99)
                       + FitGym ($45.00) via PayPal;
                       The Athletic ($12.00) flagged manual-only.
""")


if __name__ == '__main__':
    seed()
    sys.exit(0)
