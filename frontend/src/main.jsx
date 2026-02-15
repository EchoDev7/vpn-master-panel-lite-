import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

console.log('Starting app...');
try {
    const root = ReactDOM.createRoot(document.getElementById('root'));
    console.log('Root created, rendering app...');
    root.render(
        <React.StrictMode>
            <App />
        </React.StrictMode>,
    );
    console.log('App rendered');
} catch (error) {
    console.error('Error mounting app:', error);
    document.body.innerHTML = '<div style="color: red; padding: 20px;"><h1>App Crash</h1><pre>' + error.toString() + '</pre></div>';
}
