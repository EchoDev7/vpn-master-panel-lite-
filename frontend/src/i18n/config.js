/**
 * i18n Configuration
 * Multi-language support with RTL
 */
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import translations
import en from './locales/en.json';
import fa from './locales/fa.json';

// RTL languages
const RTL_LANGUAGES = ['fa', 'ar'];

i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
        resources: {
            en: { translation: en },
            fa: { translation: fa }
        },
        fallbackLng: 'en',
        debug: false,
        interpolation: {
            escapeValue: false
        },
        detection: {
            order: ['localStorage', 'navigator'],
            caches: ['localStorage']
        }
    });

// Set document direction based on language
i18n.on('languageChanged', (lng) => {
    const dir = RTL_LANGUAGES.includes(lng) ? 'rtl' : 'ltr';
    document.documentElement.dir = dir;
    document.documentElement.lang = lng;
});

// Set initial direction
const currentLang = i18n.language;
const initialDir = RTL_LANGUAGES.includes(currentLang) ? 'rtl' : 'ltr';
document.documentElement.dir = initialDir;
document.documentElement.lang = currentLang;

export default i18n;
