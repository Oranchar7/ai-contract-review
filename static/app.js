// Global variables
let currentAnalysis = null;

// DOM elements
const uploadForm = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const emailInput = document.getElementById('emailInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const loadingIndicator = document.getElementById('loadingIndicator');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');
const resultsContainer = document.getElementById('resultsContainer');

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
});

function initializeEventListeners() {
    // Form submission
    uploadForm.addEventListener('submit', handleFormSubmit);
    
    // File input validation
    fileInput.addEventListener('change', validateFileInput);
    
    // Results actions
    document.getElementById('downloadReport')?.addEventListener('click', downloadReport);
    document.getElementById('shareReport')?.addEventListener('click', shareReport);
    document.getElementById('analyzeAnother')?.addEventListener('click', analyzeAnother);
}

async function handleFormSubmit(event) {
    event.preventDefault();
    
    const file = fileInput.files[0];
    const email = emailInput.value.trim();
    
    if (!file) {
        showError('Please select a file to analyze.');
        return;
    }
    
    if (!validateFile(file)) {
        return;
    }
    
    await analyzeContract(file, email);
}

function validateFileInput() {
    const file = fileInput.files[0];
    if (file) {
        validateFile(file);
    }
}

function validateFile(file) {
    // Check file type
    const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    const allowedExtensions = ['.pdf', '.docx'];
    
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    
    if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
        showError('Invalid file type. Please upload a PDF or DOCX file.');
        return false;
    }
    
    // Check file size (10MB limit)
    if (file.size > 10 * 1024 * 1024) {
        showError('File size too large. Maximum size is 10MB.');
        return false;
    }
    
    hideError();
    return true;
}

async function analyzeContract(file, email) {
    try {
        showLoading();
        hideError();
        hideResults();
        
        const formData = new FormData();
        formData.append('file', file);
        if (email) {
            formData.append('email', email);
        }
        
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Analysis failed');
        }
        
        const analysisResult = await response.json();
        currentAnalysis = analysisResult;
        
        displayResults(analysisResult);
        
    } catch (error) {
        console.error('Analysis error:', error);
        showError(error.message || 'An error occurred during analysis. Please try again.');
    } finally {
        hideLoading();
    }
}

function displayResults(analysis) {
    // Update risk score
    const riskScore = document.getElementById('riskScore');
    const riskLevel = document.getElementById('riskLevel');
    
    riskScore.textContent = analysis.risk_score;
    
    // Set risk level styling
    let levelClass = 'low';
    let levelText = 'Low Risk';
    
    if (analysis.risk_score >= 7) {
        levelClass = 'high';
        levelText = 'High Risk';
    } else if (analysis.risk_score >= 4) {
        levelClass = 'medium';
        levelText = 'Medium Risk';
    }
    
    riskLevel.className = `risk-level ${levelClass}`;
    riskLevel.textContent = levelText;
    
    // Update quick summary
    document.getElementById('quickSummary').textContent = analysis.summary;
    
    // Display risky clauses
    displayRiskyClauses(analysis.risky_clauses);
    
    // Display missing protections
    displayMissingProtections(analysis.missing_protections);
    
    // Display detailed summary
    document.getElementById('detailedSummary').innerHTML = formatDetailedSummary(analysis.detailed_analysis);
    
    // Show results
    showResults();
}

function displayRiskyClauses(clauses) {
    const container = document.getElementById('riskyClauses');
    
    if (!clauses || clauses.length === 0) {
        container.innerHTML = '<p class="text-muted">No high-risk clauses identified.</p>';
        return;
    }
    
    container.innerHTML = clauses.map(clause => `
        <div class="clause-item">
            <div class="clause-title">${escapeHtml(clause.clause_type || 'Risky Clause')}</div>
            <div class="clause-description">${escapeHtml(clause.description || '')}</div>
            <div class="clause-recommendation">
                <strong>Recommendation:</strong> ${escapeHtml(clause.recommendation || '')}
            </div>
        </div>
    `).join('');
}

function displayMissingProtections(protections) {
    const container = document.getElementById('missingProtections');
    
    if (!protections || protections.length === 0) {
        container.innerHTML = '<p class="text-muted">All standard protections appear to be in place.</p>';
        return;
    }
    
    container.innerHTML = protections.map(protection => `
        <div class="missing-protection">
            <div class="protection-title">${escapeHtml(protection.protection_type || 'Missing Protection')}</div>
            <div class="protection-description">${escapeHtml(protection.description || '')}</div>
            <div class="protection-importance">
                <strong>Why it matters:</strong> ${escapeHtml(protection.importance || '')}
            </div>
        </div>
    `).join('');
}

function formatDetailedSummary(detailedAnalysis) {
    if (typeof detailedAnalysis === 'string') {
        return escapeHtml(detailedAnalysis).replace(/\n/g, '<br>');
    }
    
    if (typeof detailedAnalysis === 'object') {
        return Object.entries(detailedAnalysis)
            .map(([key, value]) => `<strong>${escapeHtml(key)}:</strong> ${escapeHtml(value)}`)
            .join('<br><br>');
    }
    
    return 'Detailed analysis not available.';
}

function downloadReport() {
    if (!currentAnalysis) return;
    
    const reportData = {
        analysisDate: new Date().toISOString(),
        riskScore: currentAnalysis.risk_score,
        summary: currentAnalysis.summary,
        riskyClauses: currentAnalysis.risky_clauses,
        missingProtections: currentAnalysis.missing_protections,
        detailedAnalysis: currentAnalysis.detailed_analysis
    };
    
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `contract-analysis-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function shareReport() {
    if (!currentAnalysis) return;
    
    const shareText = `Contract Analysis Results:\nRisk Score: ${currentAnalysis.risk_score}/10\nSummary: ${currentAnalysis.summary}`;
    
    if (navigator.share) {
        navigator.share({
            title: 'Contract Analysis Report',
            text: shareText,
            url: window.location.href
        });
    } else {
        // Fallback: copy to clipboard
        navigator.clipboard.writeText(shareText).then(() => {
            alert('Report details copied to clipboard!');
        });
    }
}

function analyzeAnother() {
    // Reset form
    uploadForm.reset();
    currentAnalysis = null;
    
    // Hide results and errors
    hideResults();
    hideError();
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Utility functions
function showLoading() {
    loadingIndicator.style.display = 'block';
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Analyzing...';
}

function hideLoading() {
    loadingIndicator.style.display = 'none';
    analyzeBtn.disabled = false;
    analyzeBtn.innerHTML = '<i class="fas fa-search me-2"></i>Analyze Contract';
}

function showError(message) {
    errorText.textContent = message;
    errorMessage.style.display = 'block';
    errorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function hideError() {
    errorMessage.style.display = 'none';
}

function showResults() {
    resultsContainer.style.display = 'block';
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function hideResults() {
    resultsContainer.style.display = 'none';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Firebase integration functions (for future use)
window.storeAnalysisLocally = function(analysis) {
    if (window.firebaseDb && analysis.document_id) {
        // Store analysis reference locally for offline access
        localStorage.setItem('lastAnalysis', JSON.stringify({
            id: analysis.document_id,
            timestamp: new Date().toISOString(),
            riskScore: analysis.risk_score
        }));
    }
};

// Error handling for network issues
window.addEventListener('online', function() {
    hideError();
});

window.addEventListener('offline', function() {
    showError('You are currently offline. Please check your internet connection.');
});
