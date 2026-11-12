#!/usr/bin/env python3
"""
Spark2Pay demo seed
Creates the tables and a demo account that looks like it has been lived in
for months: an active portfolio shaped so the AI savings engine surfaces the
three signature recommendations (long-term unused, duplicate category,
costly underuse), plus believable history - past cancellations, audited
execution records (completed / rejected / failed), and dismissed
AI recommendations.

Usage:  cd backend && python seed_demo.py        (delete spark2pay.db to reseed)
Login:  demo / Spark2Pay2026
"""
import sys
import json
from datetime import datetime, timedelta

from app import create_app, db
from app.models import (
    User, Currency, Category, HouseholdMember, PaymentMethod,
    Subscription, SubscriptionUsage, PayPalAction, AIRecommendation
)
from app.services.auth_service import AuthService


def days_ago(n):
    return datetime.now() - timedelta(days=n)


def seed():
    app = create_app('development')

    with app.app_context():
        # Models bind to app.models.Base (not Flask-SQLAlchemy's db.Model),
        # so schema creation must use that metadata.
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
            budget=250.0,
            created_at=days_ago(240)
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
        pm_amex = PaymentMethod(user_id=user.id, name='Amex •• 1005', icon='amex', order=2)
        pm_mc = PaymentMethod(user_id=user.id, name='Mastercard •• 8841', icon='mastercard', order=3)
        db.session.add_all([pm_paypal, pm_visa, pm_amex, pm_mc])

        # Household members (payers)
        payer = HouseholdMember(user_id=user.id, name='Alex',
                                email='alex@spark2pay.app')
        db.session.add(payer)
        db.session.flush()
        partner = HouseholdMember(user_id=user.id, name='Sam (partner)',
                                  email='sam@spark2pay.app')
        db.session.add(partner)
        db.session.flush()

        def sub(name, price, cycle, freq, next_pay, category, pm, payer_id=None,
                paypal_id=None, inactive=False, notes=None, created_days=180):
            s = Subscription(
                user_id=user.id, name=name, price=price, currency_id=usd.id,
                cycle=cycle, frequency=freq, next_payment=next_pay,
                auto_renew=not inactive, category_id=category.id,
                payment_method_id=pm.id, payer_user_id=payer_id or payer.id,
                paypal_subscription_id=paypal_id, inactive=inactive,
                notes=notes, created_at=days_ago(created_days)
            )
            db.session.add(s)
            return s

        today = datetime.now().date()
        def in_days(n):
            return today + timedelta(days=n)

        # --- active portfolio (cycle: 3=months, 4=years) ---------------- #
        netflix = sub(
            'Netflix Premium', 22.99, 3, 1, in_days(9),
            categories['Streaming'], pm_paypal,
            paypal_id='SIM-SUB-NETFLIX-001', created_days=210,
            notes='4K streaming plan, billed monthly through PayPal'
        )
        hulu = sub(
            'Hulu', 17.99, 3, 1, in_days(21),
            categories['Streaming'], pm_visa, created_days=200,
            notes='Paid directly by card - cancel manually on hulu.com'
        )
        adobe = sub(
            'Adobe Creative Cloud', 59.99, 3, 1, in_days(4),
            categories['Software'], pm_paypal,
            paypal_id='SIM-SUB-ADOBE-001', created_days=190,
            notes='All-apps plan billed through PayPal Subscriptions'
        )
        spotify = sub(
            'Spotify Duo', 16.99, 3, 1, in_days(14),
            categories['Music'], pm_paypal,
            paypal_id='SIM-SUB-SPOTIFY-001', created_days=230,
            notes='Duo plan shared with Sam'
        )
        athletic = sub(
            'The Athletic', 12.00, 3, 1, in_days(18),
            categories['News'], pm_visa, created_days=120,
            notes='Sports journalism, paid directly by card'
        )
        fitgym = sub(
            'FitGym Elite', 45.00, 3, 1, in_days(7),
            categories['Fitness'], pm_paypal,
            paypal_id='SIM-SUB-FITGYM-001', created_days=150
        )
        icloud = sub(
            'iCloud+ 2TB', 9.99, 3, 1, in_days(26),
            categories['Cloud'], pm_visa, created_days=300,
            payer_id=partner.id,
            notes='Family photo backup, paid by Sam'
        )
        nyt = sub(
            'NYT Digital', 17.00, 3, 1, in_days(11),
            categories['News'], pm_mc, paypal_id='SIM-SUB-NYT-001',
            created_days=260, payer_id=partner.id,
            notes='Morning briefing, billed on Mastercard'
        )
        onedrive = sub(
            'OneDrive 1TB (annual)', 69.99, 4, 1, in_days(120),
            categories['Cloud'], pm_amex, created_days=320,
            notes='Switched to annual billing last spring'
        )
        db.session.flush()

        # --- cancelled history (inactive - excluded from advice) -------- #
        masterclass = sub(
            'MasterClass', 15.00, 3, 1, in_days(-45),
            categories['Streaming'], pm_paypal,
            paypal_id='SIM-SUB-MASTERCLASS-001', inactive=True,
            created_days=260, notes='Cancelled - finished the cooking course'
        )
        barkbox = sub(
            'BarkBox', 24.00, 3, 1, in_days(-70),
            categories['Streaming'], pm_visa, inactive=True,
            created_days=280, notes='Cancelled on the merchant site'
        )
        db.session.flush()

        masterclass.inactive = True
        masterclass.cancellation_date = today - timedelta(days=45)
        barkbox.inactive = True
        barkbox.cancellation_date = today - timedelta(days=70)
        db.session.flush()

        # --- usage telemetry driving the heuristic rules ---------------- #
        def usage(s, last_used_days, count_30d, note=None):
            db.session.add(SubscriptionUsage(
                subscription_id=s.id,
                last_used_at=days_ago(last_used_days) if last_used_days is not None else None,
                usage_count_30d=count_30d,
                notes=note,
                created_at=days_ago(60)
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
        usage(masterclass, 60, 0, 'Finished the last course before cancelling')
        usage(barkbox, 70, 0, 'Dog preferred the cardboard box')

        # --- audited execution history ---------------------------------- #
        def action(sub_row, action_type, status, created_days, reason=None,
                   savings=None, amount=None, currency=None, order_id=None,
                   capture_id=None, paypal_sub_id=None, error=None,
                   origin='ai_recommendation'):
            a = PayPalAction(
                user_id=user.id,
                subscription_id=sub_row.id if sub_row else None,
                action_type=action_type, status=status, reason=reason,
                amount=amount, currency=currency,
                estimated_monthly_savings=savings,
                paypal_order_id=order_id, paypal_capture_id=capture_id,
                paypal_subscription_id=paypal_sub_id
                or (sub_row.paypal_subscription_id if sub_row else None),
                paypal_mode='simulation',
                error=error,
                created_at=days_ago(created_days),
                executed_at=days_ago(created_days) if status in (
                    PayPalAction.STATUS_COMPLETED, PayPalAction.STATUS_FAILED,
                    PayPalAction.STATUS_REJECTED) else None
            )
            a.set_payload({
                'subscription_name': sub_row.name if sub_row else None,
                'monthly_cost': savings,
                'origin': origin
            })
            db.session.add(a)
            return a

        action(masterclass, 'cancel', PayPalAction.STATUS_COMPLETED, 45,
               reason='Finished the courses we cared about',
               savings=15.00)
        action(onedrive, 'pay', PayPalAction.STATUS_COMPLETED, 40,
               reason='Annual plan payment',
               amount=69.99, currency='USD',
               order_id='SIM-ORD-ANNUAL-8F21', capture_id='SIM-CAP-ANNUAL-8F21')
        action(barkbox, 'cancel', PayPalAction.STATUS_COMPLETED, 70,
               reason='Too many boxes', savings=24.00, origin='manual')
        action(nyt, 'cancel', PayPalAction.STATUS_REJECTED, 25,
               reason='Consider cancelling - price went up',
               savings=17.00)
        action(fitgym, 'cancel', PayPalAction.STATUS_FAILED, 20,
               reason='Unused for over a month', savings=45.00,
               error='PayPal API error on POST '
                     '/v1/billing/subscriptions/SIM-SUB-FITGYM-001/cancel: '
                     'upstream timeout (retriable)')

        # --- dismissed AI recommendations (older advice the user passed on)
        for title, desc, savings, rtype, sub_ids, d in [
            ('Bundle NYT Digital with The Athletic',
             'Both are news subscriptions - a bundle could cover both for less.',
             8.00, 'bundle', [nyt.id, athletic.id], 30),
            ('Downgrade Adobe CC to the Photography plan',
             'You have not opened Illustrator or Premiere in 90 days.',
             30.00, 'optimize', [adobe.id], 21),
            ('Cancel The Athletic - low engagement',
             'One open in the last 30 days at $12.00/month.',
             12.00, 'cancel', [athletic.id], 14)
        ]:
            db.session.add(AIRecommendation(
                user_id=user.id, title=title[:255], description=desc,
                savings=f'${savings:.2f}/month', recommendation_type=rtype,
                related_subscription_ids=json.dumps(sub_ids),
                dismissed=True, created_at=days_ago(d)
            ))

        db.session.commit()

        total = 0.0
        for s in db.session.query(Subscription).filter_by(user_id=user.id,
                                                          inactive=False).all():
            from app.services.billing_cycle import BillingCycleCalculator
            total += BillingCycleCalculator.calculate_monthly_cost(
                s.price, s.cycle, s.frequency)

        actions = db.session.query(PayPalAction).count()
        print(f"""
    ✔ Seed complete

    Login (frontend):   demo / Spark2Pay2026
    Monthly total:      ${total:.2f} across 9 active subscriptions
    Cancelled history:  MasterClass (45d ago), BarkBox (70d ago)
    Audit trail:        {actions} actions (2 completed cancels, 1 payment,
                        1 rejected, 1 failed)
    PayPal-managed:     Netflix, Adobe, Spotify, FitGym, NYT
    Card-managed:       Hulu, The Athletic, iCloud, OneDrive
    Expected advice:    cancel Netflix ($22.99) + Adobe ($59.99)
                        + FitGym ($45.00) via PayPal;
                        The Athletic ($12.00) flagged manual-only.
""")


if __name__ == '__main__':
    seed()
    sys.exit(0)
