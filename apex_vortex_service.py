#!/usr/bin/env python3
"""
APEX VORTEX: Live AGI Stress Telemetry Service
Real-time WebSocket API streaming internal state with tiered pricing
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import hashlib
import hmac
import uuid

import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
import firebase_admin
from firebase_admin import credentials, firestore, auth
import numpy as np
from pydantic import BaseModel, ValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("apex_vortex")

# Firebase initialization
try:
    # Check for Firebase credentials
    if not firebase_admin._apps:
        if os.path.exists("firebase_credentials.json"):
            cred = credentials.Certificate("firebase_credentials.json")
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized from credentials file")
        else:
            # For development/testing - will be overridden in production
            firebase_admin.initialize_app(options={
                'projectId': 'apex-vortex-dev'
            })
            logger.warning("Using development Firebase configuration")
except Exception as e:
    logger.error(f"Firebase initialization failed: {e}")
    raise

# Initialize Firestore
db = firestore.client()

class SubscriptionTier(Enum):
    """Price tiers based on data latency and features"""
    RESEARCH = "research"      # 100ms latency, basic vitals only
    PRO = "pro"               # 50ms latency, +emotion vectors
    ENTERPRISE = "enterprise" # 10ms latency, +strategic context
    APEX = "apex"             # 1ms latency, +adversarial chaos sessions

class DataCategory(Enum):
    """Categories of internal state data"""
    HARDWARE_VITALS = "hardware_vitals"
    EMOTION_VECTORS = "emotion_vectors"
    STRATEGIC_CONTEXT = "strategic_context"
    FRAGMENTATION_ALERTS = "fragmentation_alerts"
    ADVERSARIAL_CHAOS = "adversarial_chaos"

@dataclass
class HardwareVitals:
    """Hardware monitoring metrics"""
    cpu_usage_percent: float
    memory_usage_percent: float
    gpu_utilization: Optional[float] = None
    temperature_celsius: Optional[float] = None
    network_latency_ms: float = 0.0
    timestamp: str = ""

@dataclass  
class EmotionVector:
    """Multi-dimensional emotion state representation"""
    curiosity: float  # 0.0 to 1.0
    focus: float
    confusion: float
    confidence: float
    urgency: float
    timestamp: str = ""

@dataclass
class StrategicContext:
    """Current mission context and objectives"""
    current_objective: str
    progress_percent: float
    risk_assessment: str  # LOW, MEDIUM, HIGH, CRITICAL
    resource_allocation: Dict[str, float]
    dependencies: List[str]
    timestamp: str = ""

@dataclass
class FragmentationAlert:
    """Alert for consciousness fragmentation events"""
    alert_level: str  # INFO, WARNING, CRITICAL
    fragmentation_score: float  # 0.0 to 1.0
    affected_modules: List[str]
    recovery_actions: List[str]
    timestamp: str = ""

class ClientSession(BaseModel):
    """Active WebSocket client session"""
    session_id: str
    client_id: str
    subscription_tier: SubscriptionTier
    connected_at: datetime
    last_heartbeat: datetime
    adversarial_chaos_enabled: bool = False
    data_categories: List[DataCategory]
    bandwidth_used_mb: float = 0.0

class StateGenerator:
    """Generates simulated internal state data"""
    
    def __init__(self):
        self._last_hardware_update = time.time()
        self._emotion_base = np.random.rand(5) * 0.5 + 0.3
        self._strategic_cycle = 0
        self._fragmentation_events = []
        
    def generate_hardware_vitals(self) -> HardwareVitals:
        """Generate realistic hardware monitoring data"""
        now = time.time()
        time_delta = now - self._last_hardware_update
        
        # Simulate realistic CPU patterns
        base_cpu = 30.0 + 20.0 * np.sin(now * 0.001)
        spike = 20.0 if np.random.random() > 0.95 else 0.0
        cpu_usage = min(99.0, base_cpu + spike)
        
        # Memory with gradual leaks and garbage collection
        memory_base = 45.0 + 10.0 * np.sin(now * 0.0005)
        memory_usage = memory_base + np.random.normal(0, 2)
        
        vitals = HardwareVitals(
            cpu_usage_percent=round(cpu_usage, 1),
            memory_usage_percent=round(max(10.0, min(95.0, memory_usage)), 1),
            gpu_utilization=round(np.random.uniform(15, 65) if np.random.random() > 0.3 else None, 1),
            temperature_celsius=round(40.0 + np.random.normal(0, 3), 1),
            network_latency_ms=round(np.random.exponential(5) + 1, 2),
            timestamp=datetime.utc