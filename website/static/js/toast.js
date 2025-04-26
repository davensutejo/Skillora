/**
 * Toast Notification System for Skillora
 * Handles displaying various notification types to users
 */

// Function to show a toast notification
function showToast(message, category = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${category}`;
    
    let iconClass = 'info-circle';
    if (category === 'success') {
        iconClass = 'check-circle';
    } else if (category === 'error') {
        iconClass = 'exclamation-circle';
    } else if (category === 'warning') {
        iconClass = 'exclamation-triangle';
    }
    
    toast.innerHTML = `
        <div class="toast-content">
            <i class="fas fa-${iconClass}"></i>
            <span>${message}</span>
        </div>
        <button class="toast-close">&times;</button>
    `;
    
    const container = document.getElementById('toast-container');
    if (container) {
        container.appendChild(toast);
    } else {
        // Create container if it doesn't exist
        const newContainer = document.createElement('div');
        newContainer.id = 'toast-container';
        newContainer.className = 'toast-container';
        document.body.appendChild(newContainer);
        newContainer.appendChild(toast);
    }
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        toast.classList.add('toast-hiding');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 5000);
    
    // Close button functionality
    toast.querySelector('.toast-close').addEventListener('click', function() {
        toast.classList.add('toast-hiding');
        setTimeout(() => {
            toast.remove();
        }, 300);
    });
} 