// Arabic Learning App - Main JavaScript File

// Auto-hide flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(flash => {
        setTimeout(() => {
            flash.style.opacity = '0';
            setTimeout(() => flash.remove(), 300);
        }, 5000);
    });
});

// Smooth scroll for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// Dashboard chart animations
function animateProgressBars() {
    const bars = document.querySelectorAll('.box-bar');
    bars.forEach((bar, index) => {
        const width = bar.style.width;
        bar.style.width = '0';
        setTimeout(() => {
            bar.style.width = width;
        }, index * 100);
    });
}

// Call on dashboard load
if (document.querySelector('.box-distribution')) {
    animateProgressBars();
}

// Keyboard shortcuts helper
function showKeyboardShortcuts() {
    if (document.querySelector('.flashcard')) {
        console.log('Keyboard Shortcuts:');
        console.log('Space/Enter - Flip card');
        console.log('1 - Forgot');
        console.log('2 - Struggled');
        console.log('3 - Good');
        console.log('4 - Perfect');
    }
}

// Form validation helper
function validatePasswordStrength(password) {
    const requirements = {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        number: /[0-9]/.test(password)
    };
    return requirements;
}

// Display password strength indicator
function updatePasswordStrength(inputId, indicatorId) {
    const input = document.getElementById(inputId);
    const indicator = document.getElementById(indicatorId);
    
    if (input && indicator) {
        input.addEventListener('input', function() {
            const strength = validatePasswordStrength(this.value);
            const passed = Object.values(strength).filter(Boolean).length;
            
            indicator.textContent = `Strength: ${passed}/3`;
            indicator.className = passed === 3 ? 'strong' : passed === 2 ? 'medium' : 'weak';
        });
    }
}

// Local storage for user preferences
const UserPreferences = {
    save: function(key, value) {
        localStorage.setItem('arabic_app_' + key, JSON.stringify(value));
    },
    
    get: function(key) {
        const item = localStorage.getItem('arabic_app_' + key);
        return item ? JSON.parse(item) : null;
    },
    
    remove: function(key) {
        localStorage.removeItem('arabic_app_' + key);
    }
};

// Tooltip functionality
function initTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(element => {
        element.addEventListener('mouseenter', function() {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = this.dataset.tooltip;
            document.body.appendChild(tooltip);
            
            const rect = this.getBoundingClientRect();
            tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + 'px';
            tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
        });
        
        element.addEventListener('mouseleave', function() {
            const tooltip = document.querySelector('.tooltip');
            if (tooltip) tooltip.remove();
        });
    });
}

// Progress tracking for review sessions
class ReviewSessionTracker {
    constructor() {
        this.startTime = Date.now();
        this.cardsReviewed = 0;
        this.scores = [];
    }
    
    addScore(score) {
        this.scores.push(score);
        this.cardsReviewed++;
    }
    
    getAverageScore() {
        if (this.scores.length === 0) return 0;
        return this.scores.reduce((a, b) => a + b, 0) / this.scores.length;
    }
    
    getDuration() {
        return Math.floor((Date.now() - this.startTime) / 1000);
    }
    
    getStats() {
        return {
            duration: this.getDuration(),
            cardsReviewed: this.cardsReviewed,
            averageScore: this.getAverageScore()
        };
    }
}

// Initialize on specific pages
if (document.querySelector('.review-container')) {
    window.sessionTracker = new ReviewSessionTracker();
}
