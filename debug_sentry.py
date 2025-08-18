#!/usr/bin/env python3
"""
🧪 Sentry Debug Test Route for UmrahCheck API
Test error monitoring and message capture functionality
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sentry_sdk
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class DebugResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    sentry_event_id: str = None

@router.get("/debug-sentry", response_model=DebugResponse)
async def test_sentry_error():
    """Test route to trigger Sentry error capture"""
    try:
        # Intentionally throw an error to test Sentry
        raise Exception("🚨 Test error from Sentry debug route - this is intentional for testing")
    except Exception as e:
        # Capture the error with additional context
        event_id = sentry_sdk.capture_exception(e, extra={
            "test_route": True,
            "endpoint": "/debug-sentry",
            "timestamp": datetime.now().isoformat(),
            "test_type": "error_capture"
        })
        
        return DebugResponse(
            success=False,
            message="Test error thrown and captured by Sentry",
            timestamp=datetime.now().isoformat(),
            sentry_event_id=str(event_id) if event_id else "none"
        )

@router.post("/debug-sentry", response_model=DebugResponse)
async def test_sentry_message():
    """Test route to send custom message to Sentry"""
    
    # Add breadcrumb
    sentry_sdk.add_breadcrumb(
        message="Debug POST request received",
        level="info",
        category="api.debug"
    )
    
    # Capture custom message
    event_id = sentry_sdk.capture_message(
        "🧪 Custom test message from debug API",
        level="info",
        extras={
            "test_route": True,
            "endpoint": "/debug-sentry POST",
            "timestamp": datetime.now().isoformat(),
            "test_type": "message_capture"
        }
    )
    
    return DebugResponse(
        success=True,
        message="Custom Sentry message sent successfully",
        timestamp=datetime.now().isoformat(),
        sentry_event_id=str(event_id) if event_id else "none"
    )

@router.get("/debug-sentry/performance")
async def test_sentry_performance():
    """Test route for performance monitoring"""
    import time
    
    # Start a transaction
    with sentry_sdk.start_transaction(op="api.test", name="performance_test"):
        # Simulate some work
        with sentry_sdk.start_span(op="db.query", description="simulated database query"):
            time.sleep(0.1)  # Simulate DB query
            
        with sentry_sdk.start_span(op="http.request", description="simulated API call"):
            time.sleep(0.05)  # Simulate API call
    
    return {
        "success": True,
        "message": "Performance test completed",
        "timestamp": datetime.now().isoformat()
    }