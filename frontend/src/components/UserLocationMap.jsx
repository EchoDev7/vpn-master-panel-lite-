import React, { useState, useEffect } from 'react';
import { ComposableMap, Geographies, Geography, Marker, ZoomableGroup } from 'react-simple-maps';
import { MapPin, Users as UsersIcon, RefreshCw } from 'lucide-react';
import apiService from '../services/api';

const geoUrl = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

const UserLocationMap = () => {
    const [locations, setLocations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [hoveredLocation, setHoveredLocation] = useState(null);

    useEffect(() => {
        loadLocations();
        const interval = setInterval(loadLocations, 60000); // Refresh every minute
        return () => clearInterval(interval);
    }, []);

    const loadLocations = async () => {
        try {
            setLoading(true);
            const response = await apiService.get('/monitoring/user-locations');
            setLocations(response.data || []);
            setLoading(false);
        } catch (error) {
            console.error('Failed to load locations:', error);
            // Mock data for demonstration
            setLocations(getMockLocations());
            setLoading(false);
        }
    };

    const getMockLocations = () => [
        { id: 1, country: 'Iran', city: 'Tehran', lat: 35.6892, lon: 51.3890, users: 45, coordinates: [51.3890, 35.6892] },
        { id: 2, country: 'Germany', city: 'Frankfurt', lat: 50.1109, lon: 8.6821, users: 23, coordinates: [8.6821, 50.1109] },
        { id: 3, country: 'USA', city: 'New York', lat: 40.7128, lon: -74.0060, users: 18, coordinates: [-74.0060, 40.7128] },
        { id: 4, country: 'UK', city: 'London', lat: 51.5074, lon: -0.1278, users: 12, coordinates: [-0.1278, 51.5074] },
        { id: 5, country: 'Netherlands', city: 'Amsterdam', lat: 52.3676, lon: 4.9041, users: 8, coordinates: [4.9041, 52.3676] }
    ];

    const getMarkerSize = (userCount) => {
        if (userCount > 30) return 12;
        if (userCount > 15) return 10;
        if (userCount > 5) return 8;
        return 6;
    };

    const getMarkerColor = (userCount) => {
        if (userCount > 30) return '#ef4444'; // Red
        if (userCount > 15) return '#f59e0b'; // Orange
        if (userCount > 5) return '#3b82f6';  // Blue
        return '#10b981'; // Green
    };

    if (loading) {
        return (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 animate-pulse">
                <div className="h-6 bg-gray-300 dark:bg-gray-700 rounded w-48 mb-4"></div>
                <div className="h-96 bg-gray-300 dark:bg-gray-700 rounded"></div>
            </div>
        );
    }

    const totalUsers = locations.reduce((sum, loc) => sum + loc.users, 0);

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-4">
                <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                        <MapPin className="text-blue-500" size={20} />
                        User Locations
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        {totalUsers} active users across {locations.length} locations
                    </p>
                </div>
                <button
                    onClick={loadLocations}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    title="Refresh"
                >
                    <RefreshCw size={16} className="text-gray-600 dark:text-gray-400" />
                </button>
            </div>

            {/* Map */}
            <div className="relative bg-gray-50 dark:bg-gray-900 rounded-lg overflow-hidden" style={{ height: 400 }}>
                <ComposableMap
                    projection="geoMercator"
                    projectionConfig={{
                        scale: 147
                    }}
                >
                    <ZoomableGroup>
                        <Geographies geography={geoUrl}>
                            {({ geographies }) =>
                                geographies.map((geo) => (
                                    <Geography
                                        key={geo.rsmKey}
                                        geography={geo}
                                        fill="#d1d5db"
                                        stroke="#9ca3af"
                                        strokeWidth={0.5}
                                        style={{
                                            default: { outline: 'none' },
                                            hover: { fill: '#9ca3af', outline: 'none' },
                                            pressed: { outline: 'none' }
                                        }}
                                    />
                                ))
                            }
                        </Geographies>

                        {/* Markers */}
                        {locations.map((location) => (
                            <Marker
                                key={location.id}
                                coordinates={location.coordinates}
                                onMouseEnter={() => setHoveredLocation(location)}
                                onMouseLeave={() => setHoveredLocation(null)}
                            >
                                <circle
                                    r={getMarkerSize(location.users)}
                                    fill={getMarkerColor(location.users)}
                                    stroke="#fff"
                                    strokeWidth={2}
                                    style={{
                                        cursor: 'pointer',
                                        opacity: hoveredLocation?.id === location.id ? 1 : 0.8
                                    }}
                                />
                            </Marker>
                        ))}
                    </ZoomableGroup>
                </ComposableMap>

                {/* Tooltip */}
                {hoveredLocation && (
                    <div className="absolute top-4 left-4 bg-gray-900 text-white px-4 py-3 rounded-lg shadow-xl z-10">
                        <p className="font-semibold">{hoveredLocation.city}, {hoveredLocation.country}</p>
                        <p className="text-sm flex items-center gap-1 mt-1">
                            <UsersIcon size={14} />
                            {hoveredLocation.users} active users
                        </p>
                    </div>
                )}
            </div>

            {/* Legend */}
            <div className="mt-4 flex items-center justify-center gap-6 text-sm">
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span className="text-gray-600 dark:text-gray-400">1-5 users</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                    <span className="text-gray-600 dark:text-gray-400">6-15 users</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                    <span className="text-gray-600 dark:text-gray-400">16-30 users</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <span className="text-gray-600 dark:text-gray-400">30+ users</span>
                </div>
            </div>

            {/* Location List */}
            <div className="mt-6 space-y-2">
                {locations.map((location) => (
                    <div
                        key={location.id}
                        className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                    >
                        <div className="flex items-center gap-3">
                            <div
                                className="w-2 h-2 rounded-full"
                                style={{ backgroundColor: getMarkerColor(location.users) }}
                            ></div>
                            <div>
                                <p className="font-medium text-gray-900 dark:text-white">
                                    {location.city}, {location.country}
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                    {location.lat.toFixed(4)}, {location.lon.toFixed(4)}
                                </p>
                            </div>
                        </div>
                        <div className="text-right">
                            <p className="font-semibold text-gray-900 dark:text-white">{location.users}</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">users</p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default UserLocationMap;
