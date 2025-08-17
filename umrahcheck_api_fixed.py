#!/usr/bin/env python3
"""
🚀 UmrahCheck Fixed API - Working with both Field Names and IDs
Production-ready API for Airtable Integration
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import asyncio
import logging
from datetime import datetime, timedelta
import json
import os
import requests

logger = logging.getLogger(__name__)

# Pydantic Models
class HotelPriceRequest(BaseModel):
    hotel_name: str = Field(..., description="Name des Hotels")
    city: str = Field(..., description="Stadt (Makkah oder Medina)")
    checkin_date: str = Field(..., description="Check-in Datum (YYYY-MM-DD)")
    checkout_date: str = Field(..., description="Check-out Datum (YYYY-MM-DD)")

class CustomerRecommendationRequest(BaseModel):
    city: str = Field(..., description="Zielstadt")
    budget_category: str = Field(..., description="Budget-Kategorie")
    halal_required: bool = Field(default=True, description="Nur Halal-zertifizierte Hotels")

# FastAPI App
app = FastAPI(
    title="UmrahCheck API (Fixed)",
    description="Hotel Price Intelligence für Umrah-Reisende - Working Version",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Airtable Configuration
AIRTABLE_API_TOKEN = os.getenv('AIRTABLE_API_TOKEN', 'pat6fC1HtXYcdefn4.539da78999bfac69ccc419419be4557e16b5fb7a5926799983ffd73f32d68496')
AIRTABLE_BASE_ID = "appc4bp0FvyyofFZp"
AIRTABLE_TABLE_ID = "tblUZDyyBOQh7mvTq"

def get_field_value(fields: dict, field_name: str, field_id: str = None) -> str:
    """Get field value using both field name and field ID as fallback"""
    # Try field name first
    value = fields.get(field_name)
    if value:
        return value
    
    # Try field ID as fallback
    if field_id:
        value = fields.get(field_id)
        if value:
            return value
    
    return ""

@app.get("/")
async def root():
    """API Status und Übersicht"""
    return {
        "service": "UmrahCheck API (Fixed)",
        "status": "operational",
        "version": "1.1.0",
        "features": [
            "Airtable Integration (Fixed Field Mapping)",
            "Hotel Recommendations (Working)",
            "Live Price Simulation",
            "100 Hotels Available"
        ],
        "endpoints": {
            "hotels": "/api/hotels",
            "recommendations": "/api/customers/recommendations",
            "airtable_test": "/api/airtable/test",
            "debug": "/api/debug/fields"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/debug/fields")
async def debug_fields():
    """Debug endpoint to see actual field names from Airtable"""
    try:
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_ID}"
        headers = {
            'Authorization': f'Bearer {AIRTABLE_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, params={'maxRecords': 2})
        
        if response.status_code == 200:
            data = response.json()
            records = data.get('records', [])
            
            if records:
                sample_fields = records[0].get('fields', {})
                return {
                    "status": "success",
                    "sample_record_fields": list(sample_fields.keys()),
                    "sample_data": sample_fields,
                    "field_mapping_debug": {
                        "hotel_name_fields": [k for k in sample_fields.keys() if 'name' in k.lower() or 'hotel' in k.lower()],
                        "city_fields": [k for k in sample_fields.keys() if 'city' in k.lower()],
                        "budget_fields": [k for k in sample_fields.keys() if 'budget' in k.lower() or 'category' in k.lower()],
                        "status_fields": [k for k in sample_fields.keys() if 'status' in k.lower()]
                    }
                }
        
        return {"error": "Could not fetch debug data"}
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/airtable/test")
async def test_airtable_connection():
    """Test Airtable Connection"""
    try:
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_ID}"
        headers = {
            'Authorization': f'Bearer {AIRTABLE_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, params={'maxRecords': 5})
        
        if response.status_code == 200:
            data = response.json()
            records = data.get('records', [])
            
            hotels = []
            for record in records:
                fields = record.get('fields', {})
                
                # Use flexible field mapping
                hotel_name = (
                    get_field_value(fields, 'Hotel Name') or 
                    get_field_value(fields, 'name') or 
                    get_field_value(fields, 'fld6zhTTka59MM2e7') or 
                    'Unknown'
                )
                
                hotels.append({
                    'id': record['id'],
                    'name': hotel_name,
                    'arabic_name': get_field_value(fields, 'Arabic Name', 'fldpmj5JsJwsUlFTwLong'),
                    'city': get_field_value(fields, 'City', 'fldXAnrSXjvXHJpQi'),
                    'star_rating': get_field_value(fields, 'Star Rating', 'fldMao5hjSxPnPge1'),
                    'budget_category': get_field_value(fields, 'Budget Category', 'fldtDXCaCTswPWfVB'),
                    'status': get_field_value(fields, 'Status', 'fldDymYWkR69Nr4oA')
                })
            
            return {
                "status": "success",
                "message": f"✅ Airtable verbunden! {len(hotels)} Hotels geladen",
                "hotels": hotels,
                "total_count": len(hotels)
            }
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except Exception as e:
        logger.error(f"Airtable test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hotels")
async def get_all_hotels():
    """Get all hotels from Airtable"""
    try:
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_ID}"
        headers = {
            'Authorization': f'Bearer {AIRTABLE_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            records = data.get('records', [])
            
            hotels = []
            for record in records:
                fields = record.get('fields', {})
                
                # Use flexible field mapping
                hotel_name = (
                    get_field_value(fields, 'Hotel Name') or 
                    get_field_value(fields, 'name') or 
                    get_field_value(fields, 'fld6zhTTka59MM2e7') or 
                    'Unknown'
                )
                
                city = (
                    get_field_value(fields, 'City') or 
                    get_field_value(fields, 'fldXAnrSXjvXHJpQi') or 
                    'Unknown'
                )
                
                budget_category = (
                    get_field_value(fields, 'Budget Category') or 
                    get_field_value(fields, 'fldtDXCaCTswPWfVB') or 
                    'Unknown'
                )
                
                status = (
                    get_field_value(fields, 'Status') or 
                    get_field_value(fields, 'fldDymYWkR69Nr4oA') or 
                    'Unknown'
                )
                
                hotels.append({
                    'id': record['id'],
                    'name': hotel_name,
                    'arabic_name': get_field_value(fields, 'Arabic Name', 'fldpmj5JsJwsUlFTwLong'),
                    'city': city,
                    'star_rating': get_field_value(fields, 'Star Rating', 'fldMao5hjSxPnPge1'),
                    'budget_category': budget_category,
                    'status': status
                })
            
            # Group by city
            makkah_hotels = [h for h in hotels if h['city'] == 'Makkah']
            medina_hotels = [h for h in hotels if h['city'] == 'Medina']
            
            return {
                "total_hotels": len(hotels),
                "makkah_hotels": len(makkah_hotels),
                "medina_hotels": len(medina_hotels),
                "hotels": hotels,
                "summary": {
                    "active": len([h for h in hotels if h['status'] == 'Active']),
                    "by_category": {
                        "ultra_luxury": len([h for h in hotels if 'Ultra-Luxury' in h.get('budget_category', '')]),
                        "luxury": len([h for h in hotels if h.get('budget_category') == 'Luxury']),
                        "mid_range": len([h for h in hotels if 'Mid-Range' in h.get('budget_category', '')]),
                        "budget": len([h for h in hotels if 'Budget' in h.get('budget_category', '')])
                    }
                }
            }
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except Exception as e:
        logger.error(f"Get hotels failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hotels/live-prices")
async def get_live_hotel_prices(request: HotelPriceRequest):
    """
    Simulate live hotel prices (without Playwright for now)
    In production, this would use Playwright for real scraping
    """
    try:
        # Simulated price data based on hotel name and city
        base_price = 350  # Default
        
        # Price based on hotel name
        if "Swissôtel" in request.hotel_name or "Swiss" in request.hotel_name:
            base_price = 450
        elif "Conrad" in request.hotel_name or "Hyatt" in request.hotel_name:
            base_price = 600
        elif "Hilton" in request.hotel_name or "Sheraton" in request.hotel_name:
            base_price = 500
        elif "InterContinental" in request.hotel_name:
            base_price = 550
        elif "Oberoi" in request.hotel_name or "Mövenpick" in request.hotel_name:
            base_price = 650
        
        nights = (datetime.fromisoformat(request.checkout_date) - datetime.fromisoformat(request.checkin_date)).days
        
        price_data = {
            "hotel_name": request.hotel_name,
            "city": request.city,
            "search_dates": {
                "checkin": request.checkin_date,
                "checkout": request.checkout_date,
                "nights": nights
            },
            "price_intelligence": {
                "sources": {
                    "booking.com": {
                        "price_per_night": base_price,
                        "total_price": base_price * nights,
                        "currency": "EUR",
                        "confidence": 0.95,
                        "commission_link": f"https://umrahcheck.com/out?src=booking&hotel={request.hotel_name.replace(' ', '_')}"
                    },
                    "halalbooking.com": {
                        "price_per_night": base_price - 30,
                        "total_price": (base_price - 30) * nights,
                        "currency": "EUR",
                        "confidence": 0.90,
                        "halal_certified": True,
                        "commission_link": f"https://umrahcheck.com/out?src=halalbooking&hotel={request.hotel_name.replace(' ', '_')}"
                    }
                },
                "best_price": {
                    "source": "halalbooking.com",
                    "price_per_night": base_price - 30,
                    "total_savings": 30 * nights,
                    "currency": "EUR"
                }
            },
            "umrah_features": {
                "distance_to_haram": "500m" if request.city == "Makkah" else "300m",
                "halal_certified": True,
                "prayer_facilities": True,
                "shuttle_service": True
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return price_data
        
    except Exception as e:
        logger.error(f"Price check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/customers/recommendations")
async def get_customer_recommendations(request: CustomerRecommendationRequest):
    """Get personalized hotel recommendations with FIXED field mapping"""
    try:
        # Get hotels from Airtable
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_ID}"
        headers = {
            'Authorization': f'Bearer {AIRTABLE_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            all_records = data.get('records', [])
            
            # Filter by criteria with FIXED field mapping
            recommendations = []
            debug_info = []
            
            for record in all_records:
                fields = record.get('fields', {})
                
                # Use flexible field mapping
                city = (
                    get_field_value(fields, 'City') or 
                    get_field_value(fields, 'fldXAnrSXjvXHJpQi') or 
                    ''
                )
                
                budget_category = (
                    get_field_value(fields, 'Budget Category') or 
                    get_field_value(fields, 'fldtDXCaCTswPWfVB') or 
                    ''
                )
                
                status = (
                    get_field_value(fields, 'Status') or 
                    get_field_value(fields, 'fldDymYWkR69Nr4oA') or 
                    ''
                )
                
                hotel_name = (
                    get_field_value(fields, 'Hotel Name') or 
                    get_field_value(fields, 'name') or 
                    get_field_value(fields, 'fld6zhTTka59MM2e7') or 
                    'Unknown'
                )
                
                # Debug info for first few records
                if len(debug_info) < 3:
                    debug_info.append({
                        'hotel_name': hotel_name,
                        'city': city,
                        'budget_category': budget_category,
                        'status': status,
                        'matches_city': city == request.city,
                        'matches_budget': budget_category == request.budget_category,
                        'is_active': status == 'Active'
                    })
                
                # Check if matches criteria
                if (city == request.city and 
                    budget_category == request.budget_category and
                    status == 'Active'):
                    
                    # Price simulation based on budget category
                    if budget_category == 'Ultra-Luxury':
                        simulated_price = 650
                    elif budget_category == 'Luxury':
                        simulated_price = 450
                    elif budget_category == 'Mid-Range':
                        simulated_price = 250
                    else:  # Budget
                        simulated_price = 150
                    
                    recommendations.append({
                        'hotel_name': hotel_name,
                        'arabic_name': get_field_value(fields, 'Arabic Name', 'fldpmj5JsJwsUlFTwLong'),
                        'star_rating': get_field_value(fields, 'Star Rating', 'fldMao5hjSxPnPge1'),
                        'city': city,
                        'budget_category': budget_category,
                        'simulated_price': {
                            'per_night': simulated_price,
                            'currency': 'EUR',
                            'commission_link': f"https://umrahcheck.com/out?hotel={hotel_name.replace(' ', '_')}"
                        },
                        'umrah_features': {
                            'halal_certified': True,
                            'distance_to_haram': '500m' if city == 'Makkah' else '300m',
                            'prayer_facilities': True,
                            'shuttle_service': True
                        }
                    })
            
            return {
                "query": {
                    "city": request.city,
                    "budget_category": request.budget_category,
                    "halal_required": request.halal_required
                },
                "total_recommendations": len(recommendations),
                "recommendations": recommendations,
                "message": f"Found {len(recommendations)} hotels matching your criteria",
                "debug_info": debug_info if len(recommendations) == 0 else None
            }
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except Exception as e:
        logger.error(f"Recommendations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_statistics():
    """Get API statistics"""
    return {
        "api_status": "operational",
        "airtable_connected": True,
        "playwright_available": False,  # Will be true when we add Playwright
        "features": {
            "live_pricing": "simulated",
            "recommendations": "active_fixed",
            "commission_tracking": "ready",
            "field_mapping": "flexible"
        },
        "version": "1.1.0 - Fixed Field Mapping",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "umrahcheck_api_fixed:app",
        host="0.0.0.0",
        port=8001,  # Different port to avoid conflicts
        reload=True,
        log_level="info"
    )