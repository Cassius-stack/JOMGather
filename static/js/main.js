/* MySavvyGranny Custom JavaScript */

// Document ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('MySavvyGranny loaded successfully!');
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
});

// TODO: Add custom JavaScript functions as needed by team members
