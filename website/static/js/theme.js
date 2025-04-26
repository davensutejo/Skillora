/**
 * Theme handling for Skillora Learning Platform
 */

document.addEventListener('DOMContentLoaded', function() {
    // Remove any existing theme toggle UI elements if they exist
    const existingToggles = document.querySelectorAll('#theme-toggle, #theme-toggle-nav, .theme-toggle-container');
    existingToggles.forEach(toggle => {
        if (toggle && toggle.parentNode) {
            toggle.parentNode.removeChild(toggle);
        }
    });
    
    // Remove any dark-mode class from body if it exists
    document.body.classList.remove('dark-mode');
    
    // Clear any stored theme preference
    if (localStorage.getItem('theme')) {
        localStorage.removeItem('theme');
    }
}); 