/**
 * Regulo PollBot - Dashboard JavaScript
 * Provides interactive functionality for the dashboard page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Load user preferences
    const preferences = JSON.parse(localStorage.getItem('dashboardPreferences') || '{}');
    const enableAnimations = preferences.enableAnimations !== undefined ? preferences.enableAnimations : true;
    
    // Set up activity chart
    setupActivityChart();
    
    // Initialize any tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Check for notifications (polls ending soon, etc.)
    checkNotifications();
    
    /**
     * Sets up the activity chart on the dashboard
     */
    function setupActivityChart() {
        const ctx = document.getElementById('activityChart');
        if (!ctx) return;
        
        // Parse data from server (already added in template)
        // Chart rendering is handled in the dashboard.html template
    }
    
    /**
     * Checks for notifications like polls ending soon
     */
    function checkNotifications() {
        // This would typically fetch from an API endpoint
        // For now, we'll just simulate this
        console.log('Checking for notifications...');
        
        // You could add a notification system here
        // Example:
        /*
        fetch('/api/notifications')
            .then(response => response.json())
            .then(data => {
                if (data.notifications.length > 0) {
                    showNotifications(data.notifications);
                }
            });
        */
    }
    
    /**
     * Updates stats cards with current data
     */
    function updateStats() {
        // Refresh dashboard stats every minute
        setInterval(() => {
            fetch('/api/dashboard/stats')
                .then(response => response.json())
                .then(data => {
                    // Update stats cards with new data
                    document.getElementById('total-polls').textContent = data.total_polls;
                    document.getElementById('active-polls').textContent = data.active_polls;
                    document.getElementById('total-votes').textContent = data.total_votes;
                    document.getElementById('total-servers').textContent = data.total_servers;
                })
                .catch(error => console.error('Error fetching stats:', error));
        }, 60000); // Update every minute
    }
    
    // Animate stats cards on page load
    if (enableAnimations) {
        const statCards = document.querySelectorAll('.card');
        statCards.forEach((card, index) => {
            setTimeout(() => {
                card.classList.add('fade-in');
            }, index * 100);
        });
    }
    
    // Set up real-time updates for active polls if WebSockets were implemented
    // This would be a placeholder for future real-time updates
    function setupRealtimeUpdates() {
        // Example WebSocket connection for real-time updates
        // const socket = new WebSocket('ws://' + window.location.host + '/ws');
        // socket.onmessage = function(event) {
        //     const data = JSON.parse(event.data);
        //     if (data.type === 'poll_update') {
        //         updatePollData(data);
        //     }
        // };
    }
});
