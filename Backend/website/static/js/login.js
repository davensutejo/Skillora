// Login Page JavaScript

document.addEventListener('DOMContentLoaded', () => {
    // Initialize parallax elements for login page
    createLoginParallaxElements();
    
    // Setup password toggle
    setupPasswordToggle();
    
    // Setup form validation
    setupFormValidation();
    
    // Setup form submit handler
    setupFormSubmit();
    
    // Remove the blob effects
    // enhanceBlobEffects();  <-- Comment out or remove this line
    
    // New function
    createBackgroundParticles();
});

// Create parallax elements for the login page
function createLoginParallaxElements() {
    const parallaxWrapper = document.querySelector('.login-parallax');
    if (!parallaxWrapper) return;
    
    // Create dots
    for (let i = 0; i < 30; i++) {
        const dot = document.createElement('div');
        dot.className = 'parallax-dot';
        
        // Random size (smaller than main page for subtlety)
        const size = Math.random() * 4 + 1;
        dot.style.width = `${size}px`;
        dot.style.height = `${size}px`;
        
        // Random position
        dot.style.left = `${Math.random() * 100}%`;
        dot.style.top = `${Math.random() * 100}%`;
        
        // Random opacity
        dot.style.opacity = Math.random() * 0.5 + 0.1;
        
        // Add animation delay
        dot.style.animationDelay = `${Math.random() * 2}s`;
        
        // Add floating animation
        dot.style.animation = `float ${Math.random() * 4 + 6}s ease-in-out infinite`;
        
        parallaxWrapper.appendChild(dot);
    }
    
    // Create lines
    for (let i = 0; i < 15; i++) {
        const line = document.createElement('div');
        line.className = 'parallax-line';
        
        // Random width
        line.style.width = `${Math.random() * 150 + 50}px`;
        
        // Random position
        line.style.left = `${Math.random() * 100}%`;
        line.style.top = `${Math.random() * 100}%`;
        
        // Random rotation
        line.style.transform = `rotate(${Math.random() * 360}deg)`;
        
        // Random opacity
        line.style.opacity = Math.random() * 0.3 + 0.05;
        
        parallaxWrapper.appendChild(line);
    }
    
    // Create circles
    for (let i = 0; i < 10; i++) {
        const circle = document.createElement('div');
        circle.className = 'parallax-circle';
        
        // Random size
        const size = Math.random() * 100 + 30;
        circle.style.width = `${size}px`;
        circle.style.height = `${size}px`;
        
        // Random position
        circle.style.left = `${Math.random() * 100}%`;
        circle.style.top = `${Math.random() * 100}%`;
        
        // Random opacity
        circle.style.opacity = Math.random() * 0.2 + 0.05;
        
        // Add pulse animation with random delay
        circle.style.animation = `pulse ${Math.random() * 4 + 8}s ease-in-out infinite ${Math.random() * 2}s`;
        
        parallaxWrapper.appendChild(circle);
    }
}

// Remove or comment out the entire enhanceBlobEffects function
/*
function enhanceBlobEffects() {
    // All code inside this function is removed or commented out
}
*/

// Setup password toggle functionality
function setupPasswordToggle() {
    const togglePassword = document.querySelector('.toggle-password');
    const passwordInput = document.querySelector('#password');
    
    if (!togglePassword || !passwordInput) return;
    
    togglePassword.addEventListener('click', () => {
        // Toggle password visibility
        const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordInput.setAttribute('type', type);
        
        // Toggle eye icon
        togglePassword.classList.toggle('fa-eye');
        togglePassword.classList.toggle('fa-eye-slash');
        
        // Add visual feedback
        togglePassword.style.color = '#5D3FD3';
        setTimeout(() => {
            togglePassword.style.color = '';
        }, 300);
    });
}

// Form validation
function setupFormValidation() {
    const emailInput = document.querySelector('#email');
    const passwordInput = document.querySelector('#password');
    
    if (!emailInput || !passwordInput) return;
    
    // Simple email validation
    emailInput.addEventListener('blur', () => {
        const email = emailInput.value.trim();
        if (email === '') return;
        
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            showInputError(emailInput, 'Please enter a valid email address');
        } else {
            clearInputError(emailInput);
        }
    });
    
    // Password validation (at least 6 characters)
    passwordInput.addEventListener('blur', () => {
        const password = passwordInput.value.trim();
        if (password === '') return;
        
        if (password.length < 6) {
            showInputError(passwordInput, 'Password must be at least 6 characters');
        } else {
            clearInputError(passwordInput);
        }
    });
}

// Show error message for an input
function showInputError(inputElement, message) {
    // Remove any existing error message
    clearInputError(inputElement);
    
    // Add error class to input
    inputElement.classList.add('error');
    inputElement.style.borderColor = '#ff4040';
    
    // Create and append error message
    const errorElement = document.createElement('div');
    errorElement.className = 'input-error';
    errorElement.textContent = message;
    errorElement.style.color = '#ff4040';
    errorElement.style.fontSize = '0.8rem';
    errorElement.style.marginTop = '5px';
    errorElement.style.animation = 'fadeIn 0.3s ease forwards';
    
    inputElement.parentElement.appendChild(errorElement);
}

// Clear error message for an input
function clearInputError(inputElement) {
    inputElement.classList.remove('error');
    inputElement.style.borderColor = '';
    
    const errorElement = inputElement.parentElement.querySelector('.input-error');
    if (errorElement) {
        errorElement.remove();
    }
}

// Form submit handler
function setupFormSubmit() {
    const loginForm = document.querySelector('.login-form');
    
    if (!loginForm) return;
    
    loginForm.addEventListener('submit', (e) => {
        // Get form data
        const email = document.querySelector('#email').value.trim();
        const password = document.querySelector('#password').value.trim();
        const remember = document.querySelector('#remember')?.checked || false;
        
        // Validate form data
        let isValid = true;
        
        if (!email) {
            e.preventDefault(); // Only prevent default if validation fails
            showInputError(document.querySelector('#email'), 'Email is required');
            isValid = false;
        }
        
        if (!password) {
            e.preventDefault(); // Only prevent default if validation fails
            showInputError(document.querySelector('#password'), 'Password is required');
            isValid = false;
        }
        
        if (isValid) {
            // Add login animation effect - make blobs pulse
            const bgBlobs = document.querySelectorAll('.bg-blob');
            bgBlobs.forEach(blob => {
                blob.style.transition = 'all 0.5s ease';
                blob.style.filter = 'blur(300px)'; // Extremely blurry during login animation
                blob.style.opacity = '0.8';
                blob.style.transform = 'scale(1.1)';
            });
            
            // Show loading state
            const loginBtn = document.querySelector('.login-btn');
            const loginBtnText = loginBtn.querySelector('span');
            const loginBtnIcon = loginBtn.querySelector('i');
            
            loginBtnText.textContent = 'Logging in...';
            loginBtnIcon.className = 'fas fa-spinner fa-spin';
            
            // Let the form submit naturally - don't prevent default if valid
        }
    });
}

// Add this new function to create animated particles in the background
function createBackgroundParticles() {
    const container = document.createElement('div');
    container.className = 'particles-container';
    container.style.position = 'fixed';
    container.style.top = '0';
    container.style.left = '0';
    container.style.width = '100%';
    container.style.height = '100%';
    container.style.pointerEvents = 'none';
    container.style.zIndex = '1';
    document.body.appendChild(container);
    
    // Create 50 particles
    for (let i = 0; i < 50; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        
        // Style the particle
        particle.style.position = 'absolute';
        particle.style.width = `${Math.random() * 3 + 1}px`;
        particle.style.height = `${Math.random() * 3 + 1}px`;
        particle.style.background = `rgba(${123 + Math.random() * 50}, ${95 + Math.random() * 30}, 255, ${0.2 + Math.random() * 0.3})`;
        particle.style.borderRadius = '50%';
        particle.style.boxShadow = '0 0 10px rgba(123, 95, 255, 0.5)';
        
        // Position randomly
        particle.style.left = `${Math.random() * 100}vw`;
        particle.style.top = `${Math.random() * 100}vh`;
        
        // Add animation
        const duration = 10 + Math.random() * 20;
        particle.style.animation = `floatParticle ${duration}s linear infinite`;
        particle.style.animationDelay = `-${Math.random() * duration}s`;
        
        container.appendChild(particle);
    }
    
    // Add animation keyframes
    const style = document.createElement('style');
    style.textContent = `
        @keyframes floatParticle {
            0% { transform: translateY(0) rotate(0deg); opacity: 0; }
            10% { opacity: 1; }
            90% { opacity: 1; }
            100% { transform: translateY(-100vh) rotate(360deg); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
} 