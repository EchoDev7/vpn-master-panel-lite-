import React from 'react';
import { Info } from 'lucide-react';

// Tooltip component
export const Tip = ({ text }) => (
    <div className="group relative inline-block ml-1">
        <Info className="w-3.5 h-3.5 text-gray-500 cursor-help inline" />
        <div className="absolute z-50 invisible group-hover:visible bg-gray-900 text-gray-200 text-xs rounded-lg p-2 w-64 bottom-full left-1/2 -translate-x-1/2 mb-1 border border-gray-600 shadow-xl">
            {text}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
        </div>
    </div>
);

// Iran recommended badge
export const IranBadge = () => (
    <span className="ml-2 text-[10px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">
        🇮🇷 Iran
    </span>
);

// Section title
export const SectionTitle = ({ children }) => (
    <h3 className="text-gray-300 font-bold mb-3 text-sm uppercase tracking-wider border-b border-gray-700 pb-2">
        {children}
    </h3>
);

// Input field - defined OUTSIDE Settings component to prevent remounting
export const InputField = ({ label, value, onChange, placeholder, type = "text", tip, iranBadge, mono }) => (
    <div>
        <label className="block text-gray-400 text-sm mb-1">
            {label}
            {tip && <Tip text={tip} />}
            {iranBadge && <IranBadge />}
        </label>
        <input
            type={type}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className={`w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white text-sm focus:border-blue-500 focus:outline-none ${mono ? 'font-mono text-xs' : ''}`}
        />
    </div>
);

// Select field
export const SelectField = ({ label, value, onChange, options, tip, iranBadge }) => (
    <div>
        <label className="block text-gray-400 text-sm mb-1">
            {label}
            {tip && <Tip text={tip} />}
            {iranBadge && <IranBadge />}
        </label>
        <select
            value={value || options[0]?.value || ''}
            onChange={(e) => onChange(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white text-sm focus:border-blue-500 focus:outline-none"
        >
            {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
    </div>
);

// Checkbox field
export const CheckboxField = ({ label, id, checked, onChange, tip, iranBadge }) => (
    <div className="flex items-center gap-3 bg-gray-700/50 p-3 rounded-lg">
        <input
            type="checkbox"
            id={id}
            checked={checked}
            onChange={(e) => onChange(e.target.checked)}
            className="w-5 h-5 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500"
        />
        <label htmlFor={id} className="text-gray-200 font-medium text-sm cursor-pointer">
            {label}
            {tip && <Tip text={tip} />}
            {iranBadge && <IranBadge />}
        </label>
    </div>
);

// Textarea field
export const TextareaField = ({ label, value, onChange, placeholder, tip, rows = 4 }) => (
    <div>
        <label className="block text-gray-400 text-sm mb-1">
            {label}
            {tip && <Tip text={tip} />}
        </label>
        <textarea
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            rows={rows}
            className="w-full bg-gray-900 border border-gray-600 rounded-lg p-3 text-gray-300 font-mono text-xs resize-none focus:border-blue-500 focus:outline-none"
        />
    </div>
);
