"""
Currency Converter Service
Handles currency exchange rates and conversions
"""
import requests
from datetime import datetime
from app import db
from app.models.currency import Currency


class CurrencyConverter:
    """Currency conversion and exchange rate management"""

    FIXER_API_URL = 'https://api.fixer.io/latest'

    @staticmethod
    def update_exchange_rates(api_key: str) -> bool:
        """
        Fetch and update exchange rates from Fixer.io

        Args:
            api_key: Fixer.io API key

        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.get(
                CurrencyConverter.FIXER_API_URL,
                params={'access_key': api_key},
                timeout=10
            )

            data = response.json()

            if not data.get('success'):
                print(f"Fixer API error: {data.get('error', {}).get('info', 'Unknown error')}")
                return False

            # Update rates in database
            base = data.get('base', 'EUR')
            rates = data.get('rates', {})

            # If base is not USD, convert all rates to USD base
            if base != 'USD' and 'USD' in rates:
                usd_rate = rates['USD']
                for code in rates:
                    rates[code] = rates[code] / usd_rate

            # Update all currencies with matching codes
            for code, rate in rates.items():
                currencies = db.session.query(Currency).filter_by(code=code).all()
                for currency in currencies:
                    currency.rate = rate
                    currency.last_updated = datetime.now()

            db.session.commit()
            print(f"Updated {len(rates)} exchange rates")
            return True

        except requests.RequestException as e:
            print(f"Error fetching exchange rates: {e}")
            return False
        except Exception as e:
            print(f"Error updating exchange rates: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def convert(amount: float, from_currency_id: int, to_currency_id: int) -> float:
        """
        Convert amount from one currency to another

        Args:
            amount: Amount to convert
            from_currency_id: Source currency ID
            to_currency_id: Target currency ID

        Returns:
            Converted amount

        Raises:
            ValueError: If currency not found
        """
        from_currency = db.session.get(Currency, from_currency_id)
        to_currency = db.session.get(Currency, to_currency_id)

        if not from_currency:
            raise ValueError(f"Source currency not found: {from_currency_id}")

        if not to_currency:
            raise ValueError(f"Target currency not found: {to_currency_id}")

        # Convert to USD first, then to target currency
        amount_in_usd = amount / from_currency.rate
        return amount_in_usd * to_currency.rate

    @staticmethod
    def get_supported_currencies() -> dict:
        """
        Get list of commonly supported currencies

        Returns:
            Dictionary of currency code -> name
        """
        return {
            'USD': 'US Dollar',
            'EUR': 'Euro',
            'GBP': 'British Pound',
            'JPY': 'Japanese Yen',
            'AUD': 'Australian Dollar',
            'CAD': 'Canadian Dollar',
            'CHF': 'Swiss Franc',
            'CNY': 'Chinese Yuan',
            'SEK': 'Swedish Krona',
            'NZD': 'New Zealand Dollar',
            'MXN': 'Mexican Peso',
            'SGD': 'Singapore Dollar',
            'HKD': 'Hong Kong Dollar',
            'NOK': 'Norwegian Krone',
            'KRW': 'South Korean Won',
            'TRY': 'Turkish Lira',
            'RUB': 'Russian Ruble',
            'INR': 'Indian Rupee',
            'BRL': 'Brazilian Real',
            'ZAR': 'South African Rand'
        }

    @staticmethod
    def get_currency_symbol(code: str) -> str:
        """
        Get currency symbol by code

        Args:
            code: Currency code

        Returns:
            Currency symbol
        """
        symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'JPY': '¥',
            'AUD': 'A$',
            'CAD': 'C$',
            'CHF': 'CHF',
            'CNY': '¥',
            'SEK': 'kr',
            'NZD': 'NZ$',
            'MXN': 'MX$',
            'SGD': 'S$',
            'HKD': 'HK$',
            'NOK': 'kr',
            'KRW': '₩',
            'TRY': '₺',
            'RUB': '₽',
            'INR': '₹',
            'BRL': 'R$',
            'ZAR': 'R'
        }
        return symbols.get(code, code)
