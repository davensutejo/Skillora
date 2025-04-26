document.addEventListener('DOMContentLoaded', function() {
    // Initialize Lenis smooth scrolling
    const lenis = new Lenis({
        duration: 1.2,
        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        direction: 'vertical',
        gestureDirection: 'vertical',
        smooth: true,
        smoothTouch: false,
        touchMultiplier: 2
    });

    // Check device capabilities for responsive adjustments
    const isMobile = window.innerWidth <= 768;
    const isSmallMobile = window.innerWidth <= 576;
        
    // Make detection available globally
    window.isMobile = isMobile;
    window.isSmallMobile = isSmallMobile;

    // Adjust settings based on device
    if (isMobile) {
        // Adjust Lenis smooth scrolling settings for mobile
        lenis.options.duration = 0.8;
        lenis.options.touchMultiplier = 1.5;
    }

    function raf(time) {
        lenis.raf(time);
        requestAnimationFrame(raf);
    }

    requestAnimationFrame(raf);

    // Three.js setup
    let scene, camera, renderer, particles, particlesMaterial;
    let mouseX = 0, mouseY = 0;
    let windowHalfX = window.innerWidth / 2;
    let windowHalfY = window.innerHeight / 2;

    function initThreeJS() {
        // Create scene
        scene = new THREE.Scene();
        
        // Create camera
        camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.z = 2;
        
        // Create renderer
        renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        document.getElementById('canvas-container').appendChild(renderer.domElement);
        
        // Create particles
        const particlesGeometry = new THREE.BufferGeometry();
        const count = 2000;
        
        const positions = new Float32Array(count * 3);
        const colors = new Float32Array(count * 3);
        
        for (let i = 0; i < count * 3; i++) {
            positions[i] = (Math.random() - 0.5) * 10;
            colors[i] = Math.random();
        }
        
        particlesGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        particlesGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        
        particlesMaterial = new THREE.PointsMaterial({
            size: 0.05,
            sizeAttenuation: true,
            transparent: true,
            alphaMap: createCircleTexture(),
            depthWrite: false,
            blending: THREE.AdditiveBlending,
            vertexColors: true
        });
        
        particles = new THREE.Points(particlesGeometry, particlesMaterial);
        scene.add(particles);
        
        // Expose to window object for theme-three.js
        window.threeJsScene = scene;
        window.threeJsCamera = camera;
        window.threeJsRenderer = renderer;
        
        // After creating particles, expose to window
        window.threeJsParticles = particles;
        window.threeJsParticlesMaterial = particlesMaterial;
        
        // Event listeners
        window.addEventListener('resize', onWindowResize);
        document.addEventListener('mousemove', onDocumentMouseMove);
    }

    function createCircleTexture() {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        canvas.width = 64;
        canvas.height = 64;
        
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = canvas.width / 3;
        
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI, false);
        ctx.fillStyle = 'white';
        ctx.fill();
        
        const texture = new THREE.Texture(canvas);
        texture.needsUpdate = true;
        return texture;
    }

    function onWindowResize() {
        windowHalfX = window.innerWidth / 2;
        windowHalfY = window.innerHeight / 2;
        
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        
        renderer.setSize(window.innerWidth, window.innerHeight);
    }

    function onDocumentMouseMove(event) {
        mouseX = (event.clientX - windowHalfX) * 0.001;
        mouseY = (event.clientY - windowHalfY) * 0.001;
    }

    function animate() {
        requestAnimationFrame(animate);
        
        particles.rotation.x += 0.0005;
        particles.rotation.y += 0.0008;
        
        particles.rotation.y += mouseX * 1.5;
        particles.rotation.x += mouseY * 1.5;
        
        renderer.render(scene, camera);
    }

    // Create parallax elements
    function createParallaxElements() {
        const heroParallax = document.querySelector('.hero-parallax');
        const feature1Parallax = document.querySelector('.feature1-parallax');
        const feature2Parallax = document.querySelector('.feature2-parallax');
        const feature3Parallax = document.querySelector('.feature3-parallax');
        const feature4Parallax = document.querySelector('.feature4-parallax');
        const ctaParallax = document.querySelector('.cta-parallax');
        
        // Adjust number of elements based on device performance
        const dotCount = isMobile ? (isSmallMobile ? 15 : 25) : 40;
        const lineCount = isMobile ? (isSmallMobile ? 5 : 8) : 15;
        const circleCount = isMobile ? (isSmallMobile ? 3 : 5) : 8;
        
        // Create elements for each section
        createParallaxSet(heroParallax, dotCount, lineCount, circleCount);
        
        // Only create parallax elements for the sections that are currently visible
        // or use lighter versions on mobile
        if (!isMobile) {
            createParallaxSet(feature1Parallax, dotCount * 0.7, lineCount * 0.7, circleCount * 0.7);
            createParallaxSet(feature2Parallax, dotCount * 0.7, lineCount * 0.7, circleCount * 0.7);
            createParallaxSet(feature3Parallax, dotCount * 0.7, lineCount * 0.7, circleCount * 0.7);
            createParallaxSet(feature4Parallax, dotCount * 0.7, lineCount * 0.7, circleCount * 0.7);
        } else {
            // Create lighter versions for mobile - just on the first panel
            createParallaxSet(feature1Parallax, dotCount * 0.5, lineCount * 0.3, circleCount * 0.3);
            
            // For other panels, create minimal elements or none at all
            if (!isSmallMobile) {
                createParallaxSet(feature2Parallax, dotCount * 0.3, lineCount * 0.2, circleCount * 0.2);
                createParallaxSet(feature3Parallax, dotCount * 0.3, lineCount * 0.2, circleCount * 0.2);
                createParallaxSet(feature4Parallax, dotCount * 0.3, lineCount * 0.2, circleCount * 0.2);
            }
        }
        
        // Always create some parallax for CTA section, but lighter on mobile
        createParallaxSet(ctaParallax, dotCount * (isMobile ? 0.5 : 0.8), 
                         lineCount * (isMobile ? 0.3 : 0.8), 
                         circleCount * (isMobile ? 0.2 : 0.8));
    }
    
    function createParallaxSet(container, dotCount, lineCount, circleCount) {
        if (!container) return;
        
        // Clear existing elements if any
        container.innerHTML = '';
        
        // Create layer for dots
        const dotLayer = document.createElement('div');
        dotLayer.className = 'parallax-layer';
        container.appendChild(dotLayer);
        
        // Create dots
        for (let i = 0; i < dotCount; i++) {
                const dot = document.createElement('div');
                dot.className = 'parallax-dot';
                
            const size = Math.random() * 5 + 2;
                dot.style.width = `${size}px`;
                dot.style.height = `${size}px`;
                
                dot.style.top = `${Math.random() * 100}%`;
            dot.style.left = `${Math.random() * 100}%`;
            dot.style.opacity = Math.random() * 0.5 + 0.1;
            
            dotLayer.appendChild(dot);
        }
        
        // Create layer for lines
        const lineLayer = document.createElement('div');
        lineLayer.className = 'parallax-layer';
        container.appendChild(lineLayer);
        
        // Create lines
        for (let i = 0; i < lineCount; i++) {
                const line = document.createElement('div');
                line.className = 'parallax-line';
                
            const width = Math.random() * 150 + 50;
                line.style.width = `${width}px`;
                
                line.style.top = `${Math.random() * 100}%`;
            line.style.left = `${Math.random() * 100}%`;
            line.style.opacity = Math.random() * 0.3 + 0.1;
            line.style.transform = `rotate(${Math.random() * 360}deg)`;
            
            lineLayer.appendChild(line);
        }
        
        // Create layer for circles
        const circleLayer = document.createElement('div');
        circleLayer.className = 'parallax-layer';
        container.appendChild(circleLayer);
        
        // Create circles
        for (let i = 0; i < circleCount; i++) {
                const circle = document.createElement('div');
                circle.className = 'parallax-circle';
                
            const size = Math.random() * 80 + 20;
                circle.style.width = `${size}px`;
                circle.style.height = `${size}px`;
                
                circle.style.top = `${Math.random() * 100}%`;
            circle.style.left = `${Math.random() * 100}%`;
            circle.style.opacity = Math.random() * 0.2 + 0.05;
            
            circleLayer.appendChild(circle);
        }
        
        // Add parallax effect to layers
        if (!isMobile) {
            gsap.to(dotLayer, {
                y: -50,
                x: -30,
                scrollTrigger: {
                    trigger: container.parentElement,
                    start: 'top bottom',
                    end: 'bottom top',
                    scrub: 1.5
                }
            });
            
            gsap.to(lineLayer, {
                y: -30,
                x: 20,
                scrollTrigger: {
                    trigger: container.parentElement,
                    start: 'top bottom',
                    end: 'bottom top',
                    scrub: 1
                }
            });
            
            gsap.to(circleLayer, {
                y: -20,
                x: -10,
                scrollTrigger: {
                    trigger: container.parentElement,
                    start: 'top bottom',
                    end: 'bottom top',
                    scrub: 0.5
                }
            });
        } else {
            // Lighter parallax effect for mobile
            gsap.to(dotLayer, {
                y: -25,
                scrollTrigger: {
                    trigger: container.parentElement,
                    start: 'top bottom',
                    end: 'bottom top',
                    scrub: 1
                }
            });
            
            gsap.to(lineLayer, {
                y: -15,
                scrollTrigger: {
                    trigger: container.parentElement,
                    start: 'top bottom',
                    end: 'bottom top',
                    scrub: 0.7
                }
            });
        }
    }

    // Initialize the page
    function initPage() {
        // Initialize Three.js
        initThreeJS();
        
        animate();
        
        // Register ScrollTrigger with GSAP
        if (window.ScrollTrigger) {
            gsap.registerPlugin(ScrollTrigger);
        }
        
        // Create parallax elements
        createParallaxElements();
        
        // Loader animation
        const tl = gsap.timeline();
        
        // Buat partikel untuk logo
        const logoParticles = document.querySelector('.logo-particles');
        const particleCount = 30;
        
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            
            // Ukuran random antara 3-8px
            const size = Math.random() * 5 + 3;
            particle.style.width = `${size}px`;
            particle.style.height = `${size}px`;
            
            // Set posisi awal acak
            const angle = Math.random() * Math.PI * 2;
            const radius = Math.random() * 100 + 30;
            const x = Math.cos(angle) * radius;
            const y = Math.sin(angle) * radius;
            
            particle.style.left = `calc(50% + ${x}px)`;
            particle.style.top = `calc(50% + ${y}px)`;
            
            logoParticles.appendChild(particle);
        }
        
        // Animasi logo reveal
        tl.to('.logo-circle', {
            scale: 1,
            opacity: 1,
            duration: 1,
            ease: "elastic.out(1, 0.5)"
        })
        .to('.logo-letter', {
            scale: 1,
            opacity: 1,
            rotation: 0,
            duration: 1.2,
            ease: "elastic.out(1, 0.7)"
        }, "-=0.7")
        .to('.logo-particles', {
            opacity: 1,
            duration: 0.3
        }, "-=0.9")
        .to('.particle', {
            opacity: 0.8,
            duration: 0.8,
            stagger: {
                each: 0.02,
                grid: "random",
                from: "center"
            },
            ease: "power3.out"
        }, "-=0.8")
        .to('.loader h1', {
            opacity: 1,
            y: 0,
            duration: 1,
            ease: "power2.out"
        }, "-=0.5")
        .to('.loader__subheader', {
            opacity: 1,
            y: 0,
            duration: 0.8,
            ease: "power2.out"
        }, "-=0.7")
        .to('.particle', {
            x: 0,
            y: 0,
            opacity: 0,
            scale: 0.3,
            duration: 1.5,
            stagger: {
                each: 0.02,
                grid: "random",
                from: "center"
            },
            ease: "power2.inOut"
        }, "-=0.2");
        
        // Animasi teks
        const letters = "SKILLORA".split("");
        
        // Buat elemen untuk setiap huruf untuk animasi teks
        document.querySelector('.loader h1').innerHTML = '';
        letters.forEach(letter => {
            const span = document.createElement('span');
            span.textContent = letter;
            span.style.display = 'inline-block';
            span.style.opacity = '0';
            span.style.transform = 'translateY(50px) scale(0.8)';
            document.querySelector('.loader h1').appendChild(span);
        });
        
        // Animasi setiap huruf dari judul
        tl.to('.loader h1 span', {
            opacity: 1,
            y: 0,
            scale: 1,
            duration: 0.6,
            stagger: 0.08,
            ease: "back.out(1.7)"
        }, "-=1")
        // Tambahkan efek glow pada teks Skillora setelah animasi stagger
        .to('.loader h1', {
            textShadow: '0 0 15px rgba(93, 63, 211, 0.7), 0 0 30px rgba(93, 63, 211, 0.5), 0 0 45px rgba(93, 63, 211, 0.3)',
            color: '#ffffff',
            duration: 0.8,
            ease: "power2.inOut"
        }, "-=0.2")
        .to('.loader__subheader', {
            opacity: 1,
            y: 0,
            duration: 0.8,
            ease: "power2.out"
        }, "-=1");
        
        // Animasi keluar dengan efek twist
        tl.to('.logo-letter', {
            scale: 1.5,
            rotation: 360,
            opacity: 0,
            duration: 0.7,
            ease: "power1.in"
        }, "+=1")
        .to('.logo-circle', {
            scale: 1.5,
            opacity: 0,
            duration: 0.5,
            ease: "power1.in"
        }, "-=0.5")
        .to('.loader h1 span', {
            opacity: 0,
            y: -40,
            scale: 1.2,
            stagger: 0.05,
            duration: 0.4,
            ease: "power2.in"
        }, "-=0.4")
        .to('.loader__subheader', {
            opacity: 0,
            y: -20,
            duration: 0.5,
            ease: "power2.in"
        }, "-=0.6")
        .to('.loader', {
            y: '-100%',
            duration: 0.8,
            ease: "power4.inOut",
            onComplete: () => {
                document.querySelector('.loader').style.display = 'none';
                
                // Hero section entrance animations (run after loader is gone)
                const heroEntrance = gsap.timeline();
                
                heroEntrance
                    .to('.hero-text h1', {
                        y: 0,
                        opacity: 1,
                        duration: 1.2,
                        ease: "power4.out"
                    })
                    .to('.hero-text p', {
                        y: 0,
                        opacity: 1,
                        duration: 1,
                        ease: "power3.out"
                    }, "-=0.8")
                    .to('.hero-text .btn', {
                        y: 0,
                        opacity: 1,
                        scale: 1,
                        duration: 0.7,
                        ease: "back.out(1.7)"
                    }, "-=0.6")
                    .to('.hero-svg-1', {
                        transform: 'translate(0, 0) rotate(0deg)',
                        opacity: 0.8,
                        duration: 1.5,
                        ease: "elastic.out(1, 0.5)"
                    }, "-=1.2")
                    .to('.hero-svg-2', {
                        transform: 'translate(0, 0) rotate(0deg)',
                        opacity: 0.6,
                        duration: 1.8,
                        ease: "elastic.out(1, 0.5)"
                    }, "-=1.5")
                    .to('.hero-svg-3', {
                        transform: 'translate(0, 0) scale(1) rotate(0deg)',
                        opacity: 0.4,
                        duration: 1.7,
                        ease: "elastic.out(1, 0.5)"
                    }, "-=1.7")
                    .to('.scroll-indicator', {
                        y: 0,
                        opacity: 0.7,
                        duration: 1,
                        ease: "power2.out"
                    }, "-=1");
            }
        }, "-=0.2");
        
        // Horizontal scroll setup
        gsap.registerPlugin(ScrollTrigger);
        
        const horizontalSection = document.querySelector('.horizontal-section');
        
        // Add variable to track current active panel
        let currentActivePanel = 0;
        
        gsap.to(horizontalSection, {
            x: () => -(horizontalSection.scrollWidth - window.innerWidth),
            ease: "none",
            scrollTrigger: {
                trigger: horizontalSection,
                start: "top top",
                end: () => `+=${horizontalSection.scrollWidth - window.innerWidth}`,
                scrub: isMobile ? 0.5 : 1, // Less delay on mobile for more responsive feel
                pin: true,
                anticipatePin: 1,
                invalidateOnRefresh: true,
                id: 'horizontal-section',
                onUpdate: (self) => {
                    // Get the feature panels
                    const panels = document.querySelectorAll('.feature-panel');
                    const progress = self.progress;
                    const panelWidth = window.innerWidth;
                    const totalScroll = horizontalSection.scrollWidth - window.innerWidth;
                    const scrolledAmount = progress * totalScroll;
                    
                    // Calculate which panel is currently active
                    const newActivePanel = Math.floor(scrolledAmount / panelWidth);
                    
                    // Update current active panel
                    if (newActivePanel !== currentActivePanel) {
                        currentActivePanel = newActivePanel;
                    }
                    
                    // Figure out which panels should be blurred based on scroll position
                    panels.forEach((panel, index) => {
                        const panelPosition = index * panelWidth;
                        const panelEndPosition = panelPosition + panelWidth;
                        // Adjust blur threshold for mobile - start blur sooner on small screens
                        const blurThresholdPercent = isSmallMobile ? 0.15 : (isMobile ? 0.2 : 0.3);
                        const blurThreshold = panelPosition + (panelWidth * blurThresholdPercent);
                        
                        // If we've scrolled past the blur threshold of this panel
                        if (scrolledAmount > blurThreshold) {
                            // Apply progressive blur based on how far we've gone past the panel
                            const pastDistance = scrolledAmount - blurThreshold;
                            // Less intense blur on mobile to improve performance
                            const maxBlur = isMobile ? 8 : 15;
                            const denominator = blurThresholdPercent === 0.3 ? 0.7 : (blurThresholdPercent === 0.2 ? 0.8 : 0.85);
                            const blurAmount = Math.min(maxBlur, (pastDistance / (panelWidth * denominator)) * maxBlur);
                            
                            // Apply heavy blur to panels we've passed - less intense on mobile
                            gsap.to(panel, {
                                filter: `blur(${blurAmount}px)`,
                                opacity: Math.max(0.4, 1 - (blurAmount / 20)),
                                duration: isMobile ? 0.2 : 0.3 // Faster transitions on mobile
                            });
                            
                            // Add more dramatic blur effect to SVG elements
                            gsap.to(panel.querySelectorAll('.feature-svg-element'), {
                                filter: `blur(${blurAmount * 1.5}px)`,
                                opacity: Math.max(0.3, 1 - (blurAmount / 15)),
                                scale: Math.max(0.85, 1 - (blurAmount / 100)),
                                duration: isMobile ? 0.3 : 0.4
                            });
                            
                            // Tambahkan blur ke konten
                            gsap.to(panel.querySelector('.feature-content'), {
                                filter: `blur(${blurAmount * 0.7}px)`,
                                opacity: Math.max(0.5, 1 - (blurAmount / 25)),
                                duration: isMobile ? 0.2 : 0.3
                            });
                        } 
                        // If we're currently viewing this panel (before the blur threshold)
                        else if (scrolledAmount > panelPosition && scrolledAmount < blurThreshold) {
                            // Current panel is clear
                            gsap.to(panel, {
                                filter: 'blur(0px)',
                                opacity: 1,
                                duration: 0.3
                            });
                            
                            // Clear SVG elements in current panel
                            gsap.to(panel.querySelectorAll('.feature-svg-element'), {
                                filter: 'drop-shadow(0 0 10px rgba(93, 63, 211, 0.2))',
                                opacity: 1,
                                scale: 1,
                                duration: 0.4
                            });
                            
                            // Clear content
                            gsap.to(panel.querySelector('.feature-content'), {
                                filter: 'blur(0px)',
                                opacity: 1,
                                duration: 0.3
                            });
                        }
                        // If we haven't reached this panel yet
                        else if (scrolledAmount < panelPosition) {
                            // Upcoming panels are clear (no blur)
                            gsap.to(panel, {
                                filter: 'blur(0px)',
                                opacity: 1,
                                duration: 0.3
                            });
                            
                            // Clear upcoming SVG elements
                            gsap.to(panel.querySelectorAll('.feature-svg-element'), {
                                filter: 'drop-shadow(0 0 10px rgba(93, 63, 211, 0.2))',
                                opacity: 1,
                                scale: 1,
                                duration: 0.4
                            });
                            
                            // Clear upcoming content
                            gsap.to(panel.querySelector('.feature-content'), {
                                filter: 'blur(0px)',
                                opacity: 1,
                                duration: 0.3
                            });
                        }
                    });
                }
            }
        });
        
        // GSAP animations for the hero section
        gsap.fromTo(particles.rotation, 
            { x: 0, y: 0 }, 
            { 
                x: Math.PI * 2, 
                y: Math.PI * 2, 
                duration: 20, 
                ease: "none", 
                repeat: -1 
            }
        );
        
        // Add resize and orientation change handler for responsive adjustments
        let resizeTimeout;
        const handleResize = () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                // Update mobile detection
                const wasMobile = isMobile;
                const wasSmallMobile = isSmallMobile;
                
                // Check device size again after resize
                const newIsMobile = window.innerWidth <= 768;
                const newIsSmallMobile = window.innerWidth <= 576;
                
                // Only force refresh if mobile status changed
                if (wasMobile !== newIsMobile || wasSmallMobile !== newIsSmallMobile) {
                    // Update scroll trigger to account for new dimensions
                    ScrollTrigger.refresh();
                    
                    // Force update the mobile variables - needs to be done globally
                    window.isMobile = newIsMobile;
                    window.isSmallMobile = newIsSmallMobile;
                    
                    // If switching to mobile, adjust blur settings and animations
                    if (newIsMobile) {
                        // Reduce animation intensity on mobile
                        gsap.globalTimeline.timeScale(1.2); // Speed up animations
                    } else {
                        // Reset to normal speed on desktop
                        gsap.globalTimeline.timeScale(1);
                    }
                }
            }, 200); // Debounce resize event
        };
        
        // Listen for resize and orientation change
        window.addEventListener('resize', handleResize);
        window.addEventListener('orientationchange', () => {
            // On orientation change, we need a small delay to get accurate dimensions
            setTimeout(handleResize, 300);
        });
        
        // Touch-friendly enhancements for mobile
        if (isMobile) {
            // Apply mobile-specific animation settings
            gsap.globalTimeline.timeScale(1.2); // Speed up animations on mobile
            
            // Add swipe detection for horizontal scroll section
            let touchStartX = 0;
            let touchEndX = 0;
            
            horizontalSection.addEventListener('touchstart', (e) => {
                touchStartX = e.changedTouches[0].screenX;
            }, { passive: true });
            
            horizontalSection.addEventListener('touchend', (e) => {
                touchEndX = e.changedTouches[0].screenX;
                handleSwipe();
            }, { passive: true });
            
            const handleSwipe = () => {
                const swipeDistance = touchStartX - touchEndX;
                const panelWidth = window.innerWidth;
                
                // If significant swipe detected
                if (Math.abs(swipeDistance) > 50) {
                    const direction = swipeDistance > 0 ? 1 : -1; // 1 for right, -1 for left
                    
                    // Calculate target panel
                    let targetPanel = currentActivePanel;
                    
                    if (direction === 1 && currentActivePanel < 3) { // Swipe left, go right
                        targetPanel = currentActivePanel + 1;
                    } else if (direction === -1 && currentActivePanel > 0) { // Swipe right, go left
                        targetPanel = currentActivePanel - 1;
                    }
                    
                    // Get current scroll position and calculate target position
                    const scrollInstance = ScrollTrigger.getById('horizontal-section');
                    if (scrollInstance) {
                        // Calculate target progress based on panels
                        const targetProgress = targetPanel / 3; // 4 panels, so 0, 0.33, 0.66, 1
                        
                        // Manually update scroll position
                        scrollInstance.scroll(targetProgress * scrollInstance.end);
                    }
                }
            };
        }
        
        gsap.fromTo(particlesMaterial, 
            { opacity: 0.3 }, 
            { 
                opacity: 0.8, 
                duration: 2, 
                yoyo: true, 
                repeat: -1, 
                ease: "sine.inOut" 
            }
        );
        
        // Scroll indicator animation
        gsap.to('.scroll-indicator', {
            opacity: 0,
            duration: 1,
            scrollTrigger: {
                trigger: '.hero',
                start: "top top",
                end: "bottom top",
                scrub: true
            }
        });
        
        // Parallax animations for hero SVGs with more advanced scroll effects
        const blobTimelines = [];
        
        // Modified timeline for hero-svg-1 with morphing and color change
        blobTimelines[0] = gsap.timeline({
            scrollTrigger: {
                trigger: '.hero',
                start: 'top top',
                end: 'bottom top',
                scrub: true,
                onUpdate: (self) => {
                    // Self.progress is between 0-1 based on scroll position
                    const progress = self.progress;
                    
                    // Change filter stdDeviation based on scroll
                    const glow = 4 + (progress * 8); // Between 4-12
                    gsap.set('.hero-svg-1 filter feGaussianBlur', { attr: { stdDeviation: glow } });
                    
                    // Change gradient colors based on scroll
                    const colorStart = gsap.utils.interpolate('#7B5FFF', '#BB8FFF', progress);
                    const colorEnd = gsap.utils.interpolate('#5D3FD3', '#9260FF', progress);
                    
                    gsap.set('.hero-svg-1 .gradient-stop-1', { attr: { 'stop-color': colorStart } });
                    gsap.set('.hero-svg-2 .gradient-stop-2', { attr: { 'stop-color': colorEnd } });
                }
            }
        });
        
        blobTimelines[0].to('.hero-svg-1', {
            y: -80,
            x: 50,
            rotation: 15,
            scale: 1.3, // Increased scale for more dramatic effect
            ease: 'power2.inOut',
            transformOrigin: '50% 50%'
        });
        
        // Modified timeline for hero-svg-2 dengan extend end point
        blobTimelines[1] = gsap.timeline({
            scrollTrigger: {
                trigger: '.hero',
                start: 'top top',
                end: 'bottom -30%', // Extend end point untuk terus beranimasi melewati batas section
                scrub: true,
                onUpdate: (self) => {
                    const progress = self.progress;
                    
                    // Change filter stdDeviation based on scroll
                    const glow = 3 + (progress * 7); // Between 3-10
                    gsap.set('.hero-svg-2 filter feGaussianBlur', { attr: { stdDeviation: glow } });
                    
                    // Change radial gradient position based on scroll
                    const newFx = 30 + (progress * 40); // Move focal point
                    const newFy = 30 + (progress * 20);
                    
                    gsap.set('#gradient2', { 
                        attr: { 
                            fx: newFx + '%', 
                            fy: newFy + '%',
                            r: (70 - progress * 20) + '%' // Shrink radius as we scroll
                        } 
                    });
                }
            }
        });
        
        blobTimelines[1].to('.hero-svg-2', {
            y: 100,
            x: -30,
            rotation: -45, // More rotation
            scale: 0.9,
            ease: 'power1.inOut',
            transformOrigin: '30% 70%'
        });
        
        // Modified timeline for hero-svg-3 with scale pulsing
        blobTimelines[2] = gsap.timeline({
            scrollTrigger: {
                trigger: '.hero',
                start: 'top top',
                end: 'bottom top',
                scrub: true,
                onUpdate: (self) => {
                    const progress = self.progress;
                    
                    // Change filter based on scroll
                    const glow = 2.5 + (progress * 5); // Between 2.5-7.5
                    gsap.set('.hero-svg-3 filter feGaussianBlur', { attr: { stdDeviation: glow } });
                    
                    // Change linear gradient direction based on scroll
                    const newX2 = 100 * progress; // Change gradient direction
                    const newY2 = 100 - (100 * progress);
                    
                    gsap.set('#gradient3', { 
                        attr: { 
                            x2: newX2 + '%', 
                            y2: newY2 + '%'
                        } 
                    });
                    
                    // Change middle color of gradient
                    const middleColor = gsap.utils.interpolate('#7A5CF5', '#A082FF', progress);
                    gsap.set('.hero-svg-3 .gradient-stop-2', { attr: { 'stop-color': middleColor } });
                }
            }
        });
        
        blobTimelines[2].to('.hero-svg-3', {
            y: -50,
            x: -80,
            rotation: 30,
            scale: 1.4, // More dramatic scaling
            ease: 'power2.inOut',
            transformOrigin: '80% 20%'
        });

        // Enhanced 3D effect on scroll for all blobs
        gsap.timeline({
            scrollTrigger: {
                trigger: '.hero',
                start: 'top top',
                end: 'bottom top',
                scrub: true
            }
        }).to('.hero-svg', {
            rotationY: 15,
            rotationX: -10,
            perspective: 800,
            ease: 'none'
        });
        
        // Add perspective container for 3D transformations
        gsap.set('.hero-svg', { perspective: 1000 });
        
        // Interactive animation for feature blobs - FIXED: Tidak menggunakan ScrollTrigger
        document.querySelectorAll('.feature-panel').forEach((panel, index) => {
            const svgElements = panel.querySelectorAll('.feature-svg-element');
            
            // Tambahkan animasi sederhana untuk setiap SVG blob tanpa ScrollTrigger
            svgElements.forEach((svg, i) => {
                // Set posisi awal
                gsap.set(svg, {
                    rotation: 0,
                    scale: 1,
                    y: 0,
                    x: 0,
                    transformOrigin: i % 2 === 0 ? '70% 30%' : '30% 70%'
                });
                
                // Animasi hover untuk SVG
                panel.addEventListener('mouseenter', function() {
                    gsap.to(svg, {
                        rotation: i % 2 === 0 ? 20 : -20,
                        scale: i % 2 === 0 ? 1.15 : 0.85,
                        y: i % 2 === 0 ? -20 : 20,
                        x: i % 2 === 0 ? 15 : -15,
                        duration: 0.8,
                        ease: "power2.out"
                    });
                    
                    // Animasi filter untuk efek glow
                            const filterElement = svg.querySelector('filter feGaussianBlur');
                            if (filterElement) {
                        gsap.to(filterElement, { 
                            attr: { stdDeviation: 5 },
                            duration: 0.8
                        });
                    }
                });
                
                panel.addEventListener('mouseleave', function() {
                    gsap.to(svg, {
                        rotation: 0,
                        scale: 1,
                        y: 0,
                        x: 0,
                        duration: 0.8,
                        ease: "power2.out"
                    });
                    
                    // Reset filter
                    const filterElement = svg.querySelector('filter feGaussianBlur');
                    if (filterElement) {
                        gsap.to(filterElement, { 
                            attr: { stdDeviation: 2 },
                            duration: 0.8
                        });
                    }
                });
            });
            
            // Animasi untuk konten panel dengan IntersectionObserver
            const featureObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        // Animate content when panel is visible
                        gsap.fromTo(panel.querySelector('.feature-number'), 
                    {
                        scale: 0.8,
                                opacity: 0,
                        x: index % 2 === 0 ? -50 : 50
                    },
                    {
                        scale: 1,
                        opacity: 0.1,
                        x: 0,
                                duration: 0.6,
                        ease: "back.out(1.7)"
                    }
                        );
                        
                        gsap.fromTo(panel.querySelector('.feature-icon'), 
                    {
                        scale: 0.5,
                        opacity: 0
                    },
                    {
                        scale: 1,
                        opacity: 1,
                                duration: 0.5,
                                delay: 0.2,
                        ease: "back.out(1.7)"
                            }
                        );
                        
                        gsap.fromTo(panel.querySelector('.feature-content'), 
                    { 
                        y: 50, 
                        opacity: 0
                    },
                    {
                        y: 0,
                        opacity: 1,
                                duration: 0.7,
                                delay: 0.3,
                        ease: "power2.out"
                            }
                        );
                        
                        // Stop observing once animation is triggered
                        featureObserver.unobserve(panel);
                    }
                });
            }, { threshold: 0.3 });
            
            // Start observing panel
            featureObserver.observe(panel);
        });
        
        // CTA blobs scroll animations - FIXED: Tidak menggunakan ScrollTrigger
        // Animasi ini sudah diimplementasikan di atas menggunakan IntersectionObserver
        // Kode yang menggunakan ScrollTrigger dihapus untuk mencegah error
        
        // CTA SVG animations - FIXED: Tidak menggunakan ScrollTrigger
        const ctaSvg1 = document.querySelector('.cta-svg-1');
        const ctaSvg2 = document.querySelector('.cta-svg-2');
        
        if (ctaSvg1 && ctaSvg2) {
            // Animasi default untuk posisi awal
            gsap.set(ctaSvg1, { y: 0, x: 0, rotation: 0, scale: 1 });
            gsap.set(ctaSvg2, { y: 0, x: 0, rotation: 0, scale: 1 });
            
            // Animasi dengan IntersectionObserver sebagai pengganti ScrollTrigger
            const ctaSvgObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        // Animasi untuk SVG 1
                        gsap.to(ctaSvg1, {
            y: -100,
            x: 50,
            rotation: 20,
            scale: 1.2,
                            duration: 1.5,
            ease: 'power1.inOut'
        });
        
                        // Animasi untuk SVG 2
                        gsap.to(ctaSvg2, {
            y: 100,
            x: -70,
            rotation: -15,
            scale: 0.85,
                            duration: 1.5,
            ease: 'power1.inOut'
        });
                    }
                });
            }, { threshold: 0.2 });
            
            // Cari parent CTA section untuk diobservasi
            const ctaSection = document.querySelector('.cta-section');
            if (ctaSection) {
                ctaSvgObserver.observe(ctaSection);
            }
        }
        
        // Tambahkan hover effect untuk CTA SVGs
        document.querySelectorAll('.cta-svg-element').forEach(svg => {
            svg.addEventListener('mouseenter', function() {
                gsap.to(this, {
                    scale: 1.15,
                    filter: 'drop-shadow(0 0 25px rgba(93, 63, 211, 0.6))',
                    duration: 0.5,
                    ease: 'power2.out',
                    overwrite: true
                });
            });
            
            svg.addEventListener('mouseleave', function() {
                gsap.to(this, {
                    scale: 1,
                    filter: 'drop-shadow(0 0 15px rgba(93, 63, 211, 0.3))',
                    duration: 0.5,
                    ease: 'power2.out',
                    overwrite: true
                });
            });
        });
        
        // Tambahkan pulse animation untuk CTA SVGs
        gsap.to('.cta-svg-1', {
            scale: 1.05,
            duration: 3,
            repeat: -1,
            yoyo: true,
            ease: 'sine.inOut'
        });
        
        gsap.to('.cta-svg-2', {
            scale: 1.08,
            duration: 4,
            delay: 0.5,
            repeat: -1,
            yoyo: true,
            ease: 'sine.inOut'
        });
        
        // IMPLEMENTASI BARU: Animasi header yang sederhana dengan vanilla JavaScript
        const header = document.querySelector('.nav');
        
        // Pastikan header ada
        if (header) {
            // Set style awal header
            header.style.position = "fixed";
            header.style.top = "0";
            header.style.width = "100%";
            header.style.zIndex = "100";
            header.style.transition = "top 0.3s ease";
            
            // Simpan posisi scroll terakhir
            let lastScrollTop = 0;
            
            // Fungsi untuk menyembunyikan/menampilkan header saat scroll
            function hideShowHeader() {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            
                // Tambahkan bayangan saat scroll lebih dari 10px
                if (scrollTop > 10) {
                    header.style.boxShadow = "0 4px 20px rgba(0, 0, 0, 0.15)";
                } else {
                    header.style.boxShadow = "none";
                }
                
                // Sembunyikan header saat scroll ke bawah melewati 200px
                if (scrollTop > lastScrollTop && scrollTop > 200) {
                    header.style.top = "-100px";
                } 
                // Tampilkan header saat scroll ke atas
                else if (scrollTop < lastScrollTop) {
                    header.style.top = "0";
                }
                
                // Update posisi scroll terakhir
                lastScrollTop = scrollTop;
            }
            
            // Tambahkan event listener untuk window scroll
            window.addEventListener("scroll", hideShowHeader);
            
            // Tangani juga smooth scroll Lenis jika ada
            if (typeof lenis !== 'undefined') {
                lenis.on('scroll', () => {
                    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                    if (scrollTop !== lastScrollTop) {
                        hideShowHeader();
                    }
                });
            }
        }
        
        // Pastikan elemen CTA terlihat dengan animasi masuk yang jelas
        const ctaContent = document.querySelector('.cta-content');
        if (ctaContent) {
            // Buat observer untuk animasi CTA saat muncul di viewport
            const ctaObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    // Jika CTA masuk viewport
                    if (entry.isIntersecting) {
                        // Animasi CTA content tanpa ScrollTrigger
                        gsap.fromTo(ctaContent, 
            { opacity: 0, y: 30 },
            { 
                opacity: 1,
                y: 0,
                duration: 1,
                                ease: "power2.out"
                            }
                        );
                        
                        // Animasi tombol-tombol CTA
                        const ctaButtons = document.querySelectorAll('.cta-buttons .btn');
                        if (ctaButtons.length > 0) {
                            gsap.fromTo(ctaButtons, 
            { opacity: 0, y: 20, scale: 0.9 },
            { 
                opacity: 1,
                y: 0,
                scale: 1,
                duration: 0.8,
                stagger: 0.2,
                                    ease: "back.out(1.7)"
                                }
                            );
                        }
                        
                        // Hentikan observer setelah animasi pertama
                        ctaObserver.disconnect();
                    }
                });
            }, { threshold: 0.2 }); // Trigger saat 20% dari elemen terlihat
            
            // Mulai mengobservasi CTA section
            ctaObserver.observe(ctaContent);
        }
        
        // Mobile menu functionality
        const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
        const mobileNav = document.querySelector('.mobile-nav');
        const mobileNavLinks = document.querySelectorAll('.mobile-nav a');
        
        if (mobileMenuToggle && mobileNav) {
            // Toggle mobile menu when hamburger is clicked
            mobileMenuToggle.addEventListener('click', function() {
                this.classList.toggle('active');
                mobileNav.classList.toggle('active');
                document.body.classList.toggle('menu-open');
            });
            
            // Close mobile menu when a nav link is clicked
            mobileNavLinks.forEach(link => {
                link.addEventListener('click', function() {
                    mobileMenuToggle.classList.remove('active');
                    mobileNav.classList.remove('active');
                    document.body.classList.remove('menu-open');
                });
            });

            // Add smooth scrolling to navigation links
            const allNavLinks = [...document.querySelectorAll('.nav-links a'), ...document.querySelectorAll('.mobile-nav a')];
            allNavLinks.forEach(link => {
                link.addEventListener('click', function(e) {
                    // Only process links that point to an ID on the page
                    const href = this.getAttribute('href');
                    if (href.startsWith('#')) {
                        e.preventDefault();
                        const targetSection = document.querySelector(href);
                        if (targetSection) {
                            // Use Lenis to smoothly scroll to the target
                            lenis.scrollTo(targetSection, {
                                offset: 0, // Can be adjusted if you want to offset the scroll position
                                duration: 1.2, // Duration of the animation in seconds
                                easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)) // Same easing as default Lenis
                            });
                        }
                    }
                });
            });
        }
    }

    // Tambahkan throttle function sederhana jika lodash tidak ada
    const _ = {
        throttle: function(func, wait) {
            let timeout = null;
            let previous = 0;
            
            return function() {
                const now = Date.now();
                const remaining = wait - (now - previous);
                const context = this;
                const args = arguments;
                
                if (remaining <= 0) {
                    clearTimeout(timeout);
                    timeout = null;
                    previous = now;
                    func.apply(context, args);
                } else if (!timeout) {
                    timeout = setTimeout(function() {
                        previous = Date.now();
                        timeout = null;
                        func.apply(context, args);
                    }, remaining);
                }
            };
        }
    };

    // Tambahkan animasi hover untuk tombol di hero section
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('mouseenter', function() {
            gsap.to(this, {
                scale: 1.05,
                backgroundColor: '#6F45FF',
                duration: 0.3,
                ease: 'power1.out'
            });
        });
        
        button.addEventListener('mouseleave', function() {
            gsap.to(this, {
                scale: 1,
                backgroundColor: '#5D3FD3',
                duration: 0.3,
                ease: 'power1.out'
            });
        });
    });

    // Tambahkan animasi teks 3D pada scroll di hero section dengan transisi lebih halus
    gsap.timeline({
        scrollTrigger: {
            trigger: '.hero',
            start: "top top",
            end: "bottom top",
            scrub: 0.7, // Lebih smooth dari sebelumnya
            ease: "power1.inOut" // Tambahkan easing untuk scrollTrigger
        },
        onUpdate: function() {
            // Callback onUpdate untuk variasi dinamis
            const progress = this.progress();
            
            // Variasi perspektif berdasarkan progress
            const perspective = 1000 - (progress * 200);
            gsap.set('.hero-text', { perspective: perspective });
            
            // Subtle blur efek untuk meningkatkan kesan kedalaman
            const blurAmount = Math.min(progress * 1.5, 1.5);
            if (progress > 0.1) {
                gsap.set('.hero-text', { filter: `blur(${blurAmount}px)` });
            } else {
                gsap.set('.hero-text', { filter: 'blur(0px)' });
            }
        }
    }).to('.hero-text', {
        rotationX: 10,
        rotationY: -15,
        transformPerspective: 1000,
        transformOrigin: "center center", // Pusat untuk transisi lebih halus
        scale: 0.9,
        opacity: 0.8, // Kurangi transparansi untuk keterbacaan lebih baik
        ease: "power2.inOut", // Ease yang lebih smooth
        duration: 1.5 // Durasi lebih panjang
    });

    // Tambahkan animasi yang lebih interaktif untuk feature panels
    document.querySelectorAll('.feature-panel').forEach((panel, index) => {
        const svgElements = panel.querySelectorAll('.feature-svg-element');
        
        // Tambahkan hover effect untuk feature panels
        panel.addEventListener('mouseenter', function() {
            gsap.to(svgElements, {
                scale: 1.1,
                rotation: index % 2 === 0 ? 10 : -10,
                filter: 'drop-shadow(0 0 20px rgba(93, 63, 211, 0.7))',
                duration: 1,
                ease: 'elastic.out(1, 0.5)',
                stagger: 0.1
            });
            
            gsap.to(panel.querySelector('.feature-number'), {
                scale: 1.2,
                opacity: 0.2,
                duration: 0.5,
                ease: 'power2.out'
            });
            
            gsap.to(panel.querySelector('.feature-icon'), {
                scale: 1.2,
                color: '#A58BFF',
                textShadow: '0 0 20px rgba(93, 63, 211, 0.7)',
                duration: 0.5,
                ease: 'power2.out'
            });
        });
        
        panel.addEventListener('mouseleave', function() {
            gsap.to(svgElements, {
                scale: 1,
                rotation: 0,
                filter: 'drop-shadow(0 0 10px rgba(93, 63, 211, 0.2))',
                duration: 0.7,
                ease: 'power2.out',
                stagger: 0.05
            });
            
            gsap.to(panel.querySelector('.feature-number'), {
                scale: 1,
                opacity: 0.1,
                duration: 0.5,
                ease: 'power2.out'
            });
            
            gsap.to(panel.querySelector('.feature-icon'), {
                scale: 1,
                color: '#5D3FD3',
                textShadow: 'none',
                duration: 0.5,
                ease: 'power2.out'
            });
        });
        
        // Add scroll-driven animation to each blob in feature panels
        svgElements.forEach((svg, i) => {
            // Create a timeline for each blob
            const tl = gsap.timeline({
                scrollTrigger: {
                    trigger: panel,
                    containerAnimation: ScrollTrigger.getById('horizontal-section'),
                    start: "center 75%",
                    end: "right left",
                    scrub: 1,
                    // markers: true, // Uncomment to debug trigger points
                    onUpdate: (self) => {
                        // Dynamically change filter stdDeviation based on progress
                        const progress = self.progress;
                        const filterElement = svg.querySelector('filter feGaussianBlur');
                        if (filterElement) {
                            gsap.set(filterElement, { 
                                attr: { 
                                    stdDeviation: 2 + (progress * 5) 
                                } 
                            });
                        }
                        
                        // Change radial/linear gradient parameters
                        const gradientElement = svg.querySelector('linearGradient, radialGradient');
                        if (gradientElement) {
                            // More dynamic transformations based on scroll position
                            const stops = gradientElement.querySelectorAll('stop');
                            if (stops.length > 1) {
                                // Create a shifting color effect
                                const baseColor = stops[0].getAttribute('stop-color');
                                const targetColor = stops[stops.length-1].getAttribute('stop-color');
                                
                                // Create intermediate color variations based on scroll
                                const midColor = gsap.utils.interpolate(baseColor, targetColor, progress);
                                if (stops.length > 2) {
                                    gsap.set(stops[1], { attr: { 'stop-color': midColor } });
                                }
                            }
                        }
                    }
                }
            });
            
            // Add distortion, scale and rotation animations with variations based on panel index
            tl.to(svg, {
                rotation: i % 2 === 0 ? 20 + (index * 5) : -20 - (index * 5), // Variation by panel index
                scale: i % 2 === 0 ? 1.15 + (index * 0.05) : 0.85 - (index * 0.05),
                y: i % 2 === 0 ? -40 - (index * 10) : 40 + (index * 10),
                x: i % 2 === 0 ? 30 + (index * 5) : -30 - (index * 5),
                transformOrigin: i % 2 === 0 ? '70% 30%' : '30% 70%',
                duration: 1,
                ease: "power2.inOut"
            });
        });
        
        // Feature content animations - enhanced with sequence
        const contentTimeline = gsap.timeline({
            scrollTrigger: {
                trigger: panel,
                containerAnimation: ScrollTrigger.getById('horizontal-section'),
                start: "25% center",
                end: "75% center",
                scrub: 1,
                toggleActions: "play none none reverse",
            }
        });
        
        // Animate the content elements with enhanced staggered effect
        contentTimeline
            .fromTo(panel.querySelector('.feature-number'), 
                {
                    scale: 0.8,
                    opacity: 0,
                    x: index % 2 === 0 ? -100 : 100
                },
                {
                    scale: 1,
                    opacity: 0.1,
                    x: 0,
                    duration: 0.4,
                    ease: "back.out(1.7)"
                }
            )
            .fromTo(panel.querySelector('.feature-icon'), 
                {
                    scale: 0.5,
                    opacity: 0,
                    rotationY: index % 2 === 0 ? -90 : 90 // Flip effect
                },
                {
                    scale: 1,
                    opacity: 1,
                    rotationY: 0,
                    duration: 0.4,
                    ease: "back.out(1.7)"
                }, 
                "-=0.2"
            )
            .fromTo(panel.querySelector('.feature-content h2'), 
                { 
                    y: 50, 
                    opacity: 0,
                    clipPath: "polygon(0 0, 0 0, 0 100%, 0% 100%)" // Text reveal effect
                },
                {
                    y: 0,
                    opacity: 1,
                    clipPath: "polygon(0 0, 100% 0, 100% 100%, 0% 100%)",
                    duration: 0.5,
                    ease: "power2.out"
                }, 
                "-=0.1"
            )
            .fromTo(panel.querySelector('.feature-content p'), 
                { 
                    y: 30, 
                    opacity: 0,
                    clipPath: "polygon(0 0, 0 0, 0 100%, 0% 100%)"
                },
                {
                    y: 0,
                    opacity: 1,
                    clipPath: "polygon(0 0, 100% 0, 100% 100%, 0% 100%)",
                    duration: 0.5,
                    ease: "power2.out"
                }, 
                "-=0.3"
            )
            .fromTo(panel.querySelector('.feature-content .btn'), 
                { 
                    y: 20, 
                    opacity: 0,
                    scale: 0.9
                },
                {
                    y: 0,
                    opacity: 1,
                    scale: 1,
                    duration: 0.4,
                    ease: "back.out(1.7)"
                }, 
                "-=0.2"
            );
        
        // Add floating animation for feature icons (continuous)
        gsap.to(panel.querySelector('.feature-icon'), {
            y: -10,
            duration: 2 + (index * 0.5),
            ease: 'sine.inOut',
            repeat: -1,
            yoyo: true
        });
    });

    // Enhance CTA section animations
    // Enhanced CTA animations for blobs with more complex effects
    const ctaBlobs = document.querySelectorAll('.cta-svg-element');

    ctaBlobs.forEach((blob, index) => {
        const isFirst = index === 0;
        
        // More complex animation timeline
        const tl = gsap.timeline({
            scrollTrigger: {
                trigger: '.cta-section',
                start: 'top bottom',
                end: 'center center',
                scrub: true,
                onUpdate: (self) => {
                    // Dynamic filter and gradient updates
                    const progress = self.progress;
                    const filterElement = blob.querySelector('filter feGaussianBlur');
                    
                    if (filterElement) {
                        const maxGlow = isFirst ? 12 : 9; // Increased glow for more dramatic effect
                        const minGlow = isFirst ? 5 : 3;
                        gsap.set(filterElement, { 
                            attr: { stdDeviation: minGlow + (progress * (maxGlow - minGlow)) }
                        });
                    }
                    
                    // Enhanced gradient animation
                    const gradientElement = blob.querySelector('linearGradient, radialGradient');
                    if (gradientElement) {
                        const stops = gradientElement.querySelectorAll('stop');
                        if (stops.length > 1) {
                            // Create a color shift effect from purple to more vibrant purple
                            const startColor = isFirst ? '#A58BFF' : '#8B6FFF';
                            const endColor = isFirst ? '#D5BAFF' : '#BCA2FF';
                            
                            const newColor = gsap.utils.interpolate(startColor, endColor, progress);
                            gsap.set(stops[0], { attr: { 'stop-color': newColor } });
                            
                            // Update position of radial gradient
                            if (gradientElement.tagName === 'radialGradient') {
                                const newFx = 50 - (progress * 20);
                                const newFy = 50 - (progress * 20);
                                
                                gsap.set(gradientElement, {
                                    attr: {
                                        fx: `${newFx}%`,
                                        fy: `${newFy}%`
                                    }
                                });
                            }
                        }
                    }
                }
            }
        });
        
        // Add enhanced layered animations
        tl.to(blob, {
            y: isFirst ? -140 : 140, // More extreme movement
            x: isFirst ? 90 : -100,
            rotation: isFirst ? 45 : -35, // More rotation
            scale: isFirst ? 1.6 : 0.7, // More extreme scaling
            transformOrigin: isFirst ? '60% 40%' : '40% 60%',
            ease: 'power1.inOut'
        });
        
        // Add a hover effect for blob interaction
        blob.addEventListener('mouseenter', function() {
            gsap.to(this, {
                scale: isFirst ? 1.7 : 0.8,
                rotation: isFirst ? 55 : -45,
                filter: `drop-shadow(0 0 ${isFirst ? 30 : 20}px rgba(93, 63, 211, 0.7))`,
                duration: 0.8,
                ease: 'elastic.out(1, 0.5)'
            });
        });
        
        blob.addEventListener('mouseleave', function() {
            gsap.to(this, {
                scale: isFirst ? 1.6 : 0.7,
                rotation: isFirst ? 45 : -35,
                filter: `drop-shadow(0 0 ${isFirst ? 20 : 15}px rgba(93, 63, 211, 0.4))`,
                duration: 0.5,
                ease: 'power2.out'
            });
        });
    });

    // CTA content entrance animation
    gsap.timeline({
        scrollTrigger: {
            trigger: '.cta-section',
            start: 'top 80%',
            end: 'center center',
            toggleActions: 'play none none none'
        }
    })
    .from('.cta-content h2', {
        y: 100,
        opacity: 0,
        clipPath: "polygon(0 0, 100% 0, 100% 0, 0 0)",
        duration: 1,
        ease: 'power4.out'
    })
    .from('.cta-content p', {
        y: 50,
        opacity: 0,
        clipPath: "polygon(0 0, 100% 0, 100% 0, 0 0)",
        duration: 0.8,
        ease: 'power3.out'
    }, '-=0.6')
    .from('.cta-buttons .btn:first-child', {
        x: -50,
        opacity: 0,
        scale: 0.8,
        duration: 0.6,
        ease: 'back.out(1.7)'
    }, '-=0.4')
    .from('.cta-buttons .btn:last-child', {
        x: 50,
        opacity: 0,
        scale: 0.8,
        duration: 0.6,
        ease: 'back.out(1.7)'
    }, '-=0.5');

    // Animated background effect for CTA section
    function createParticles() {
        const ctaSection = document.querySelector('.cta-section');
        const particlesContainer = document.createElement('div');
        particlesContainer.className = 'particles-container';
        particlesContainer.style.position = 'absolute';
        particlesContainer.style.top = '0';
        particlesContainer.style.left = '0';
        particlesContainer.style.width = '100%';
        particlesContainer.style.height = '100%';
        particlesContainer.style.overflow = 'hidden';
        particlesContainer.style.pointerEvents = 'none';
        particlesContainer.style.zIndex = '1';
        
        ctaSection.insertBefore(particlesContainer, ctaSection.firstChild);
        
        // Create particles
        for (let i = 0; i < 30; i++) {
            const particle = document.createElement('div');
            particle.className = 'cta-particle';
            particle.style.position = 'absolute';
            particle.style.borderRadius = '50%';
            particle.style.backgroundColor = 'rgba(93, 63, 211, 0.3)';
            
            // Random size
            const size = Math.random() * 10 + 5;
            particle.style.width = `${size}px`;
            particle.style.height = `${size}px`;
            
            // Random position
            particle.style.left = `${Math.random() * 100}%`;
            particle.style.top = `${Math.random() * 100}%`;
            
            // Random opacity
            particle.style.opacity = Math.random() * 0.5 + 0.2;
            
            particlesContainer.appendChild(particle);
            
            // Animate each particle
            gsap.to(particle, {
                y: Math.random() * 300 - 150,
                x: Math.random() * 300 - 150,
                scale: Math.random() * 1.5 + 0.5,
                opacity: Math.random() * 0.7,
                duration: Math.random() * 10 + 10,
                repeat: -1,
                yoyo: true,
                ease: 'sine.inOut',
                delay: Math.random() * 5
            });
        }
    }

    // Call the function to create particles
    createParticles();

    // Add animation for the last feature panel's SVG that extends past its section
    document.querySelectorAll('#feature4 .feature-svg-element').forEach((svg, i) => {
        // Create a timeline for blobs that extend to the next section
        gsap.timeline({
            scrollTrigger: {
                trigger: '#feature4',
                containerAnimation: ScrollTrigger.getById('horizontal-section'),
                start: "left right",
                end: "right -30%", // Extend end point past the panel boundary
                scrub: 1,
                onUpdate: (self) => {
                    // Similar update effects as other blobs
                    const progress = self.progress;
                    const filterElement = svg.querySelector('filter feGaussianBlur');
                    if (filterElement) {
                        gsap.set(filterElement, { 
                            attr: { 
                                stdDeviation: 2 + (progress * 7) // Increase glow range
                            } 
                        });
                    }
                }
            }
        }).to(svg, {
            rotation: i % 2 === 0 ? 30 : -30,
            scale: i % 2 === 0 ? 1.3 : 0.8,
            y: i % 2 === 0 ? -70 : 70, // More extreme movement
            x: i % 2 === 0 ? 50 : -50,
            transformOrigin: i % 2 === 0 ? '70% 30%' : '30% 70%',
            ease: "power2.inOut"
        });
    });

    // Helper function untuk transisi 3D yang smooth
    function createSmoothTransition(element, options = {}) {
        // Default options
        const defaults = {
            maxRotationX: 10,
            maxRotationY: -15,
            scale: 0.9,
            opacity: 0.7,
            duration: 1.5,
            perspective: 1000,
            baseScroll: 0.5
        };
        
        // Merge options
        const settings = {...defaults, ...options};
        
        // Ambil awal posisi transformasi
        let initialTransform = {
            rotationX: 0,
            rotationY: 0,
            scale: 1,
            opacity: 1
        };
        
        // Buat timeline dengan konfigurasi scroll
        return gsap.timeline({
            scrollTrigger: {
                trigger: element,
                start: "top top",
                end: "bottom top",
                scrub: settings.baseScroll,
                ease: "power1.inOut",
                onEnter: () => {
                    // Optional start callback
                    if (options.onEnter) options.onEnter();
                },
                onLeave: () => {
                    // Optional end callback
                    if (options.onLeave) options.onLeave();
                },
                onUpdate: (self) => {
                    // Update perspektif berdasarkan progress
                    const progress = self.progress;
                    const dynamicPerspective = settings.perspective - (progress * 200);
                    
                    // Fungsi easing kustom (smoothstep)
                    const smootherProgress = progress < 0.5 
                        ? 2 * progress * progress 
                        : 1 - Math.pow(-2 * progress + 2, 2) / 2;
                    
                    // Update variabel CSS untuk smooth transition
                    gsap.set(element, { 
                        perspective: dynamicPerspective,
                        '--progress': smootherProgress
                    });
                    
                    // Sedikit variasi pada rotasi berdasarkan arah scroll
                    if (options.onProgress) options.onProgress(smootherProgress, self.direction);
                }
            }
        }).to(element, {
            rotationX: settings.maxRotationX,
            rotationY: settings.maxRotationY,
            scale: settings.scale,
            opacity: settings.opacity,
            duration: settings.duration,
            ease: "power2.inOut" 
        });
    }

    // Add this after the initThreeJS function
    function updateBackgroundForTheme() {
        if (!scene || !renderer) return;
        
        // Update particle colors
        if (particles && particlesMaterial) {
            const count = particles.geometry.attributes.color.count;
            const colors = particles.geometry.attributes.color.array;
            
            // Set random colors for particles
            for (let i = 0; i < count; i++) {
                const i3 = i * 3;
                colors[i3] = Math.random(); // Red
                colors[i3 + 1] = Math.random(); // Green
                colors[i3 + 2] = Math.random(); // Blue
            }
            
            // Update the colors
            particles.geometry.attributes.color.needsUpdate = true;
            
            // Standard particle settings
            particlesMaterial.size = 0.05;
            particlesMaterial.opacity = 1.0;
        }
        
        // Force a re-render
        if (renderer) {
            renderer.render(scene, camera);
        }
    }

    // Make it available globally
    window.updateBackgroundForTheme = updateBackgroundForTheme;

    // Initialize particles
    const originalOnload = window.onload || function() {};
    window.onload = function() {
        // Call the original onload function
        if (typeof originalOnload === 'function') {
            originalOnload();
        }
        
        // Apply particle colors
        setTimeout(function() {
            if (window.updateBackgroundForTheme) {
                window.updateBackgroundForTheme();
            }
        }, 500);
    };

    // Call the initPage function to initialize the page
    initPage();
});

