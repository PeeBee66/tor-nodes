let nodesTable;
let stats = {};

// Initialize on page load
$(document).ready(function() {
    loadStats();
    
    // Load nodes when the nodes tab is shown
    $('#nodes-tab').on('shown.bs.tab', function (e) {
        if (!nodesTable) {
            loadNodes();
        } else {
            // Redraw table to fix any display issues
            nodesTable.columns.adjust().draw();
        }
    });
    
    // Load nodes immediately if the nodes tab is already active
    if ($('#nodes-tab').hasClass('active')) {
        loadNodes();
    }
    
    setInterval(loadStats, 30000); // Refresh every 30 seconds
    
    // Setup force scrape button
    $('#forceScrapeBtn').click(function() {
        forceScrape();
    });
    
    // Setup force upload button
    $('#forceUploadBtn').click(function() {
        forceGitHubUpload();
    });
    
    // Setup force OpenCTI import button
    $('#forceOpenCTIBtn').click(function() {
        forceOpenCTIImport();
    });
    
    // Setup email settings buttons
    $('#saveEmailSettings').click(function() {
        saveEmailSettings();
    });
    
    $('#testEmail').click(function() {
        sendTestEmail();
    });
    
    $('#testSummaryEmail').click(function() {
        sendTestSummaryEmail();
    });
});

function loadStats() {
    $.get('/api/stats', function(data) {
        stats = data;
        updateDashboard();
        updateHistories();
    });
}

function loadNodes() {
    console.log('Starting to load nodes...');
    
    $.get('/api/nodes', function(data) {
        console.log('Loaded', data.total, 'nodes from API');
        
        // Ensure the table element exists
        if ($('#nodesTable').length === 0) {
            console.error('Table element not found!');
            return;
        }
        
        // Destroy existing table if it exists
        if ($.fn.DataTable.isDataTable('#nodesTable')) {
            $('#nodesTable').DataTable().destroy();
            $('#nodesTable tbody').empty();
        }
        
        // Small delay to ensure DOM is ready
        setTimeout(function() {
            try {
                nodesTable = $('#nodesTable').DataTable({
                    data: data.nodes,
                    columns: [
                        { data: 'IP', defaultContent: '' },
                        { 
                            data: 'IsExit',
                            defaultContent: '',
                            render: function(data) {
                                if (data === 'ExitNode') {
                                    return '<span class="badge bg-danger">Exit</span>';
                                }
                                return '<span class="badge bg-secondary">Relay</span>';
                            }
                        },
                        { data: 'Name', defaultContent: '' },
                        { data: 'Flags', defaultContent: '' },
                        { data: 'Uptime', defaultContent: '' },
                        { data: 'Version', defaultContent: '' },
                        { data: 'CollectionDate', defaultContent: '' }
                    ],
                    pageLength: 50,
                    order: [[0, 'asc']],
                    responsive: true,
                    autoWidth: false
                });
                console.log('DataTable initialized successfully');
            } catch (e) {
                console.error('DataTable initialization error:', e);
            }
        }, 100);
    }).fail(function(xhr) {
        console.error('Failed to load nodes:', xhr);
        $('#nodes .card-body').html('<div class="alert alert-danger">Failed to load node data. Please refresh the page.</div>');
    });
}

function updateDashboard() {
    $('#totalNodes').text(stats.node_stats.total_nodes || 0);
    $('#exitNodes').text(stats.node_stats.exit_nodes || 0);
    $('#newNodes').text(stats.node_stats.added_nodes || 0);
    $('#removedNodes').text(stats.node_stats.removed_nodes || 0);
    
    // Update last update time
    if (stats.scrape_history && stats.scrape_history.length > 0) {
        const lastUpdate = new Date(stats.scrape_history[0].timestamp);
        $('#lastUpdate').text('Last update: ' + lastUpdate.toLocaleString());
    }
    
    // Update configuration status for all services
    if (stats.config) {
        // Scraping configuration
        const scrapeStatus = $('#scrapeStatus');
        const scrapeFrequency = $('#scrapeFrequency');
        
        if (stats.config.scrape_enabled) {
            scrapeStatus.removeClass('bg-danger').addClass('bg-success').text('Enabled');
        } else {
            scrapeStatus.removeClass('bg-success').addClass('bg-danger').text('Disabled');
        }
        
        scrapeFrequency.text(stats.config.scrape_frequency_hours || 1);
        
        // GitHub upload configuration
        const githubStatus = $('#githubStatus');
        const githubFrequency = $('#githubFrequency');
        
        if (stats.config.github_upload_enabled) {
            githubStatus.removeClass('bg-danger').addClass('bg-success').text('Enabled');
        } else {
            githubStatus.removeClass('bg-success').addClass('bg-danger').text('Disabled');
        }
        
        githubFrequency.text(stats.config.github_upload_frequency_hours || 1);
        
        // OpenCTI import configuration
        const openctiStatus = $('#openctiStatus');
        const openctiFrequency = $('#openctiFrequency');
        
        if (stats.config.opencti_upload_enabled) {
            openctiStatus.removeClass('bg-danger').addClass('bg-success').text('Enabled');
        } else {
            openctiStatus.removeClass('bg-success').addClass('bg-danger').text('Disabled');
        }
        
        openctiFrequency.text(stats.config.opencti_upload_frequency_hours || 24);
        
        // Email configuration
        const emailStatus = $('#emailStatus');
        
        if (stats.config.email_enabled) {
            emailStatus.removeClass('bg-danger').addClass('bg-success').text('Enabled');
        } else {
            emailStatus.removeClass('bg-success').addClass('bg-danger').text('Disabled');
        }
        
        // Update email toggle to match current configuration
        $('#emailEnabledToggle').prop('checked', stats.config.email_enabled);
        
        // Load saved email settings
        if (stats.config.email_settings) {
            const settings = stats.config.email_settings;
            $('#includeNodeStats').prop('checked', settings.includeNodeStats);
            $('#includeScrapeHistory').prop('checked', settings.includeScrapeHistory);
            $('#includeGithubHistory').prop('checked', settings.includeGithubHistory);
            $('#includeOpenctiHistory').prop('checked', settings.includeOpenctiHistory);
            $('#includeErrors').prop('checked', settings.includeErrors);
            $('#includeSystemHealth').prop('checked', settings.includeSystemHealth);
        }
        
        // Update email configuration display
        if (stats.config.email_config) {
            const emailConfig = stats.config.email_config;
            $('#configEmailEnabled').text(stats.config.email_enabled ? 'true' : 'false');
            $('#configSmtpServer').text(emailConfig.smtp_server || '(not configured)');
            $('#configSmtpPort').text(emailConfig.smtp_port || '(not configured)');
            $('#configUsername').text(emailConfig.username || '(not configured)');
            $('#configPassword').text(emailConfig.username ? '(configured)' : '(not configured)');
            $('#configEmailFrom').text(emailConfig.from_email || '(not configured)');
            $('#configEmailTo').text(emailConfig.to_email || '(not configured)');
        }
    }
}

function updateHistories() {
    // Update scrape history
    updateHistorySection('scrapeHistory', stats.scrape_history, formatScrapeItem);
    
    // Update GitHub history
    updateHistorySection('githubHistory', stats.github_history, formatSimpleItem);
    
    // Update OpenCTI history
    updateHistorySection('openctiHistory', stats.opencti_history, formatOpenCTIItem);
}

function updateHistorySection(elementId, history, formatter) {
    const container = $(`#${elementId}`);
    container.empty();
    
    if (!history || history.length === 0) {
        container.html('<p class="text-muted">No history available</p>');
        return;
    }
    
    history.slice(0, 20).forEach(item => {
        container.append(formatter(item));
    });
}

function forceScrape() {
    const btn = $('#forceScrapeBtn');
    const originalText = btn.html();
    
    // Disable button and show loading
    btn.prop('disabled', true);
    btn.html('<i class="fas fa-spinner fa-spin"></i> Scraping...');
    
    $.ajax({
        url: '/api/force-scrape',
        method: 'POST',
        success: function(response) {
            if (response.success) {
                showAlert('Force scrape completed successfully!', 'success');
                loadStats(); // Refresh stats
                loadNodes(); // Refresh node table
            } else {
                // Check if it's a rate limit error
                if (response.message && response.message.includes('RATE_LIMITED')) {
                    showAlert('Rate Limited: ' + response.message.replace('RATE_LIMITED: ', ''), 'warning');
                } else {
                    showAlert('Force scrape failed: ' + response.message, 'danger');
                }
            }
        },
        error: function(xhr) {
            const response = JSON.parse(xhr.responseText || '{}');
            showAlert('Force scrape error: ' + (response.message || 'Unknown error'), 'danger');
        },
        complete: function() {
            // Re-enable button
            btn.prop('disabled', false);
            btn.html(originalText);
        }
    });
}

function showAlert(message, type, targetTab = 'scrape') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Add alert at the top of the specified tab's card
    $(`#${targetTab} .card-body`).prepend(alertHtml);
    
    // Auto-remove after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut();
    }, 5000);
}

function forceGitHubUpload() {
    const btn = $('#forceUploadBtn');
    const originalText = btn.html();
    
    // Disable button and show loading
    btn.prop('disabled', true);
    btn.html('<i class="fas fa-spinner fa-spin"></i> Uploading...');
    
    $.ajax({
        url: '/api/force-upload-github',
        method: 'POST',
        success: function(response) {
            if (response.success) {
                showAlert('GitHub upload completed successfully! ' + response.message, 'success', 'github');
                loadStats(); // Refresh stats to show new upload in history
            } else {
                showAlert('GitHub upload failed: ' + response.message, 'danger', 'github');
            }
        },
        error: function(xhr) {
            const response = JSON.parse(xhr.responseText || '{}');
            showAlert('GitHub upload error: ' + (response.message || 'Unknown error'), 'danger', 'github');
        },
        complete: function() {
            // Re-enable button
            btn.prop('disabled', false);
            btn.html(originalText);
        }
    });
}

function formatScrapeItem(item) {
    const timestamp = new Date(item.timestamp).toLocaleString();
    const isForced = item.forced || item.message?.includes('[FORCED]');
    const statusDisplay = item.status.toUpperCase() + (isForced ? ' (FORCED)' : '');
    
    let html = `<div class="history-item ${item.status}">
        <div class="timestamp">${timestamp} - ${statusDisplay}</div>`;
    
    if (item.message) {
        // Clean up the message for display
        let message = item.message;
        if (message.includes('RATE_LIMITED:')) {
            message = message.replace('RATE_LIMITED: ', '⚠️ RATE LIMITED: ');
        }
        html += `<div class="message">${message}</div>`;
    }
    
    if (item.status === 'success') {
        html += `<div class="stats">
            Total: ${item.nodes_total || 0} | 
            Exit: ${item.nodes_exit || 0} | 
            Added: ${item.nodes_added || 0} | 
            Removed: ${item.nodes_removed || 0}
        </div>`;
    }
    
    html += '</div>';
    return html;
}

function formatSimpleItem(item) {
    const timestamp = new Date(item.timestamp).toLocaleString();
    const isForced = item.forced || item.message?.includes('[FORCED]');
    const statusDisplay = item.status.toUpperCase() + (isForced ? ' (FORCED)' : '');
    
    return `<div class="history-item ${item.status}">
        <div class="timestamp">${timestamp} - ${statusDisplay}</div>
        <div class="message">${item.message || ''}</div>
    </div>`;
}

function formatOpenCTIItem(item) {
    const timestamp = new Date(item.timestamp).toLocaleString();
    const isForced = item.forced || item.message?.includes('[FORCED]');
    const statusDisplay = item.status.toUpperCase() + (isForced ? ' (FORCED)' : '');
    
    let html = `<div class="history-item ${item.status}">
        <div class="timestamp">${timestamp} - ${statusDisplay}</div>`;
    
    if (item.message) {
        html += `<div class="message">${item.message}</div>`;
    }
    
    if (item.imported !== undefined) {
        html += `<div class="stats">Imported: ${item.imported} nodes</div>`;
    }
    
    html += '</div>';
    return html;
}

function forceOpenCTIImport() {
    const btn = $('#forceOpenCTIBtn');
    const originalText = btn.html();
    
    // Disable button and show loading
    btn.prop('disabled', true);
    btn.html('<i class="fas fa-spinner fa-spin"></i> Starting Import...');
    
    $.ajax({
        url: '/api/force-upload-opencti',
        method: 'POST',
        timeout: 10000, // 10 second timeout for starting the import
        success: function(response) {
            if (response.success) {
                if (response.estimated_time_minutes) {
                    showAlert(`${response.message} Estimated completion: ${response.estimated_time_minutes} minutes.`, 'info', 'opencti');
                } else {
                    showAlert(response.message, 'success', 'opencti');
                }
                loadStats(); // Refresh stats to show import status
                
                // Set up periodic refresh to show progress
                let refreshCount = 0;
                const maxRefreshes = 30; // Stop after 15 minutes
                const refreshInterval = setInterval(function() {
                    loadStats();
                    refreshCount++;
                    if (refreshCount >= maxRefreshes) {
                        clearInterval(refreshInterval);
                    }
                }, 30000); // Refresh every 30 seconds
                
            } else {
                showAlert('OpenCTI import failed: ' + response.message, 'danger', 'opencti');
            }
        },
        error: function(xhr) {
            const response = JSON.parse(xhr.responseText || '{}');
            if (xhr.status === 0) {
                showAlert('OpenCTI import request failed: Connection timeout. The import may still be running in the background.', 'warning', 'opencti');
            } else {
                showAlert('OpenCTI import error: ' + (response.message || 'Unknown error'), 'danger', 'opencti');
            }
        },
        complete: function() {
            // Re-enable button after a delay
            setTimeout(function() {
                btn.prop('disabled', false);
                btn.html(originalText);
            }, 2000);
        }
    });
}

function saveEmailSettings() {
    const emailSettings = {
        enabled: $('#emailEnabledToggle').is(':checked'),
        includeNodeStats: $('#includeNodeStats').is(':checked'),
        includeScrapeHistory: $('#includeScrapeHistory').is(':checked'),
        includeGithubHistory: $('#includeGithubHistory').is(':checked'),
        includeOpenctiHistory: $('#includeOpenctiHistory').is(':checked'),
        includeErrors: $('#includeErrors').is(':checked'),
        includeSystemHealth: $('#includeSystemHealth').is(':checked')
    };
    
    const btn = $('#saveEmailSettings');
    const originalText = btn.html();
    
    // Disable button and show saving
    btn.prop('disabled', true);
    btn.html('<i class="fas fa-spinner fa-spin"></i> Saving...');
    
    $.ajax({
        url: '/api/email-settings',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(emailSettings),
        success: function(response) {
            if (response.success) {
                showAlert('Email settings saved successfully!', 'success', 'email');
                loadStats(); // Refresh to show updated configuration
            } else {
                showAlert('Failed to save email settings: ' + response.message, 'danger', 'email');
            }
        },
        error: function(xhr) {
            const response = JSON.parse(xhr.responseText || '{}');
            showAlert('Error saving email settings: ' + (response.message || 'Unknown error'), 'danger', 'email');
        },
        complete: function() {
            // Re-enable button
            btn.prop('disabled', false);
            btn.html(originalText);
        }
    });
}

function sendTestEmail() {
    const btn = $('#testEmail');
    const originalText = btn.html();
    
    // Disable button and show sending
    btn.prop('disabled', true);
    btn.html('<i class="fas fa-spinner fa-spin"></i> Sending...');
    
    $.ajax({
        url: '/api/test-email',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ type: 'simple' }),
        success: function(response) {
            if (response.success) {
                showAlert('Test email sent successfully!', 'success', 'email');
            } else {
                showAlert('Failed to send test email: ' + response.message, 'danger', 'email');
            }
        },
        error: function(xhr) {
            const response = JSON.parse(xhr.responseText || '{}');
            showAlert('Error sending test email: ' + (response.message || 'Unknown error'), 'danger', 'email');
        },
        complete: function() {
            // Re-enable button
            btn.prop('disabled', false);
            btn.html(originalText);
        }
    });
}

function sendTestSummaryEmail() {
    const btn = $("#testSummaryEmail");
    const originalText = btn.html();
    
    // Disable button and show sending
    btn.prop("disabled", true);
    btn.html("<i class=\"fas fa-spinner fa-spin\"></i> Sending...");
    
    $.ajax({
        url: "/api/test-email",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({ type: "summary" }),
        success: function(response) {
            if (response.success) {
                showAlert("Test summary email sent\! Check your inbox to see how your weekly report will look.", "success", "email");
            } else {
                showAlert("Failed to send test summary: " + response.message, "danger", "email");
            }
        },
        error: function(xhr) {
            const response = JSON.parse(xhr.responseText || "{}");
            showAlert("Error sending test summary: " + (response.message || "Unknown error"), "danger", "email");
        },
        complete: function() {
            // Re-enable button
            btn.prop("disabled", false);
            btn.html(originalText);
        }
    });
}
