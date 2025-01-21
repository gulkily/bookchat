// Theme management
function getPreferredTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        return savedTheme;
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme) {
    const body = document.body;
    body.classList.remove('dark-theme', 'light-theme');
    body.classList.add(`${theme}-theme`);
    localStorage.setItem('theme', theme);
    const themeToggleText = document.getElementById('theme-toggle-text');
    if (themeToggleText) {
        themeToggleText.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
}

// Initialize theme
document.addEventListener('DOMContentLoaded', () => {
    applyTheme(getPreferredTheme());

    // Theme toggle click handler
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const isDarkTheme = document.body.classList.contains('dark-theme');
            const newTheme = isDarkTheme ? 'light' : 'dark';
            applyTheme(newTheme);
        });
    }

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            applyTheme(e.matches ? 'dark' : 'light');
        }
    });
});
