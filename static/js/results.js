/**
 * Regulo PollBot - Results JavaScript
 * Handles the poll results visualization and data exports
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get user preferences
    const preferences = JSON.parse(localStorage.getItem('dashboardPreferences') || '{}');
    const enableAnimations = preferences.enableAnimations !== undefined ? preferences.enableAnimations : true;
    
    // Initialize charts if they exist on the page
    initializeCharts();
    
    // Setup export functionality
    setupExportButtons();
    
    // Add live updates for active polls if desired
    setupLiveUpdates();
    
    /**
     * Initializes the chart visualizations
     * Charts are already configured in the template, this just adds extra functionality
     */
    function initializeCharts() {
        // Charts are created in the template using Chart.js
        // This function adds extra functionality or customizations
        
        const barChart = Chart.getChart('barChart');
        const pieChart = Chart.getChart('pieChart');
        
        if (barChart && enableAnimations) {
            // Add animation to bar chart if animations are enabled
            barChart.options.animation = {
                duration: 1000,
                easing: 'easeOutQuad'
            };
            barChart.update();
        }
        
        if (pieChart && enableAnimations) {
            // Add animation to pie chart if animations are enabled
            pieChart.options.animation = {
                animateRotate: true,
                animateScale: true,
                duration: 1000
            };
            pieChart.update();
        }
    }
    
    /**
     * Sets up the export functionality for poll results
     */
    function setupExportButtons() {
        // Export buttons already have the proper href links in the template
        // This function could add extra functionality if needed
        
        // For example, add click tracking or confirmation dialogs
        const exportButtons = document.querySelectorAll('a[href*="export/poll"]');
        exportButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                // You could add analytics tracking here
                console.log('Exporting poll data:', this.href);
                
                // For example, you could show a toast notification
                showToast('Preparing download...');
            });
        });
    }
    
    /**
     * Sets up live updates for active polls
     */
    function setupLiveUpdates() {
        // Get poll ID from the page
        const pollIdMatch = window.location.pathname.match(/\/poll\/(\d+)/);
        if (!pollIdMatch) return;
        
        const pollId = pollIdMatch[1];
        const pollStatusBadge = document.querySelector('.badge');
        
        // Only set up live updates for active polls
        if (pollStatusBadge && pollStatusBadge.textContent.trim() === 'Active') {
            // Poll for updates every 10 seconds
            const updateInterval = setInterval(() => {
                fetch(`/poll/${pollId}/data`)
                    .then(response => {
                        if (!response.ok) {
                            // If poll is no longer active, stop polling
                            if (response.status === 404) {
                                clearInterval(updateInterval);
                            }
                            throw new Error('Network response was not ok');
                        }
                        return response.json();
                    })
                    .then(data => {
                        // Update charts with new data
                        updateChartData(data);
                        
                        // Update results summary
                        updateResultsSummary(data);
                        
                        // If poll is now closed, refresh the page
                        if (data.status === 'closed') {
                            window.location.reload();
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching poll updates:', error);
                    });
            }, 10000); // Check every 10 seconds
            
            // Clean up interval when leaving the page
            window.addEventListener('beforeunload', () => {
                clearInterval(updateInterval);
            });
        }
    }
    
    /**
     * Updates chart data with new results
     */
    function updateChartData(data) {
        // This would update the charts with new data from an API call
        // For example:
        const barChart = Chart.getChart('barChart');
        const pieChart = Chart.getChart('pieChart');
        
        if (barChart && data.results) {
            barChart.data.datasets[0].data = Object.values(data.results);
            barChart.update();
        }
        
        if (pieChart && data.results) {
            pieChart.data.datasets[0].data = Object.values(data.results);
            pieChart.update();
        }
    }
    
    /**
     * Updates the results summary section with new data
     */
    function updateResultsSummary(data) {
        // Update total votes
        const totalVotesElement = document.querySelector('.display-4');
        if (totalVotesElement && data.total_votes !== undefined) {
            totalVotesElement.textContent = data.total_votes;
        }
        
        // Update progress bars and percentages
        if (data.results && data.options) {
            const listItems = document.querySelectorAll('.list-group-item');
            
            data.options.forEach((option, index) => {
                if (index < listItems.length) {
                    const votes = data.results[option] || 0;
                    const percentage = data.total_votes > 0 ? (votes / data.total_votes * 100) : 0;
                    
                    // Update vote count badge
                    const badge = listItems[index].querySelector('.badge');
                    if (badge) {
                        badge.textContent = `${votes} vote${votes !== 1 ? 's' : ''}`;
                    }
                    
                    // Update progress bar
                    const progressBar = listItems[index].querySelector('.progress-bar');
                    if (progressBar) {
                        progressBar.style.width = `${percentage}%`;
                        progressBar.setAttribute('aria-valuenow', percentage);
                    }
                    
                    // Update percentage text
                    const percentageText = listItems[index].querySelector('.small');
                    if (percentageText) {
                        percentageText.textContent = `${percentage.toFixed(1)}%`;
                    }
                }
            });
        }
        
        // If votes table exists and it's not an anonymous poll, update that too
        if (!data.is_anonymous && data.votes) {
            const votesTable = document.querySelector('table tbody');
            if (votesTable) {
                // This would be more complex, requiring rebuilding the table
                // For simplicity, we would just refresh the page if votes change significantly
            }
        }
    }
    
    /**
     * Shows a toast notification
     */
    function showToast(message) {
        // Create toast element
        const toastContainer = document.createElement('div');
        toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '5';
        
        toastContainer.innerHTML = `
            <div class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header">
                    <strong class="me-auto">Regulo PollBot</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        document.body.appendChild(toastContainer);
        
        // Remove after 3 seconds
        setTimeout(() => {
            const toast = new bootstrap.Toast(toastContainer.querySelector('.toast'));
            toast.hide();
            // Remove from DOM after hiding
            toast._element.addEventListener('hidden.bs.toast', () => {
                toastContainer.remove();
            });
        }, 3000);
    }
});
