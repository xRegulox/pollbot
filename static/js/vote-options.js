/**
 * Regulo PollBot - Vote Options JavaScript
 * Handles vote limit and vote changing functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    setupVoteOptions();
    
    /**
     * Sets up the vote options functionality (max votes, vote changing)
     */
    function setupVoteOptions() {
        const allowMultipleCheckbox = document.getElementById('allow_multiple');
        const maxVotesContainer = document.getElementById('max_votes_container');
        
        if (!allowMultipleCheckbox || !maxVotesContainer) return;
        
        // Show/hide max votes container based on allow multiple checkbox
        allowMultipleCheckbox.addEventListener('change', function() {
            maxVotesContainer.style.display = this.checked ? 'block' : 'none';
            
            // Reset max votes to 0 when disabling multiple votes
            if (!this.checked) {
                document.getElementById('max_votes').value = 0;
            }
        });
        
        // Initialize based on current state
        maxVotesContainer.style.display = allowMultipleCheckbox.checked ? 'block' : 'none';
        
        // Update poll preview when vote options change
        const voteOptionControls = [
            allowMultipleCheckbox,
            document.getElementById('max_votes'),
            document.getElementById('allow_vote_change'),
            document.getElementById('is_anonymous'),
            document.getElementById('show_live_results')
        ];
        
        voteOptionControls.forEach(control => {
            if (control) {
                control.addEventListener('change', function() {
                    if (typeof updatePollPreview === 'function') {
                        updatePollPreview();
                    }
                });
            }
        });
    }
});