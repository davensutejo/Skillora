/**
 * Skillora Responsive Script
 * Contains functionality to enhance mobile responsiveness across all pages
 */

document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle with overlay
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    const menuOverlay = document.querySelector('.menu-overlay');
    const body = document.body;
    
    if (mobileMenuToggle && sidebar && menuOverlay) {
        mobileMenuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
            menuOverlay.classList.toggle('active');
            body.classList.toggle('menu-open');
            
            // Change icon based on menu state
            const icon = this.querySelector('i');
            if (sidebar.classList.contains('active')) {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-times');
            } else {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        });
        
        // Close menu when overlay is clicked
        menuOverlay.addEventListener('click', function() {
            sidebar.classList.remove('active');
            menuOverlay.classList.remove('active');
            body.classList.remove('menu-open');
            
            const icon = mobileMenuToggle.querySelector('i');
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
        });
        
        // Close menu when a menu item is clicked
        const menuItems = document.querySelectorAll('.sidebar .menu-item');
        menuItems.forEach(item => {
            item.addEventListener('click', function() {
                if (window.innerWidth < 992) {
                    sidebar.classList.remove('active');
                    menuOverlay.classList.remove('active');
                    body.classList.remove('menu-open');
                    
                    const icon = mobileMenuToggle.querySelector('i');
                    icon.classList.remove('fa-times');
                    icon.classList.add('fa-bars');
                }
            });
        });
    }
    
    // Responsive charts resizing
    function resizeCharts() {
        if (typeof Chart !== 'undefined') {
            Chart.helpers.each(Chart.instances, function(instance) {
                instance.resize();
            });
        }
    }
    
    // Handle window resize for responsive adjustments
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(function() {
            resizeCharts();
        }, 250);
    });
    
    // Add swipe functionality for mobile
    let touchStartX = 0;
    let touchEndX = 0;
    
    document.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
    }, false);
    
    document.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, false);
    
    function handleSwipe() {
        const swipeThreshold = 50;
        
        if (!sidebar || !menuOverlay || !mobileMenuToggle) return;
        
        // Right swipe (open menu)
        if (touchEndX - touchStartX > swipeThreshold && !sidebar.classList.contains('active')) {
            sidebar.classList.add('active');
            menuOverlay.classList.add('active');
            body.classList.add('menu-open');
            
            const icon = mobileMenuToggle.querySelector('i');
            icon.classList.remove('fa-bars');
            icon.classList.add('fa-times');
        }
        
        // Left swipe (close menu)
        if (touchStartX - touchEndX > swipeThreshold && sidebar.classList.contains('active')) {
            sidebar.classList.remove('active');
            menuOverlay.classList.remove('active');
            body.classList.remove('menu-open');
            
            const icon = mobileMenuToggle.querySelector('i');
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
        }
    }
    
    // Enhanced table responsiveness
    const tables = document.querySelectorAll('table');
    tables.forEach(table => {
        const wrapper = document.createElement('div');
        wrapper.classList.add('table-responsive');
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);
    });
    
    // Enhanced image responsiveness
    const contentImages = document.querySelectorAll('.main-content img:not(.user-avatar):not(.user-avatar-sm)');
    contentImages.forEach(img => {
        if (!img.classList.contains('responsive-img')) {
            img.classList.add('responsive-img');
        }
    });
    
    // Handle fixed position elements on iOS
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    if (isIOS) {
        document.documentElement.classList.add('ios');
    }
}); 