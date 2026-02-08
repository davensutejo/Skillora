/**
 * Theme.js - Handles theme switching and customization
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check for saved theme preference or use default
    const currentTheme = localStorage.getItem('theme') || 'light';
    setTheme(currentTheme);
    
    // Theme toggle functionality if a theme toggle exists
    const themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = document.body.classList.contains('dark-theme') ? 'light' : 'dark';
            setTheme(currentTheme);
        });
    }
    
    // Function to set the theme
    function setTheme(theme) {
        if (theme === 'dark') {
            document.body.classList.add('dark-theme');
            document.body.classList.remove('light-theme');
            localStorage.setItem('theme', 'dark');
        } else {
            document.body.classList.add('light-theme');
            document.body.classList.remove('dark-theme');
            localStorage.setItem('theme', 'light');
        }
    }
}); 