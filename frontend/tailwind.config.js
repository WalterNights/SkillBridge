const { transform } = require('typescript');

/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: 'class',
    content: [
        "./src/**/*.{html,ts}"
    ],
    theme: {
        extend: {
            colors: {
                primary: '#1a73e8',
                darkBg: '#1c1c1d',
                darkCard: '#252728',
                darkText: '#e5e5e5',
                darkBgTa: '#333334',
                skBg1: '#FCEEB5',
            },
            fontFamily: {
                'timesNR': ['Times New Roman'],
                'nunito': ['Nunito'],
            },
            animation: {
                'fade-in': 'fadeIn 0.5s ease-in-out',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0', transform: 'scale(0.95)' },
                    '100%': { opacity: '1', transform: 'scale(1)' },
                },
            },
        },
    },
    plugins: [],
}