"""
Monitoring API Endpoints - Real-time system and VPN monitoring
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any
from datetime import datetime, timedelta

from ..database import get_db
from ..models.user import User, ConnectionLog, TrafficLog
from ..utils.security import get_current_admin

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get dashboard statistics"""
    try:
        # Total users
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.status == "active").count()
        
        # Active connections
        try:
            active_connections = db.query(ConnectionLog).filter(
                ConnectionLog.is_active == True
            ).count()
        except:
            active_connections = 0
        
        # Total traffic (last 24h)
        try:
            day_ago = datetime.utcnow() - timedelta(days=1)
            traffic_24h = db.query(
                func.sum(TrafficLog.upload_bytes + TrafficLog.download_bytes)
            ).filter(
                TrafficLog.recorded_at >= day_ago
            ).scalar() or 0
        except:
            traffic_24h = 0
        
        # System stats
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)  # Reduced interval
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to get system stats: {e}")
            cpu_percent = 0
            memory_percent = 0
            disk_percent = 0
        
        return {
            "users": {
                "total": total_users,
                "active": active_users
            },
            "connections": {
                "active": active_connections
            },
            "traffic": {
                "bytes_24h": traffic_24h,
                "gb_24h": round(traffic_24h / (1024**3), 2)
            },
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Dashboard endpoint error: {e}", exc_info=True)
        
        # Return minimal valid data
        return {
            "users": {"total": 0, "active": 0},
            "connections": {"active": 0},
            "traffic": {"bytes_24h": 0, "gb_24h": 0},
            "system": {"cpu_percent": 0, "memory_percent": 0, "disk_percent": 0},
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/active-connections")
async def get_active_connections(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get list of active connections"""
    connections = db.query(ConnectionLog).filter(
        ConnectionLog.is_active == True
    ).all()
    
    result = []
    for conn in connections:
        result.append({
            "user_id": conn.user_id,
            "username": conn.user.username if conn.user else None,
            "protocol": conn.protocol,
            "client_ip": conn.client_ip,
            "virtual_ip": conn.virtual_ip,
            "connected_at": conn.connected_at.isoformat() if conn.connected_at else None
        })
    
    return result


@router.get("/traffic-stats")
async def get_traffic_stats(
    days: int = 7,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get traffic statistics for the last N days"""
    from sqlalchemy import func
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Group by date using SQLite-compatible func.date()
    daily_traffic = db.query(
        func.date(TrafficLog.recorded_at).label('date'),
        func.sum(TrafficLog.upload_bytes).label('upload'),
        func.sum(TrafficLog.download_bytes).label('download')
    ).filter(
        TrafficLog.recorded_at >= start_date
    ).group_by(
        func.date(TrafficLog.recorded_at)
    ).all()
    
    result = []
    for day in daily_traffic:
        result.append({
            "date": day.date if isinstance(day.date, str) else str(day.date),
            "upload_gb": round((day.upload or 0) / (1024**3), 2),
            "download_gb": round((day.download or 0) / (1024**3), 2),
            "total_gb": round(((day.upload or 0) + (day.download or 0)) / (1024**3), 2)
        })
    
    return result


@router.get("/server-resources")
async def get_detailed_server_resources(
    current_admin: User = Depends(get_current_admin)
):
    """Get detailed server resource metrics"""
    import psutil
    import time
    
    # CPU details
    cpu_percent_per_core = psutil.cpu_percent(interval=0.5, percpu=True)
    cpu_freq = psutil.cpu_freq()
    try:
        load_avg = psutil.getloadavg()
    except AttributeError:
        # getloadavg not available on Windows
        load_avg = (0, 0, 0)
    
    # Memory details
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    # Disk I/O
    try:
        disk_io = psutil.disk_io_counters()
        disk_io_dict = {
            "read_bytes": disk_io.read_bytes,
            "write_bytes": disk_io.write_bytes,
            "read_count": disk_io.read_count,
            "write_count": disk_io.write_count,
        } if disk_io else None
    except:
        disk_io_dict = None
    
    # Disk partitions
    partitions = []
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            partitions.append({
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent": usage.percent
            })
        except PermissionError:
            continue
    
    # Network I/O per interface
    net_io = psutil.net_io_counters(pernic=True)
    network_interfaces = {}
    for iface, stats in net_io.items():
        network_interfaces[iface] = {
            "bytes_sent": stats.bytes_sent,
            "bytes_recv": stats.bytes_recv,
            "packets_sent": stats.packets_sent,
            "packets_recv": stats.packets_recv,
            "errin": stats.errin,
            "errout": stats.errout,
            "dropin": stats.dropin,
            "dropout": stats.dropout
        }
    
    # System uptime
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time
    
    # Process count
    process_count = len(psutil.pids())
    
    return {
        "cpu": {
            "per_core": cpu_percent_per_core,
            "total": psutil.cpu_percent(),
            "frequency": {
                "current": cpu_freq.current if cpu_freq else 0,
                "min": cpu_freq.min if cpu_freq else 0,
                "max": cpu_freq.max if cpu_freq else 0
            } if cpu_freq else None,
            "load_average": {
                "1min": round(load_avg[0], 2),
                "5min": round(load_avg[1], 2),
                "15min": round(load_avg[2], 2)
            },
            "count": psutil.cpu_count(),
            "count_logical": psutil.cpu_count(logical=True)
        },
        "memory": {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "free": mem.free,
            "percent": mem.percent,
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "free_gb": round(mem.free / (1024**3), 2)
        },
        "swap": {
            "total": swap.total,
            "used": swap.used,
            "free": swap.free,
            "percent": swap.percent,
            "total_gb": round(swap.total / (1024**3), 2),
            "used_gb": round(swap.used / (1024**3), 2),
            "free_gb": round(swap.free / (1024**3), 2)
        },
        "disk_io": disk_io_dict,
        "partitions": partitions,
        "network": network_interfaces,
        "uptime_seconds": uptime_seconds,
        "uptime_days": round(uptime_seconds / 86400, 1),
        "process_count": process_count,
        "timestamp": datetime.utcnow().isoformat()
    }


# Global speed monitor for tracking network speed
class SpeedMonitor:
    def __init__(self):
        self.last_check = {}
        
    def get_current_speed(self, interface='all'):
        """Calculate current network speed in bytes/sec"""
        import psutil
        import time
        
        try:
            if interface == 'all':
                current = psutil.net_io_counters()
            else:
                net_io_dict = psutil.net_io_counters(pernic=True)
                current = net_io_dict.get(interface)
                if not current:
                    return {"upload_mbps": 0, "download_mbps": 0, "total_mbps": 0}
            
            current_time = time.time()
            
            if interface in self.last_check:
                last_stats, last_time = self.last_check[interface]
                time_delta = current_time - last_time
                
                if time_delta > 0:
                    upload_speed = (current.bytes_sent - last_stats.bytes_sent) / time_delta
                    download_speed = (current.bytes_recv - last_stats.bytes_recv) / time_delta
                else:
                    upload_speed = download_speed = 0
            else:
                upload_speed = download_speed = 0
                
            self.last_check[interface] = (current, current_time)
            
            return {
                "upload_bps": int(upload_speed),
                "download_bps": int(download_speed),
                "upload_mbps": round(upload_speed * 8 / (1024**2), 2),
                "download_mbps": round(download_speed * 8 / (1024**2), 2),
                "total_mbps": round((upload_speed + download_speed) * 8 / (1024**2), 2)
            }
        except Exception as e:
            return {"upload_mbps": 0, "download_mbps": 0, "total_mbps": 0, "error": str(e)}


speed_monitor = SpeedMonitor()


@router.get("/network-speed")
async def get_network_speed(
    current_admin: User = Depends(get_current_admin)
):
    """Get real-time network speed for different interfaces"""
    import psutil
    
    # Get all network interfaces
    net_io = psutil.net_io_counters(pernic=True)
    
    # Try to identify main interface and tunnel interface
    main_interface = None
    tunnel_interface = None
    
    for iface in net_io.keys():
        if 'tun' in iface.lower() or 'tap' in iface.lower():
            tunnel_interface = iface
        elif 'eth' in iface.lower() or 'en' in iface.lower() or 'wlan' in iface.lower():
            if not main_interface:
                main_interface = iface
    
    # Get speeds
    total_speed = speed_monitor.get_current_speed('all')
    main_speed = speed_monitor.get_current_speed(main_interface) if main_interface else {"upload_mbps": 0, "download_mbps": 0, "total_mbps": 0}
    tunnel_speed = speed_monitor.get_current_speed(tunnel_interface) if tunnel_interface else {"upload_mbps": 0, "download_mbps": 0, "total_mbps": 0}
    
    return {
        "client_server": {
            "interface": main_interface,
            **main_speed
        },
        "tunnel": {
            "interface": tunnel_interface,
            **tunnel_speed
        },
        "total": total_speed,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/traffic-by-type")
async def get_traffic_by_type(
    days: int = 7,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get traffic statistics separated by type (direct vs tunnel)"""
    try:
        from ..models.user import TrafficType
        from sqlalchemy import cast, Date
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Direct traffic
        direct_traffic = db.query(
            func.sum(TrafficLog.upload_bytes + TrafficLog.download_bytes)
        ).filter(
            TrafficLog.traffic_type == TrafficType.DIRECT,
            TrafficLog.recorded_at >= start_date
        ).scalar() or 0
        
        # Tunnel traffic
        tunnel_traffic = db.query(
            func.sum(TrafficLog.upload_bytes + TrafficLog.download_bytes)
        ).filter(
            TrafficLog.traffic_type == TrafficType.TUNNEL,
            TrafficLog.recorded_at >= start_date
        ).scalar() or 0
        
        # Daily breakdown using SQLite-compatible func.date()
        daily_direct = db.query(
            func.date(TrafficLog.recorded_at).label('date'),
            func.sum(TrafficLog.upload_bytes).label('upload'),
            func.sum(TrafficLog.download_bytes).label('download')
        ).filter(
            TrafficLog.traffic_type == TrafficType.DIRECT,
            TrafficLog.recorded_at >= start_date
        ).group_by(
            func.date(TrafficLog.recorded_at)
        ).all()
        
        daily_tunnel = db.query(
            func.date(TrafficLog.recorded_at).label('date'),
            func.sum(TrafficLog.upload_bytes).label('upload'),
            func.sum(TrafficLog.download_bytes).label('download')
        ).filter(
            TrafficLog.traffic_type == TrafficType.TUNNEL,
            TrafficLog.recorded_at >= start_date
        ).group_by(
            func.date(TrafficLog.recorded_at)
        ).all()
        
        # Combine daily data
        daily_combined = {}
        for day in daily_direct:
            date_str = day.date if isinstance(day.date, str) else str(day.date)
            daily_combined[date_str] = {
                "date": date_str,
                "direct_gb": round(((day.upload or 0) + (day.download or 0)) / (1024**3), 2),
                "tunnel_gb": 0
            }
        
        for day in daily_tunnel:
            date_str = day.date if isinstance(day.date, str) else str(day.date)
            if date_str in daily_combined:
                daily_combined[date_str]["tunnel_gb"] = round(((day.upload or 0) + (day.download or 0)) / (1024**3), 2)
            else:
                daily_combined[date_str] = {
                    "date": date_str,
                    "direct_gb": 0,
                    "tunnel_gb": round(((day.upload or 0) + (day.download or 0)) / (1024**3), 2)
                }
        
        return {
            "summary": {
                "direct": {
                    "bytes": direct_traffic,
                    "gb": round(direct_traffic / (1024**3), 2)
                },
                "tunnel": {
                    "bytes": tunnel_traffic,
                    "gb": round(tunnel_traffic / (1024**3), 2)
                },
                "total": {
                    "bytes": direct_traffic + tunnel_traffic,
                    "gb": round((direct_traffic + tunnel_traffic) / (1024**3), 2)
                }
            },
            "daily": list(daily_combined.values())
        }
    except Exception as e:
        # If traffic_type column doesn't exist or has issues, return empty data
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error in traffic-by-type endpoint: {e}")
        
        # Return empty but valid structure
        return {
            "summary": {
                "direct": {"bytes": 0, "gb": 0},
                "tunnel": {"bytes": 0, "gb": 0},
                "total": {"bytes": 0, "gb": 0}
            },
            "daily": []
        }


@router.get("/protocol-distribution")
async def get_protocol_distribution(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get distribution of active users by VPN protocol"""
    openvpn_count = db.query(ConnectionLog).filter(
        ConnectionLog.is_active == True,
        ConnectionLog.protocol == "openvpn"
    ).count()
    
    wireguard_count = db.query(ConnectionLog).filter(
        ConnectionLog.is_active == True,
        ConnectionLog.protocol == "wireguard"
    ).count()
    
    return {
        "openvpn": openvpn_count,
        "wireguard": wireguard_count,
        "total": openvpn_count + wireguard_count
    }
