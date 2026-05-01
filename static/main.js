// Auto-hide flash messages after 5 seconds with a fade-out first - nested setTimeout gives the CSS opacity transition time to play before the element is actually removed from the display
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

// Animate the box distribution bars on the dashboard by resetting their width to 0 and then restoring it, which triggers the CSS transition; the staggered delay (index * 100ms) makes the bars fill in one after another rather than all at once, which makes the progress feel more dynamic and just overall more fun to watch the animation.
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

// Only run on pages that actually have a box distribution section
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

// Checks a password string against the three required rules and returns which ones pass - used by updatePasswordStrength
function validatePasswordStrength(password) {
    const requirements = {
        length:    password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        number:    /[0-9]/.test(password)
    };
    return requirements;
}

// Attaches a live listener to a password input field that updates an indicator element with a Strength: N/3 score as the user types.
// Note: needs to be called with the correct element IDs and those elements need to exist in the HTML for it to have any effect.
function updatePasswordStrength(inputId, indicatorId) {
    const input     = document.getElementById(inputId);
    const indicator = document.getElementById(indicatorId);
    
    if (input && indicator) {
        input.addEventListener('input', function() {
            const strength = validatePasswordStrength(this.value);
            const passed = Object.values(strength).filter(Boolean).length;
            
            indicator.textContent = `Strength: ${passed}/3`;
            // Swap the CSS class so the indicator colour changes with the score - 'strong', 'medium', and 'weak' need corresponding styles in the CSS.
            indicator.className = passed === 3 ? 'strong' : passed === 2 ? 'medium' : 'weak';
        });
    }
}

// Thin wrapper around localStorage that namespaces all keys with 'arabic_app_' to avoid clashing with anything else that might be using localStorage on the same origin.
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

// Positions a tooltip div relative to the triggering element using getBoundingClientRect(), then removes it on mouseleave; the tooltip text comes from the element's data-tooltip attribute so no JavaScript changes needed to add a new tooltip - just adding attribute to the HTML element.
function initTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(element => {
        element.addEventListener('mouseenter', function() {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = this.dataset.tooltip;
            document.body.appendChild(tooltip);
            
            const rect = this.getBoundingClientRect();
            tooltip.style.top  = rect.top - tooltip.offsetHeight - 5 + 'px';
            tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
        });
        
        element.addEventListener('mouseleave', function() {
            const tooltip = document.querySelector('.tooltip');
            if (tooltip) tooltip.remove();
        });
    });
}

// Tracks timing and scores for the current review session so session statistics can be calculated at the end without storing anything server-side.
class ReviewSessionTracker {
    constructor() {
        this.startTime     = Date.now();
        this.cardsReviewed = 0;
        this.scores        = [];
    }
    
    addScore(score) {
        this.scores.push(score);
        this.cardsReviewed++;
    }
    
    getAverageScore() {
        if (this.scores.length === 0) return 0;
        // reduce() sums all scores, then divide by count to get the mean.
        return this.scores.reduce((a, b) => a + b, 0) / this.scores.length;
    }
    
    getDuration() {
        // Converts milliseconds to whole seconds
        return Math.floor((Date.now() - this.startTime) / 1000);
    }
    
    getStats() {
        return {
            duration:      this.getDuration(),
            cardsReviewed: this.cardsReviewed,
            averageScore:  this.getAverageScore()
        };
    }
}

// Attach the tracker to the window object so any other script on the review page can call window.sessionTracker.addScore() after each card is rated.
if (document.querySelector('.review-container')) {
    window.sessionTracker = new ReviewSessionTracker();
}
