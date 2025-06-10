/**
 * Regulo PollBot - Polls JavaScript
 * Handles poll creation, management, and interactive elements
 */

document.addEventListener('DOMContentLoaded', function() {
    // Option management for poll creation
    setupOptionManagement();
    
    // Handle server and channel selection
    setupServerChannelSelection();
    
    // Setup expiration and scheduling UI
    setupExpirationAndScheduling();
    
    // Setup poll preview
    setupPollPreview();
    
    // Setup form validation
    setupFormValidation();
    
    // Setup vote options functionality
    setupVoteOptions();
    
    /**
     * Sets up the add/remove option functionality
     */
    function setupOptionManagement() {
        const optionsContainer = document.getElementById('options-container');
        const addOptionBtn = document.getElementById('add-option');
        
        if (!optionsContainer || !addOptionBtn) return;
        
        let optionCount = optionsContainer.querySelectorAll('.input-group').length;
        
        // Add option button click handler
        addOptionBtn.addEventListener('click', function() {
            optionCount++;
            if (optionCount <= 10) {
                const newOption = document.createElement('div');
                newOption.className = 'input-group mb-2';
                newOption.innerHTML = `
                    <span class="input-group-text">${optionCount}</span>
                    <input type="text" class="form-control" name="option_${optionCount}" 
                        placeholder="Option ${optionCount}" maxlength="1000">
                    <button type="button" class="btn btn-outline-danger remove-option">
                        <i class="bi bi-trash"></i>
                    </button>
                `;
                optionsContainer.appendChild(newOption);
                
                // Update preview
                updatePollPreview();
                
                // If we hit the max, disable the add button
                if (optionCount >= 10) {
                    addOptionBtn.disabled = true;
                }
            }
        });
        
        // Remove option handler (using event delegation)
        optionsContainer.addEventListener('click', function(e) {
            if (e.target.classList.contains('remove-option') || e.target.parentElement.classList.contains('remove-option')) {
                const button = e.target.classList.contains('remove-option') ? e.target : e.target.parentElement;
                button.closest('.input-group').remove();
                
                // Re-number the options
                const options = optionsContainer.querySelectorAll('.input-group');
                options.forEach((option, index) => {
                    const span = option.querySelector('.input-group-text');
                    const input = option.querySelector('input');
                    span.textContent = index + 1;
                    input.name = `option_${index + 1}`;
                    input.placeholder = `Option ${index + 1}`;
                });
                
                optionCount = options.length;
                addOptionBtn.disabled = false;
                
                // Update preview
                updatePollPreview();
            }
        });
    }
    
    /**
     * Sets up the server and channel selection dropdowns
     */
    function setupServerChannelSelection() {
        const serverSelect = document.getElementById('server_id');
        const channelSelect = document.getElementById('channel_id');
        
        if (!serverSelect || !channelSelect) return;
        
        serverSelect.addEventListener('change', function() {
            const serverId = this.value;
            if (serverId) {
                // Enable channel select
                channelSelect.disabled = true;
                channelSelect.innerHTML = '<option value="" selected>Loading channels...</option>';
                
                // Fetch channels for selected server
                fetch(`/get_channels/${serverId}`)
                    .then(response => response.json())
                    .then(channels => {
                        channelSelect.innerHTML = '<option value="" selected>Use default channel</option>';
                        channels.forEach(channel => {
                            const option = document.createElement('option');
                            option.value = channel.id;
                            option.textContent = `#${channel.name}`;
                            channelSelect.appendChild(option);
                        });
                        channelSelect.disabled = false;
                    })
                    .catch(error => {
                        console.error('Error loading channels:', error);
                        channelSelect.innerHTML = '<option value="" selected>Use default channel</option>';
                        channelSelect.disabled = false;
                    });
            } else {
                channelSelect.disabled = false;
                channelSelect.innerHTML = '<option value="" selected>Use default channel</option>';
            }
        });
    }
    
    /**
     * Sets up expiration and scheduling UI interactions
     */
    function setupExpirationAndScheduling() {
        // Expiration type radios
        const noExpiration = document.getElementById('no_expiration');
        const durationExpiration = document.getElementById('duration_expiration');
        const datetimeExpiration = document.getElementById('datetime_expiration');
        const durationInputs = document.getElementById('duration-inputs');
        const datetimeInputs = document.getElementById('datetime-inputs');
        
        if (noExpiration && durationExpiration && datetimeExpiration) {
            noExpiration.addEventListener('change', function() {
                if (this.checked) {
                    durationInputs.style.display = 'none';
                    datetimeInputs.style.display = 'none';
                    updatePollPreview();
                }
            });
            
            durationExpiration.addEventListener('change', function() {
                if (this.checked) {
                    durationInputs.style.display = 'flex';
                    datetimeInputs.style.display = 'none';
                    updatePollPreview();
                }
            });
            
            datetimeExpiration.addEventListener('change', function() {
                if (this.checked) {
                    durationInputs.style.display = 'none';
                    datetimeInputs.style.display = 'flex';
                    updatePollPreview();
                }
            });
        }
        
        // Scheduling type radios
        const postNow = document.getElementById('post_now');
        const postScheduled = document.getElementById('post_scheduled');
        const scheduleInputs = document.getElementById('schedule-inputs');
        
        if (postNow && postScheduled && scheduleInputs) {
            postNow.addEventListener('change', function() {
                if (this.checked) {
                    scheduleInputs.style.display = 'none';
                }
            });
            
            postScheduled.addEventListener('change', function() {
                if (this.checked) {
                    scheduleInputs.style.display = 'flex';
                }
            });
        }
        
        // Initialize date/time inputs with current values
        initializeDateTimeInputs();
    }
    
    /**
     * Initializes date and time inputs with default values
     */
    function initializeDateTimeInputs() {
        const now = new Date();
        const tomorrow = new Date(now);
        tomorrow.setDate(now.getDate() + 1);
        
        // Format dates for input fields
        const formatDate = (date) => {
            return date.toISOString().split('T')[0];
        };
        
        const formatTime = (date) => {
            return date.toTimeString().substring(0, 5);
        };
        
        // Set default values for date and time pickers
        const expirationDate = document.getElementById('expiration_date');
        const expirationTime = document.getElementById('expiration_time');
        const scheduleDate = document.getElementById('schedule_date');
        const scheduleTime = document.getElementById('schedule_time');
        
        if (expirationDate) expirationDate.value = formatDate(tomorrow);
        if (expirationTime) expirationTime.value = formatTime(now);
        if (scheduleDate) scheduleDate.value = formatDate(now);
        if (scheduleTime) scheduleTime.value = formatTime(now);
    }
    
    /**
     * Sets up the live poll preview
     */
    function setupPollPreview() {
        // Poll content inputs
        const questionInput = document.getElementById('question');
        const descriptionInput = document.getElementById('description');
        const allowMultipleCheck = document.getElementById('allow_multiple');
        const isAnonymousCheck = document.getElementById('is_anonymous');
        
        // Poll preview elements
        const previewQuestion = document.getElementById('preview-question');
        const previewDescription = document.getElementById('preview-description');
        const previewOptions = document.getElementById('preview-options');
        
        if (!questionInput || !previewQuestion) return;
        
        // Add event listeners for preview updates
        questionInput.addEventListener('input', updatePollPreview);
        if (descriptionInput) descriptionInput.addEventListener('input', updatePollPreview);
        if (allowMultipleCheck) allowMultipleCheck.addEventListener('change', updatePollPreview);
        if (isAnonymousCheck) isAnonymousCheck.addEventListener('change', updatePollPreview);
        
        // Duration inputs for expiration
        const durationValue = document.getElementById('duration_value');
        const durationUnit = document.getElementById('duration_unit');
        const expirationDate = document.getElementById('expiration_date');
        const expirationTime = document.getElementById('expiration_time');
        
        if (durationValue) durationValue.addEventListener('input', updatePollPreview);
        if (durationUnit) durationUnit.addEventListener('change', updatePollPreview);
        if (expirationDate) expirationDate.addEventListener('input', updatePollPreview);
        if (expirationTime) expirationTime.addEventListener('input', updatePollPreview);
        
        // Initial preview update
        updatePollPreview();
    }
    
    /**
     * Updates the poll preview based on current form values
     */
    function updatePollPreview() {
        const questionInput = document.getElementById('question');
        const descriptionInput = document.getElementById('description');
        const allowMultipleCheck = document.getElementById('allow_multiple');
        const isAnonymousCheck = document.getElementById('is_anonymous');
        
        const previewQuestion = document.getElementById('preview-question');
        const previewDescription = document.getElementById('preview-description');
        const previewOptions = document.getElementById('preview-options');
        
        if (!questionInput || !previewQuestion) return;
        
        // Update question and description
        previewQuestion.textContent = questionInput.value || 'Your question will appear here';
        
        if (descriptionInput) {
            if (descriptionInput.value) {
                previewDescription.textContent = descriptionInput.value;
                previewDescription.style.display = 'block';
            } else {
                previewDescription.textContent = 'Description (optional)';
                previewDescription.style.display = 'block';
            }
        }
        
        // Update options
        if (previewOptions) {
            let optionsHTML = '';
            const emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟'];
            
            const optionsContainer = document.getElementById('options-container');
            if (optionsContainer) {
                const optionInputs = optionsContainer.querySelectorAll('input[type="text"]');
                optionInputs.forEach((input, index) => {
                    optionsHTML += `<div class="mb-1">${emojis[index]} ${input.value || `Option ${index + 1}`}</div>`;
                });
                
                previewOptions.innerHTML = optionsHTML;
            }
        }
        
        // Update footer
        const footerElement = document.querySelector('#poll-preview .text-muted.small');
        if (footerElement) {
            let footerText = [];
            
            if (allowMultipleCheck && allowMultipleCheck.checked) {
                footerText.push('Multiple votes allowed');
            } else {
                footerText.push('One vote per person');
            }
            
            if (isAnonymousCheck && isAnonymousCheck.checked) {
                footerText.push('Votes are anonymous');
            }
            
            // Add expiration info
            const noExpiration = document.getElementById('no_expiration');
            const durationExpiration = document.getElementById('duration_expiration');
            const datetimeExpiration = document.getElementById('datetime_expiration');
            
            if (noExpiration && noExpiration.checked) {
                footerText.push('Closes: Never');
            } else if (durationExpiration && durationExpiration.checked) {
                const durationValue = document.getElementById('duration_value');
                const durationUnit = document.getElementById('duration_unit');
                
                if (durationValue && durationUnit) {
                    const value = durationValue.value || 1;
                    const unit = durationUnit.value || 'days';
                    footerText.push(`Closes: After ${value} ${unit}`);
                }
            } else if (datetimeExpiration && datetimeExpiration.checked) {
                const expirationDate = document.getElementById('expiration_date');
                const expirationTime = document.getElementById('expiration_time');
                
                if (expirationDate && expirationTime) {
                    const date = expirationDate.value;
                    const time = expirationTime.value;
                    if (date && time) {
                        footerText.push(`Closes: ${date} ${time}`);
                    } else {
                        footerText.push('Closes: (set date/time)');
                    }
                }
            }
            
            footerElement.textContent = footerText.join(' • ');
        }
    }
    
    /**
     * Sets up form validation for poll creation
     */
    function setupFormValidation() {
        const form = document.querySelector('form');
        if (!form) return;
        
        form.addEventListener('submit', function(event) {
            // Get the question and first two options
            const question = document.getElementById('question');
            const option1 = document.querySelector('input[name="option_1"]');
            const option2 = document.querySelector('input[name="option_2"]');
            const server = document.getElementById('server_id');
            const channel = document.getElementById('channel_id');
            
            let isValid = true;
            let errorMessage = '';
            
            // Basic validation
            if (!question || !question.value.trim()) {
                isValid = false;
                errorMessage = 'Please enter a question for the poll.';
            } else if (!option1 || !option1.value.trim() || !option2 || !option2.value.trim()) {
                isValid = false;
                errorMessage = 'Please provide at least two options for the poll.';
            // Server and channel validation removed - defaults will be used if empty
            // Updated: Allow empty server/channel for default behavior
            }
            
            // Check scheduling if applicable
            const postScheduled = document.getElementById('post_scheduled');
            if (postScheduled && postScheduled.checked) {
                const scheduleDate = document.getElementById('schedule_date');
                const scheduleTime = document.getElementById('schedule_time');
                
                if (!scheduleDate || !scheduleDate.value || !scheduleTime || !scheduleTime.value) {
                    isValid = false;
                    errorMessage = 'Please set a date and time for the scheduled poll.';
                } else {
                    // Validate that scheduled time is in the future
                    const scheduledDateTime = new Date(`${scheduleDate.value}T${scheduleTime.value}`);
                    if (scheduledDateTime <= new Date()) {
                        isValid = false;
                        errorMessage = 'Scheduled time must be in the future.';
                    }
                }
            }
            
            // Check expiration if applicable
            const datetimeExpiration = document.getElementById('datetime_expiration');
            if (datetimeExpiration && datetimeExpiration.checked) {
                const expirationDate = document.getElementById('expiration_date');
                const expirationTime = document.getElementById('expiration_time');
                
                if (!expirationDate || !expirationDate.value || !expirationTime || !expirationTime.value) {
                    isValid = false;
                    errorMessage = 'Please set an expiration date and time for the poll.';
                } else {
                    // Validate that expiration time is in the future
                    const expirationDateTime = new Date(`${expirationDate.value}T${expirationTime.value}`);
                    
                    // If scheduled, make sure expiration is after scheduled time
                    const postScheduled = document.getElementById('post_scheduled');
                    if (postScheduled && postScheduled.checked) {
                        const scheduleDate = document.getElementById('schedule_date');
                        const scheduleTime = document.getElementById('schedule_time');
                        
                        if (scheduleDate && scheduleDate.value && scheduleTime && scheduleTime.value) {
                            const scheduledDateTime = new Date(`${scheduleDate.value}T${scheduleTime.value}`);
                            
                            if (expirationDateTime <= scheduledDateTime) {
                                isValid = false;
                                errorMessage = 'Expiration time must be after the scheduled time.';
                            }
                        }
                    } else if (expirationDateTime <= new Date()) {
                        isValid = false;
                        errorMessage = 'Expiration time must be in the future.';
                    }
                }
            }
            
            if (!isValid) {
                event.preventDefault();
                alert(errorMessage);
            }
        });
    }
});
