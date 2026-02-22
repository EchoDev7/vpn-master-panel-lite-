import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Check, X, Loader2, CreditCard, Calendar, Database, Users } from 'lucide-react';

const SubscriptionPlans = () => {
    const [plans, setPlans] = useState([]);
    const [currentSubscription, setCurrentSubscription] = useState(null);
    const [loading, setLoading] = useState(true);
    const [subscribing, setSubscribing] = useState(null);

    useEffect(() => {
        fetchPlans();
        fetchCurrentSubscription();
    }, []);

    const fetchPlans = async () => {
        try {
            const response = await axios.get('/api/v1/subscription-plans');
            setPlans(response.data.plans);
        } catch (error) {
            console.error('Error fetching plans:', error);
        }
    };

    const fetchCurrentSubscription = async () => {
        try {
            const response = await axios.get('/api/v1/my-subscription');
            setCurrentSubscription(response.data.subscription);
        } catch (error) {
            console.error('Error fetching subscription:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSubscribe = async (planId) => {
        setSubscribing(planId);
        try {
            const response = await axios.post(`/api/v1/subscribe/${planId}`);
            alert(response.data.message);
            fetchCurrentSubscription();
        } catch (error) {
            alert(error.response?.data?.detail || 'Failed to subscribe');
        } finally {
            setSubscribing(null);
        }
    };

    const handleCancelSubscription = async () => {
        if (!confirm('Are you sure you want to cancel your subscription?')) return;

        try {
            const response = await axios.post('/api/v1/cancel-subscription');
            alert(response.data.message);
            fetchCurrentSubscription();
        } catch (error) {
            alert(error.response?.data?.detail || 'Failed to cancel subscription');
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            </div>
        );
    }

    return (
        <div className="max-w-7xl mx-auto px-4 py-8">
            <div className="text-center mb-12">
                <h1 className="text-4xl font-bold mb-4">Choose Your Plan</h1>
                <p className="text-gray-600 dark:text-gray-400">
                    Select the perfect plan for your VPN needs
                </p>
            </div>

            {/* Current Subscription */}
            {currentSubscription && (
                <div className="mb-8 p-6 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-lg font-semibold mb-2">Current Subscription: {currentSubscription.plan_name}</h3>
                            <div className="flex gap-4 text-sm text-gray-600 dark:text-gray-400">
                                <span>📅 Expires: {new Date(currentSubscription.end_date).toLocaleDateString()}</span>
                                <span>⏰ {currentSubscription.days_remaining} days remaining</span>
                                <span>📊 {currentSubscription.usage_percent}% used</span>
                            </div>
                        </div>
                        <button
                            onClick={handleCancelSubscription}
                            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                        >
                            Cancel Subscription
                        </button>
                    </div>
                </div>
            )}

            {/* Subscription Plans */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {plans.map((plan) => (
                    <div
                        key={plan.id}
                        className={`relative p-6 rounded-2xl border-2 transition-all ${plan.name === 'Pro'
                                ? 'border-blue-600 shadow-xl scale-105'
                                : 'border-gray-200 dark:border-gray-700 hover:border-blue-400'
                            }`}
                    >
                        {plan.name === 'Pro' && (
                            <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                                <span className="bg-blue-600 text-white px-4 py-1 rounded-full text-sm font-semibold">
                                    Most Popular
                                </span>
                            </div>
                        )}

                        <div className="text-center mb-6">
                            <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
                            <div className="text-4xl font-bold mb-2">
                                ${plan.price}
                                <span className="text-lg text-gray-500">/mo</span>
                            </div>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                {plan.description}
                            </p>
                        </div>

                        <div className="space-y-3 mb-6">
                            <div className="flex items-center gap-2">
                                <Database className="w-5 h-5 text-blue-600" />
                                <span className="text-sm">
                                    {plan.traffic_limit_gb === 0 ? 'Unlimited' : `${plan.traffic_limit_gb}GB`} Traffic
                                </span>
                            </div>
                            <div className="flex items-center gap-2">
                                <Users className="w-5 h-5 text-blue-600" />
                                <span className="text-sm">
                                    {plan.connection_limit === 0 ? 'Unlimited' : plan.connection_limit} Connections
                                </span>
                            </div>
                            <div className="flex items-center gap-2">
                                <Calendar className="w-5 h-5 text-blue-600" />
                                <span className="text-sm">{plan.duration_days} Days</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <Check className="w-5 h-5 text-green-600" />
                                <span className="text-sm">All Protocols</span>
                            </div>
                        </div>

                        <button
                            onClick={() => handleSubscribe(plan.id)}
                            disabled={subscribing === plan.id || (currentSubscription && currentSubscription.plan_name === plan.name)}
                            className={`w-full py-3 rounded-lg font-semibold transition-colors ${currentSubscription && currentSubscription.plan_name === plan.name
                                    ? 'bg-gray-300 dark:bg-gray-700 cursor-not-allowed'
                                    : plan.name === 'Pro'
                                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                                        : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                                }`}
                        >
                            {subscribing === plan.id ? (
                                <Loader2 className="w-5 h-5 animate-spin mx-auto" />
                            ) : currentSubscription && currentSubscription.plan_name === plan.name ? (
                                'Current Plan'
                            ) : (
                                'Subscribe'
                            )}
                        </button>
                    </div>
                ))}
            </div>

            {/* Features Comparison */}
            <div className="mt-16">
                <h2 className="text-2xl font-bold text-center mb-8">Compare Features</h2>
                <div className="overflow-x-auto">
                    <table className="w-full border-collapse">
                        <thead>
                            <tr className="border-b-2 border-gray-200 dark:border-gray-700">
                                <th className="p-4 text-left">Feature</th>
                                {plans.map((plan) => (
                                    <th key={plan.id} className="p-4 text-center">{plan.name}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            <tr className="border-b border-gray-200 dark:border-gray-700">
                                <td className="p-4">Monthly Traffic</td>
                                {plans.map((plan) => (
                                    <td key={plan.id} className="p-4 text-center">
                                        {plan.traffic_limit_gb === 0 ? '∞' : `${plan.traffic_limit_gb}GB`}
                                    </td>
                                ))}
                            </tr>
                            <tr className="border-b border-gray-200 dark:border-gray-700">
                                <td className="p-4">Simultaneous Connections</td>
                                {plans.map((plan) => (
                                    <td key={plan.id} className="p-4 text-center">
                                        {plan.connection_limit === 0 ? '∞' : plan.connection_limit}
                                    </td>
                                ))}
                            </tr>
                            <tr className="border-b border-gray-200 dark:border-gray-700">
                                <td className="p-4">Max Devices</td>
                                {plans.map((plan) => (
                                    <td key={plan.id} className="p-4 text-center">
                                        {plan.max_devices === 0 ? '∞' : plan.max_devices}
                                    </td>
                                ))}
                            </tr>
                            <tr className="border-b border-gray-200 dark:border-gray-700">
                                <td className="p-4">All Protocols</td>
                                {plans.map((plan) => (
                                    <td key={plan.id} className="p-4 text-center">
                                        <Check className="w-5 h-5 text-green-600 mx-auto" />
                                    </td>
                                ))}
                            </tr>
                            <tr>
                                <td className="p-4">24/7 Support</td>
                                {plans.map((plan) => (
                                    <td key={plan.id} className="p-4 text-center">
                                        {plan.price > 0 ? (
                                            <Check className="w-5 h-5 text-green-600 mx-auto" />
                                        ) : (
                                            <X className="w-5 h-5 text-red-600 mx-auto" />
                                        )}
                                    </td>
                                ))}
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default SubscriptionPlans;
