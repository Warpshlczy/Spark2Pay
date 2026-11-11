#!/usr/bin/env python3
"""
Spark2Pay Backend Entry Point
Run the Flask development server
"""
import os
from app import create_app

# Determine environment
env = os.getenv('FLASK_ENV', 'development')

# Create app
app = create_app(env)

if __name__ == '__main__':
    port = app.config.get('PORT', 3038)
    debug = app.config.get('DEBUG', True)

    print(f"""
    ╔═══════════════════════════════════════════╗
    ║                                           ║
    ║          Spark2Pay Backend API            ║
    ║   AI advice  ->  PayPal execution         ║
    ║                                           ║
    ╚═══════════════════════════════════════════╝

    🚀 Server starting on http://localhost:{port}
    📚 API status: http://localhost:{port}/api/v1/status
    💚 Health check: http://localhost:{port}/health

    Environment: {env}
    PayPal mode: {app.config.get('PAYPAL_MODE')}
    AI provider: {app.config.get('AI_PROVIDER')}

    Press CTRL+C to quit
    """)

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
