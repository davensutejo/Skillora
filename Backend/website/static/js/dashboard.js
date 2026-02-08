// SKILLORA DASHBOARD JAVASCRIPT
// Enhanced functionality and animations

document.addEventListener('DOMContentLoaded', function() {
    console.log('Skillora Dashboard Initialized');
    
    // Apply fade-in animation to main sections
    const fadeInElements = document.querySelectorAll('.dashboard-header, .quick-actions-bar, .stat-card, .streak-section, .course-card');
    fadeInElements.forEach((element, index) => {
        element.classList.add('fade-in');
        element.style.animationDelay = `${index * 0.1}s`;
    });
    
    // === Mobile menu toggle functionality ===
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (mobileMenuToggle && sidebar) {
        mobileMenuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
            document.body.classList.toggle('sidebar-open');
        });
        
        // Close sidebar when clicking outside
        document.addEventListener('click', function(event) {
            if (sidebar.classList.contains('active') && 
                !sidebar.contains(event.target) && 
                event.target !== mobileMenuToggle) {
                sidebar.classList.remove('active');
                document.body.classList.remove('sidebar-open');
            }
        });
    }
    
    // === Hover effects for cards ===
    const enhancedCards = document.querySelectorAll('.enhanced-card');
    enhancedCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = 'var(--shadow-lg)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = 'var(--shadow-md)';
        });
    });
    
    // === Initialize Charts ===
    initializeCharts();
    
    // === Tooltips ===
    const tooltips = document.querySelectorAll('.tooltip');
    tooltips.forEach(tooltip => {
        const tooltipText = tooltip.querySelector('.tooltip-text');
        if (!tooltipText) return;
        
        tooltip.addEventListener('mouseenter', function() {
            tooltipText.style.visibility = 'visible';
            tooltipText.style.opacity = '1';
        });
        
        tooltip.addEventListener('mouseleave', function() {
            tooltipText.style.visibility = 'hidden';
            tooltipText.style.opacity = '0';
        });
    });
    
    // === Progress bars animation ===
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        const width = bar.style.width;
        bar.style.width = '0';
        
        setTimeout(() => {
            bar.style.transition = 'width 1s ease';
            bar.style.width = width;
        }, 300);
    });
    
    // === Streak calendar interactivity ===
    const calendarDays = document.querySelectorAll('.day:not(.outside)');
    calendarDays.forEach(day => {
        day.addEventListener('click', function() {
            if (!this.classList.contains('completed') && !this.classList.contains('current')) {
                alert('You can\'t mark future days as completed yet.');
            }
        });
    });
    
    // === Quick actions interactivity ===
    const quickActions = document.querySelectorAll('.quick-action-item');
    quickActions.forEach(action => {
        action.addEventListener('click', function() {
            const actionName = this.querySelector('span').textContent;
            console.log(`Quick action clicked: ${actionName}`);
            
            // Example animation feedback
            const icon = this.querySelector('.quick-action-icon');
            icon.style.transform = 'scale(1.2)';
            
            setTimeout(() => {
                icon.style.transform = 'scale(1)';
            }, 300);
            
            // Demo action for "Continue Learning"
            if (actionName.includes('Continue Learning')) {
                window.location.href = '#learning-path-section';
            }
        });
    });
    
    // === Notification badge pulse animation ===
    const notificationBadges = document.querySelectorAll('.notification-badge');
    notificationBadges.forEach(badge => {
        setInterval(() => {
            badge.classList.add('pulse');
            
            setTimeout(() => {
                badge.classList.remove('pulse');
            }, 1000);
        }, 5000);
    });
    
    // === Scroll to top button functionality ===
    const scrollButton = document.createElement('button');
    scrollButton.innerHTML = '<i class="fas fa-arrow-up"></i>';
    scrollButton.classList.add('scroll-top-btn');
    document.body.appendChild(scrollButton);
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > 300) {
            scrollButton.classList.add('visible');
        } else {
            scrollButton.classList.remove('visible');
        }
    });
    
    scrollButton.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
});

// === Chart Initialization ===
function initializeCharts() {
    // Safely get chart canvas elements
    const getChartCanvas = (id) => document.getElementById(id)?.getContext('2d');
    
    // Courses Chart (Doughnut)
    const coursesCtx = getChartCanvas('coursesChart');
    if (coursesCtx) {
        new Chart(coursesCtx, {
            type: 'doughnut',
            data: {
                labels: ['Completed', 'In Progress', 'Not Started'],
                datasets: [{
                    data: [3, 4, 2],
                    backgroundColor: [
                        'rgba(0, 200, 83, 0.7)',
                        'rgba(98, 0, 234, 0.7)',
                        'rgba(225, 225, 225, 0.7)'
                    ],
                    borderColor: [
                        'rgba(0, 200, 83, 1)',
                        'rgba(98, 0, 234, 1)',
                        'rgba(225, 225, 225, 1)'
                    ],
                    borderWidth: 1,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '75%',
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: true,
                        backgroundColor: 'rgba(0, 0, 0, 0.7)',
                        padding: 10,
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        bodyFont: {
                            size: 14
                        },
                        boxPadding: 5,
                        usePointStyle: true
                    }
                },
                animation: {
                    animateScale: true,
                    animateRotate: true,
                    duration: 2000,
                    easing: 'easeOutQuart'
                }
            }
        });
    }
    
    // Study Time Chart (Bar chart)
    const studyTimeCtx = getChartCanvas('studyTimeChart');
    if (studyTimeCtx) {
        new Chart(studyTimeCtx, {
            type: 'bar',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Morning',
                    data: [1.2, 0.8, 1.5, 1.0, 0.7, 2.0, 1.8],
                    backgroundColor: 'rgba(98, 0, 234, 0.7)',
                    borderRadius: 6
                }, {
                    label: 'Afternoon',
                    data: [0.5, 1.2, 0.8, 1.5, 1.0, 1.3, 0.6],
                    backgroundColor: 'rgba(157, 70, 255, 0.7)',
                    borderRadius: 6
                }, {
                    label: 'Evening',
                    data: [2.0, 1.5, 1.8, 1.2, 1.6, 0.8, 0.5],
                    backgroundColor: 'rgba(176, 0, 32, 0.7)',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: true,
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        stacked: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value + 'h';
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            boxWidth: 12,
                            padding: 15,
                            usePointStyle: true
                        }
                    }
                },
                animation: {
                    duration: 2000,
                    easing: 'easeOutQuart'
                }
            }
        });
    }
    
    // Subject Performance Chart (Radar)
    const perfCtx = getChartCanvas('subjectPerformanceChart');
    if (perfCtx) {
        new Chart(perfCtx, {
            type: 'radar',
            data: {
                labels: ['Python', 'Data Science', 'Machine Learning', 'Web Dev', 'Databases', 'DevOps'],
                datasets: [{
                    label: 'Score',
                    data: [85, 70, 65, 90, 75, 60],
                    backgroundColor: 'rgba(98, 0, 234, 0.2)',
                    borderColor: 'rgba(98, 0, 234, 1)',
                    pointBackgroundColor: 'rgba(98, 0, 234, 1)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgba(98, 0, 234, 1)',
                    borderWidth: 2
                }, {
                    label: 'Time Spent',
                    data: [70, 60, 55, 80, 50, 40],
                    backgroundColor: 'rgba(176, 0, 32, 0.2)',
                    borderColor: 'rgba(176, 0, 32, 1)',
                    pointBackgroundColor: 'rgba(176, 0, 32, 1)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgba(176, 0, 32, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                elements: {
                    line: {
                        tension: 0.2
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            boxWidth: 12,
                            padding: 15,
                            usePointStyle: true
                        }
                    }
                },
                scales: {
                    r: {
                        angleLines: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        pointLabels: {
                            font: {
                                size: 12
                            }
                        },
                        ticks: {
                            backdropColor: 'transparent',
                            color: 'rgba(0, 0, 0, 0.4)',
                            showLabelBackdrop: false,
                            font: {
                                size: 10
                            }
                        },
                        suggestedMin: 0,
                        suggestedMax: 100
                    }
                },
                animation: {
                    duration: 2000,
                    easing: 'easeOutQuart'
                }
            }
        });
    }
} 