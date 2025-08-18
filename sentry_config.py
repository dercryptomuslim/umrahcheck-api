import sentry_sdk
import os
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging

def init_sentry():
    """Initialize Sentry for FastAPI backend with UmrahCheck configuration"""
    
    # Temporary disable for deployment fix
    if os.getenv('DISABLE_SENTRY', 'false').lower() == 'true':
        print("⚠️ Sentry disabled via DISABLE_SENTRY environment variable")
        return
    
    # Use the provided DSN directly (same as frontend for now)
    sentry_dsn = "https://d5f99134cd8bdcc0e3154295e60dd883@o4509861037080576.ingest.de.sentry.io/4509861255184464"
    environment = os.getenv('ENVIRONMENT', 'development')
    
    # Configure logging integration
    logging_integration = LoggingIntegration(
        level=logging.INFO,        # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        
        # Add data like request headers and IP for users
        send_default_pii=True,
        
        # Performance monitoring - adjust for production
        traces_sample_rate=1.0 if environment == 'development' else 0.1,
        
        # Environment
        environment=environment,
        
        # Release tracking
        release=f"umrahcheck-api@{os.getenv('RAILWAY_GIT_COMMIT_SHA', 'dev')}",
        
        # Integrations
        integrations=[
            FastApiIntegration(
                transaction_style="endpoint"
            ),
            logging_integration,
        ],
        
        # Custom error filtering
        before_send=filter_errors,
        
        # Tags
        tags={
            "component": "backend",
            "platform": "railway",
            "service": "umrahcheck-api"
        }
    )
    
    print(f"✅ Sentry initialized successfully for {environment} environment")

def filter_errors(event, hint):
    """Filter out non-critical errors"""
    
    # Get request URL if available
    request_url = event.get('request', {}).get('url', '')
    
    # Filter out health check endpoints
    if any(endpoint in request_url for endpoint in ['/health', '/healthz', '/ping']):
        return None
    
    # Filter out specific known issues
    if 'exception' in event:
        exc_info = event['exception']['values'][0]
        exc_type = exc_info.get('type', '')
        
        # Filter out non-critical connection errors
        if 'ConnectionError' in exc_type or 'TimeoutError' in exc_type:
            # Only send if it's a critical error
            return event if event.get('level') == 'error' else None
            
        # Filter out expected 404s for certain endpoints
        if exc_type == 'HTTPException':
            status_code = event.get('extra', {}).get('status_code', 0)
            if status_code == 404 and '/api/' not in request_url:
                return None
    
    return event

# Context helpers
def set_user_context(user_id: str, email: str = None):
    """Set user context for better error tracking"""
    sentry_sdk.set_user({
        "id": user_id,
        "email": email
    })

def set_transaction_context(transaction_name: str, **kwargs):
    """Set transaction context"""
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("transaction", transaction_name)
        for key, value in kwargs.items():
            scope.set_extra(key, value)

def capture_api_error(error: Exception, context: dict = None):
    """Capture API error with context"""
    with sentry_sdk.configure_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_extra(key, value)
        
        sentry_sdk.capture_exception(error)

# Performance monitoring helpers
def start_span(op: str, description: str):
    """Start a performance monitoring span"""
    return sentry_sdk.start_span(op=op, description=description)

def track_airtable_request(operation: str):
    """Track Airtable API requests"""
    return sentry_sdk.start_span(
        op="http.client",
        description=f"Airtable API - {operation}"
    )

def track_hotel_recommendation(city: str, budget: str):
    """Track hotel recommendation queries"""
    span = sentry_sdk.start_span(
        op="hotel.recommendation",
        description=f"Find hotels in {city} - {budget}"
    )
    span.set_tag("city", city)
    span.set_tag("budget_category", budget)
    return span

# Logging helper
def get_logger(name: str):
    """Get a logger instance with Sentry integration"""
    logger = logging.getLogger(name)
    return logger