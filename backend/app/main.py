"""
VPN Master Panel - FastAPI Main Application
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Dict, Any

from .config import settings
from .database import init_db, engine
from . import models

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
    logger.info("🚀 Starting VPN Master Panel...")
    
    try:
        # Initialize database
        init_db()
        logger.info("✅ Database initialized")
        
        # Create initial admin user if not exists
        from .utils.security import create_initial_admin
        create_initial_admin()
        
        # Start tunnel monitoring
        from .tunnels.persianshield import PersianShieldManager
        shield_manager = PersianShieldManager()
        shield_manager.start_monitoring()
        app.state.shield_manager = shield_manager
        
        logger.info("✅ VPN Master Panel started successfully")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down VPN Master Panel...")
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

# Add Gzip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
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


# System info endpoint
@app.get("/api/system/info")
async def system_info():
    """Get system information"""
    import psutil
    import platform
    
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
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


# Import and include routers
from .api import auth, users, servers, tunnels, monitoring

app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])
app.include_router(servers.router, prefix=f"{settings.API_V1_PREFIX}/servers", tags=["Servers"])
app.include_router(tunnels.router, prefix=f"{settings.API_V1_PREFIX}/tunnels", tags=["Tunnels"])
app.include_router(monitoring.router, prefix=f"{settings.API_V1_PREFIX}/monitoring", tags=["Monitoring"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
