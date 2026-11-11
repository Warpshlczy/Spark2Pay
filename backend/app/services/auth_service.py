"""
Authentication Service
Handles password hashing, JWT tokens, and TOTP 2FA
"""
import bcrypt
import pyotp
import jwt
from datetime import datetime, timedelta
from typing import Optional


class AuthService:
    """Authentication service for user management"""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify password against hash

        Args:
            password: Plain text password
            hashed: Hashed password

        Returns:
            True if password matches
        """
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    @staticmethod
    def generate_totp_secret() -> str:
        """
        Generate TOTP secret for 2FA

        Returns:
            Base32 encoded secret
        """
        return pyotp.random_base32()

    @staticmethod
    def get_totp_uri(secret: str, username: str, issuer: str = 'Spark2Pay') -> str:
        """
        Generate TOTP provisioning URI for QR code

        Args:
            secret: TOTP secret
            username: User's username
            issuer: Service name

        Returns:
            Provisioning URI
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=username, issuer_name=issuer)

    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        """
        Verify TOTP code

        Args:
            secret: TOTP secret
            code: 6-digit code from authenticator app

        Returns:
            True if code is valid
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

    @staticmethod
    def generate_token(user_id: int, secret_key: str, expires_in: int = 2592000) -> str:
        """
        Generate JWT token

        Args:
            user_id: User ID to encode
            secret_key: JWT secret key
            expires_in: Token expiration in seconds (default 30 days)

        Returns:
            JWT token
        """
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, secret_key, algorithm='HS256')

    @staticmethod
    def verify_token(token: str, secret_key: str) -> Optional[int]:
        """
        Verify JWT token and return user_id

        Args:
            token: JWT token
            secret_key: JWT secret key

        Returns:
            User ID if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            return payload.get('user_id')
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def generate_qr_code_data_uri(totp_uri: str) -> str:
        """
        Generate QR code as data URI for TOTP setup

        Args:
            totp_uri: TOTP provisioning URI

        Returns:
            Data URI for QR code image
        """
        import qrcode
        import io
        import base64

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64 data URI
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode()

        return f"data:image/png;base64,{img_base64}"
