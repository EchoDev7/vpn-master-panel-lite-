"""
VPN Master Panel - FastAPI Main Application
"""
from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import asyncio
import json
from typing import Dict, Any

from .config import settings
from .database import init_db, engine
from . import models
from .utils.security import get_current_admin

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events - startup and shutdown
    """
    # Startup
    logger.info("Starting VPN Master Panel (Lite Edition)...")

    # Security sanity check
    if settings.is_default_secret:
        logger.warning(
            "⚠️  WARNING: Using default SECRET_KEY! "
            "Set a strong SECRET_KEY env variable before deploying to production. "
            "Run: openssl rand -hex 32"
        )

    try:
        # Initialize database FIRST (Critical: Creates tables)
        init_db()
        logger.info("✅ Database initialized")

        # Auto-Heal: Ensure OpenVPN Config & PKI (Added by Fix)
        try:
            from .services.openvpn import OpenVPNService
            service = OpenVPNService()
            
            logger.info("🔐 Checking/Generating OpenVPN PKI...")
            service._ensure_pki()
            
            logger.info("🔧 Checking/Generating OpenVPN Server Config...")
            config_content = service.generate_server_config()
            
            # Write config to default location
            config_path = "/etc/openvpn/server.conf"
            try:
                with open(config_path, "w") as f:
                    f.write(config_content)
                logger.info(f"✅ Server config written to {config_path}")
            except (FileNotFoundError, PermissionError) as e:
                 logger.warning(f"⚠️ Could not write to {config_path}: {e}")

        except Exception as e:
            logger.error(f"❌ OpenVPN Initialization Failed: {e}")

        # Create initial admin user if not exists
        from .utils.security import create_initial_admin
        create_initial_admin()
        
        # Start tunnel monitoring
        from .tunnels.persianshield import PersianShieldManager
        shield_manager = PersianShieldManager()
        shield_manager.start_monitoring()
        app.state.shield_manager = shield_manager
        
        # Start WebSocket heartbeat
        from .websocket.manager import start_heartbeat
        asyncio.create_task(start_heartbeat())
        logger.info("✅ WebSocket heartbeat started")

        # Start Traffic Monitor (User Management 2.0)
        try:
            from .services.monitoring import traffic_monitor
            asyncio.create_task(traffic_monitor.start())
            logger.info("✅ Traffic Monitor started")
        except Exception as e:
            logger.error(f"❌ Traffic Monitor failed to start: {e}")

        # Start Scheduler Service
        try:
            from .services.scheduler import scheduler as scheduler_service
            asyncio.create_task(scheduler_service.start())
            logger.info("✅ Scheduler Service started")
        except Exception as e:
            logger.error(f"❌ Scheduler Service failed to start: {e}")
        
        # Initialize Telegram bot (if configured)
        try:
            from .services.telegram import telegram_service
            if telegram_service.bot_token:
                await telegram_service.initialize()
                logger.info("✅ Telegram bot initialized")
            else:
                logger.info("ℹ️  Telegram bot not configured (skipped)")
        except Exception as e:
            logger.warning(f"⚠️  Telegram bot initialization failed: {e}")

        # Initialize default settings
        try:
            from .database import get_db_context
            from .api.settings import init_default_settings
            with get_db_context() as db:
                init_default_settings(db)
            logger.info("✅ Default settings initialized")
        except Exception as e:
            logger.warning(f"⚠️  Default settings initialization failed: {e}")

        logger.info("✅ VPN Master Panel started successfully!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down VPN Master Panel...")

    # Stop Scheduler
    try:
        from .services.scheduler import scheduler as scheduler_service
        await scheduler_service.stop()
        logger.info("✅ Scheduler Service stopped")
    except Exception as e:
        logger.warning(f"⚠️  Scheduler stop failed: {e}")

    # Stop Traffic Monitor
    try:
        from .services.monitoring import traffic_monitor
        await traffic_monitor.stop()
        logger.info("✅ Traffic Monitor stopped")
    except Exception as e:
        logger.warning(f"⚠️  Traffic Monitor shutdown failed: {e}")
    
    # Shutdown telegram bot
    try:
        from .services.telegram import telegram_service
        await telegram_service.shutdown()
        logger.info("✅ Telegram bot shutdown")
    except Exception as e:
        logger.warning(f"⚠️  Telegram bot shutdown failed: {e}")
    logger.info("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Advanced Multi-Protocol VPN Management Panel with Anti-Censorship Features",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# NOTE: GZipMiddleware is intentionally NOT added here.
# It buffers the entire response body before compressing, which breaks
# StreamingResponse (certbot live output). Static file compression is
# handled by Nginx (gzip on; in nginx.conf) — zero overhead on FastAPI side.


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

@app.get("/api/health")
async def api_health_check():
    """API Health check endpoint for Nginx"""
    return {
        "status": "healthy",
        "service": "backend",
        "version": settings.APP_VERSION
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "VPN Master Panel API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


# System info endpoint — admin only
@app.get("/api/system/info")
async def system_info(
    current_admin=Depends(get_current_admin)
):
    """Get system information (Admin only)"""
    import psutil
    import platform

    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "architecture": platform.machine(),
        "cpu_count": psutil.cpu_count(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent
        },
        "disk": {
            "total": psutil.disk_usage('/').total,
            "used": psutil.disk_usage('/').used,
            "free": psutil.disk_usage('/').free,
            "percent": psutil.disk_usage('/').percent
        }
    }


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# WebSocket endpoint
@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket endpoint for real-time updates"""
    from .websocket.manager import manager
    from .websocket.handlers import WebSocketHandler
    from jose import JWTError
    from .config import settings as app_settings
    from jose import jwt as jose_jwt

    # Validate token before accepting the WebSocket — decode_token raises
    # HTTPException which WebSocket cannot handle gracefully, so we use
    # jose directly and close with the correct WebSocket close code.
    try:
        payload = jose_jwt.decode(
            token, app_settings.SECRET_KEY, algorithms=[app_settings.ALGORITHM]
        )
    except JWTError as exc:
        logger.warning(f"WebSocket rejected — invalid token: {exc}")
        await websocket.close(code=1008, reason="Invalid token")
        return
    except Exception as exc:
        logger.error(f"WebSocket token decode error: {exc}")
        await websocket.close(code=1011, reason="Internal error")
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=1008, reason="Invalid token payload")
        return

    is_admin = payload.get("role") in ("admin", "super_admin")

    try:
        # Accept and register connection
        await manager.connect(websocket, user_id, is_admin)

        try:
            while True:
                # Receive messages from client
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle message
                await WebSocketHandler.handle_message(websocket, message)

        except WebSocketDisconnect:
            manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            manager.disconnect(websocket)

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal error")
        except Exception:
            pass


# Import and include routers
from .api import auth, users, servers, tunnels, monitoring, notifications, activity, diagnostics, subscription

app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])
app.include_router(servers.router, prefix=f"{settings.API_V1_PREFIX}/servers", tags=["Servers"])
app.include_router(tunnels.router, prefix=f"{settings.API_V1_PREFIX}/tunnels", tags=["Tunnels"])
app.include_router(monitoring.router, prefix=f"{settings.API_V1_PREFIX}/monitoring", tags=["Monitoring"])
app.include_router(diagnostics.router, prefix=f"{settings.API_V1_PREFIX}/diagnostics", tags=["Diagnostics"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Notifications"])
app.include_router(activity.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Activity"])

# Real-time Connections
from .api import connections
app.include_router(connections.router, prefix=f"{settings.API_V1_PREFIX}/connections", tags=["Connections"])

# Subscription Router (Public Access)
app.include_router(subscription.router, prefix="/sub", tags=["Subscription"])


# Settings Router
from .api import settings as api_settings
app.include_router(api_settings.router, prefix=f"{settings.API_V1_PREFIX}/settings", tags=["Settings"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
