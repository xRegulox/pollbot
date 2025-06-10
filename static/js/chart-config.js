/**
 * Regulo PollBot - Chart Configuration
 * 
 * This file contains global Chart.js configuration settings
 * for consistent styling across the application.
 */

// Set default Chart.js configuration
Chart.defaults.color = '#ffffff';
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';

// Discord-themed color palette
const DISCORD_COLORS = {
    blurple: '#5865F2',
    green: '#57F287',
    yellow: '#FEE75C',
    fuchsia: '#EB459E',
    red: '#ED4245',
    white: '#FFFFFF',
    black: '#000000',
    darkButNotBlack: '#2C2F33',
    notQuiteBlack: '#23272A',
    greyple: '#99AAB5',
    darkTheme: {
        primary: '#36393F',
        secondary: '#2F3136',
        tertiary: '#202225'
    }
};

// Color arrays for charts
const DEFAULT_COLORS = [
    DISCORD_COLORS.blurple,
    DISCORD_COLORS.green,
    DISCORD_COLORS.yellow,
    DISCORD_COLORS.fuchsia,
    DISCORD_COLORS.red,
    '#9B59B6', // Purple
    '#3498DB', // Blue
    '#2ECC71', // Green
    '#F1C40F', // Yellow
    '#E74C3C'  // Red
];

// Configure default chart styles
const configureCharts = function() {
    // Apply Discord dark theme to all charts
    Chart.defaults.backgroundColor = 'rgba(255, 255, 255, 0.1)';
    Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';
    Chart.defaults.color = '#ffffff';
    
    // Get user preferences
    const preferences = JSON.parse(localStorage.getItem('dashboardPreferences') || '{}');
    const enableAnimations = preferences.enableAnimations !== undefined ? preferences.enableAnimations : true;
    
    // Configure global defaults for all chart types
    Chart.defaults.animation = enableAnimations ? {
        duration: 1000,
        easing: 'easeOutQuad'
    } : false;
    
    // Bar chart defaults
    Chart.defaults.elements.bar.borderWidth = 1;
    Chart.defaults.elements.bar.borderRadius = 4;
    
    // Line chart defaults
    Chart.defaults.elements.line.tension = 0.3;
    Chart.defaults.elements.line.borderWidth = 2;
    Chart.defaults.elements.point.radius = 3;
    
    // Pie chart defaults
    Chart.defaults.elements.arc.borderWidth = 1;
    Chart.defaults.elements.arc.borderColor = DISCORD_COLORS.darkTheme.primary;
    
    // Configure tooltips
    Chart.defaults.plugins.tooltip = {
        backgroundColor: DISCORD_COLORS.darkTheme.tertiary,
        titleColor: DISCORD_COLORS.white,
        bodyColor: DISCORD_COLORS.white,
        borderColor: DISCORD_COLORS.darkTheme.primary,
        borderWidth: 1,
        cornerRadius: 6,
        displayColors: true,
        enabled: preferences.showTooltips !== undefined ? preferences.showTooltips : true,
        mode: 'index',
        intersect: false,
        padding: 10
    };
    
    // Configure legends
    Chart.defaults.plugins.legend = {
        display: true,
        position: 'top',
        align: 'center',
        labels: {
            boxWidth: 12,
            padding: 15,
            usePointStyle: false
        }
    };
    
    // Configure scales
    Chart.defaults.scales.linear = {
        grid: {
            color: 'rgba(255, 255, 255, 0.1)',
            drawBorder: false
        },
        ticks: {
            padding: 8
        }
    };
    
    Chart.defaults.scales.category = {
        grid: {
            drawBorder: false,
            drawOnChartArea: false
        },
        ticks: {
            padding: 8
        }
    };
    
    // Configure responsiveness
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.responsive = true;
    Chart.defaults.layout = {
        padding: {
            top: 10,
            right: 16,
            bottom: 10,
            left: 16
        }
    };
};

// Initialize chart configuration on page load
document.addEventListener('DOMContentLoaded', configureCharts);

/**
 * Creates a bar chart with Discord-themed styling
 * 
 * @param {string} elementId - The canvas element ID
 * @param {array} labels - Array of labels
 * @param {array} data - Array of data points
 * @param {object} options - Additional options to override defaults
 * @returns {Chart} The configured Chart.js instance
 */
function createBarChart(elementId, labels, data, options = {}) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: options.label || 'Votes',
                data: data,
                backgroundColor: options.colors || DEFAULT_COLORS,
                borderColor: options.borderColors || DEFAULT_COLORS.map(color => color + '88'),
                borderWidth: 1
            }]
        },
        options: {
            ...options,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

/**
 * Creates a pie chart with Discord-themed styling
 * 
 * @param {string} elementId - The canvas element ID
 * @param {array} labels - Array of labels
 * @param {array} data - Array of data points
 * @param {object} options - Additional options to override defaults
 * @returns {Chart} The configured Chart.js instance
 */
function createPieChart(elementId, labels, data, options = {}) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: options.colors || DEFAULT_COLORS,
                borderColor: DISCORD_COLORS.darkTheme.primary,
                borderWidth: 1
            }]
        },
        options: {
            ...options,
            plugins: {
                legend: {
                    position: 'right',
                    align: 'start'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const value = context.raw;
                            const percentage = Math.round((value / total) * 100);
                            return `${context.label}: ${value} votes (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Creates a line chart with Discord-themed styling
 * 
 * @param {string} elementId - The canvas element ID
 * @param {array} labels - Array of labels
 * @param {array} datasets - Array of dataset objects
 * @param {object} options - Additional options to override defaults
 * @returns {Chart} The configured Chart.js instance
 */
function createLineChart(elementId, labels, datasets, options = {}) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Add Discord colors to datasets if not specified
    const styledDatasets = datasets.map((dataset, index) => {
        const color = DEFAULT_COLORS[index % DEFAULT_COLORS.length];
        return {
            ...dataset,
            borderColor: dataset.borderColor || color,
            backgroundColor: dataset.backgroundColor || color + '22',
            pointBackgroundColor: dataset.pointBackgroundColor || color,
            pointBorderColor: dataset.pointBorderColor || DISCORD_COLORS.white,
            pointHoverBackgroundColor: dataset.pointHoverBackgroundColor || DISCORD_COLORS.white,
            pointHoverBorderColor: dataset.pointHoverBorderColor || color
        };
    });
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: styledDatasets
        },
        options: options
    });
}
