// Smart Attendance System - Enhanced JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initAnimations();
    initThemeSystem();
    initInteractiveElements();
    initNotifications();
});

// Animation System
function initAnimations() {
    // Initialize AOS
    AOS.init({
        duration: 800,
        once: true,
        offset: 100
    });

    // Floating elements
    const floatingElements = document.querySelectorAll('.floating');
    floatingElements.forEach((el, index) => {
        el.style.animationDelay = `${index * 0.5}s`;
    });

    // Pulse animations
    const pulseElements = document.querySelectorAll('.pulse-glow');
    pulseElements.forEach((el, index) => {
        el.style.animationDelay = `${index * 0.3}s`;
    });
}

// Theme System
function initThemeSystem() {
    const themeToggle = document.getElementById('themeToggle');
    const sunIcon = themeToggle.querySelector('[data-lucide="sun"]');
    const moonIcon = themeToggle.querySelector('[data-lucide="moon"]');
    
    // Check saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);

    themeToggle.addEventListener('click', function() {
        const currentTheme = document.body.classList.contains('dark') ? 'dark' : 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        setTheme(newTheme);
    });

    function setTheme(theme) {
        if (theme === 'dark') {
            document.body.classList.add('dark');
            sunIcon.classList.remove('hidden');
            moonIcon.classList.add('hidden');
        } else {
            document.body.classList.remove('dark');
            sunIcon.classList.add('hidden');
            moonIcon.classList.remove('hidden');
        }
        localStorage.setItem('theme', theme);
    }
}

// Interactive Elements
function initInteractiveElements() {
    // File upload enhancements
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const files = e.target.files;
            const container = this.closest('.file-upload-container') || this.parentElement;
            
            // Create preview if image
            if (files.length > 0 && files[0].type.startsWith('image/')) {
                createImagePreview(files[0], container);
            }
            
            // Add file count badge
            addFileCountBadge(files.length, container);
        });
    });

    // Progress bars animation
    animateProgressBars();
    
    // Count-up animations for stats
    animateStatistics();
}

// Image Preview System
function createImagePreview(file, container) {
    const reader = new FileReader();
    reader.onload = function(e) {
        // Remove existing preview
        const existingPreview = container.querySelector('.image-preview');
        if (existingPreview) existingPreview.remove();

        // Create new preview
        const preview = document.createElement('div');
        preview.className = 'image-preview relative mt-4';
        preview.innerHTML = `
            <img src="${e.target.result}" class="w-full h-48 object-cover rounded-lg shadow-lg">
            <button type="button" class="absolute top-2 right-2 bg-red-500 text-white p-1 rounded-full" onclick="this.parentElement.remove()">
                <i data-lucide="x" class="w-4 h-4"></i>
            </button>
        `;
        container.appendChild(preview);
        lucide.createIcons();
    };
    reader.readAsDataURL(file);
}

// File Count Badge
function addFileCountBadge(count, container) {
    let badge = container.querySelector('.file-count-badge');
    if (!badge) {
        badge = document.createElement('span');
        badge.className = 'file-count-badge absolute -top-2 -right-2 bg-indigo-500 text-white text-xs rounded-full w-6 h-6 flex items-center justify-center';
        container.style.position = 'relative';
        container.appendChild(badge);
    }
    badge.textContent = count;
    badge.classList.toggle('hidden', count === 0);
}

// Progress Bars Animation
function animateProgressBars() {
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        const width = bar.style.width;
        bar.style.width = '0%';
        setTimeout(() => {
            bar.style.width = width;
            bar.style.transition = 'width 2s ease-in-out';
        }, 500);
    });
}

// Statistics Animation
function animateStatistics() {
    const stats = document.querySelectorAll('.stat-number');
    stats.forEach(stat => {
        const finalValue = parseInt(stat.textContent);
        let current = 0;
        const increment = finalValue / 50;
        const timer = setInterval(() => {
            current += increment;
            if (current >= finalValue) {
                stat.textContent = finalValue;
                clearInterval(timer);
            } else {
                stat.textContent = Math.floor(current);
            }
        }, 30);
    });
}

// Notification System
function initNotifications() {
    // Auto-hide flash messages
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            message.style.transform = 'translateY(-20px)';
            setTimeout(() => message.remove(), 300);
        }, 5000);
    });

    // Success confetti
    const successMessages = document.querySelectorAll('.alert-success');
    successMessages.forEach(() => {
        confetti({
            particleCount: 100,
            spread: 70,
            origin: { y: 0.6 }
        });
    });
}

// Form Validation Enhancement
function enhanceFormValidation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('error');
                    isValid = false;
                    
                    // Add error animation
                    field.animate([
                        { transform: 'translateX(0px)' },
                        { transform: 'translateX(-10px)' },
                        { transform: 'translateX(10px)' },
                        { transform: 'translateX(0px)' }
                    ], {
                        duration: 500
                    });
                } else {
                    field.classList.remove('error');
                }
            });

            if (!isValid) {
                e.preventDefault();
                
                // Show error message
                showNotification('Please fill all required fields', 'error');
            }
        });
    });
}

// Custom Notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-lg glass-effect text-white z-50 transform translate-x-full transition-transform ${type === 'error' ? 'bg-red-500/20' : 'bg-green-500/20'}`;
    notification.innerHTML = `
        <div class="flex items-center space-x-3">
            <i data-lucide="${type === 'error' ? 'alert-circle' : 'check-circle'}" class="w-5 h-5"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(notification);
    lucide.createIcons();
    
    // Animate in
    setTimeout(() => notification.classList.remove('translate-x-full'), 100);
    
    // Auto remove
    setTimeout(() => {
        notification.classList.add('translate-x-full');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Export functions for global use
window.toggleSidebar = function() {
    document.querySelector('.fixed.left-0').classList.toggle('-translate-x-full');
};

window.showNotification = showNotification;