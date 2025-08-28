/**
 * Voice-to-Text Legal Jargon Explainer
 * Handles speech recognition and legal term explanation
 */

class VoiceLegalExplainer {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.isSupported = false;
        this.currentAudio = null;
        
        this.initializeSpeechRecognition();
        this.setupUI();
    }
    
    initializeSpeechRecognition() {
        // Check browser support for Speech Recognition
        if ('webkitSpeechRecognition' in window) {
            this.recognition = new webkitSpeechRecognition();
            this.isSupported = true;
        } else if ('SpeechRecognition' in window) {
            this.recognition = new SpeechRecognition();
            this.isSupported = true;
        } else {
            console.warn('Speech Recognition not supported in this browser');
            this.isSupported = false;
            return;
        }
        
        // Configure speech recognition
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';
        this.recognition.maxAlternatives = 1;
        
        // Event handlers
        this.recognition.onstart = () => {
            this.isListening = true;
            this.updateUI();
            console.log('Voice recognition started');
        };
        
        this.recognition.onresult = (event) => {
            const result = event.results[event.results.length - 1];
            const transcript = result[0].transcript;
            
            if (result.isFinal) {
                this.handleFinalResult(transcript);
            } else {
                this.handleInterimResult(transcript);
            }
        };
        
        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.handleError(event.error);
        };
        
        this.recognition.onend = () => {
            this.isListening = false;
            this.updateUI();
            console.log('Voice recognition ended');
        };
    }
    
    setupUI() {
        // Create voice interface if it doesn't exist
        if (!document.getElementById('voice-legal-interface')) {
            this.createVoiceInterface();
        }
        
        // Setup event listeners
        this.setupEventListeners();
    }
    
    createVoiceInterface() {
        const voiceHTML = `
            <div id="voice-legal-interface" class="voice-interface mb-4">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">
                            <i class="fas fa-microphone me-2"></i>
                            Voice Legal Assistant
                        </h5>
                        <small class="text-muted">Ask about legal terms</small>
                    </div>
                    <div class="card-body">
                        <div class="voice-controls text-center mb-3">
                            <button id="startVoiceBtn" class="btn btn-primary btn-lg me-2" ${!this.isSupported ? 'disabled' : ''}>
                                <i class="fas fa-microphone"></i>
                                Start Listening
                            </button>
                            <button id="stopVoiceBtn" class="btn btn-danger btn-lg" disabled>
                                <i class="fas fa-stop"></i>
                                Stop
                            </button>
                        </div>
                        
                        <div id="voiceStatus" class="voice-status text-center mb-3">
                            ${this.isSupported ? 
                                '<span class="text-muted">Click "Start Listening" to ask about legal terms</span>' : 
                                '<span class="text-warning"><i class="fas fa-exclamation-triangle"></i> Voice recognition not supported in this browser</span>'
                            }
                        </div>
                        
                        <div id="voiceTranscript" class="voice-transcript p-3 bg-light rounded" style="min-height: 60px; display: none;">
                            <strong>You said:</strong> <span id="transcriptText"></span>
                        </div>
                        
                        <div id="voiceExplanation" class="voice-explanation mt-3" style="display: none;">
                            <div class="alert alert-info">
                                <h6><i class="fas fa-lightbulb me-2"></i>Legal Explanation:</h6>
                                <div id="explanationText"></div>
                                <div class="mt-2">
                                    <button id="speakExplanationBtn" class="btn btn-sm btn-outline-primary me-2">
                                        <i class="fas fa-volume-up"></i> Listen to Explanation
                                    </button>
                                    <button id="askAnotherBtn" class="btn btn-sm btn-outline-secondary">
                                        <i class="fas fa-microphone"></i> Ask Another Term
                                    </button>
                                </div>
                            </div>
                        </div>
                        
                        <div class="voice-examples mt-3">
                            <small class="text-muted">
                                <strong>Try saying:</strong> "What does force majeure mean?" • "Explain liquidated damages" • "What is indemnification?"
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Insert at the top of the chat container or main content
        const chatContainer = document.getElementById('chatContainer') || document.querySelector('.container');
        if (chatContainer) {
            chatContainer.insertAdjacentHTML('afterbegin', voiceHTML);
        }
    }
    
    setupEventListeners() {
        const startBtn = document.getElementById('startVoiceBtn');
        const stopBtn = document.getElementById('stopVoiceBtn');
        const speakBtn = document.getElementById('speakExplanationBtn');
        const askAnotherBtn = document.getElementById('askAnotherBtn');
        
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startListening());
        }
        
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopListening());
        }
        
        if (speakBtn) {
            speakBtn.addEventListener('click', () => this.speakExplanation());
        }
        
        if (askAnotherBtn) {
            askAnotherBtn.addEventListener('click', () => this.resetForNewQuery());
        }
    }
    
    startListening() {
        if (!this.isSupported) {
            this.showError('Speech recognition is not supported in your browser');
            return;
        }
        
        if (this.isListening) {
            return;
        }
        
        try {
            this.recognition.start();
            this.updateStatus('Listening... Speak now!', 'listening');
        } catch (error) {
            console.error('Error starting recognition:', error);
            this.handleError(error.message);
        }
    }
    
    stopListening() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
        }
    }
    
    handleInterimResult(transcript) {
        this.showTranscript(transcript, false);
        this.updateStatus('Listening... Keep speaking', 'listening');
    }
    
    handleFinalResult(transcript) {
        console.log('Final transcript:', transcript);
        this.showTranscript(transcript, true);
        this.updateStatus('Processing your question...', 'processing');
        
        // Send to backend for legal explanation
        this.explainLegalTerm(transcript);
    }
    
    async explainLegalTerm(text) {
        try {
            const response = await fetch('/api/voice-legal-explain', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    voice_optimized: true
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.displayExplanation(data);
            
        } catch (error) {
            console.error('Error explaining legal term:', error);
            this.showError('Sorry, I had trouble processing that. Please try again.');
        }
    }
    
    displayExplanation(data) {
        const explanationDiv = document.getElementById('voiceExplanation');
        const explanationText = document.getElementById('explanationText');
        
        if (data.type === 'legal_explanation') {
            explanationText.innerHTML = data.voice_explanation || data.explanation;
            explanationDiv.style.display = 'block';
            this.updateStatus('Explanation ready!', 'ready');
            
            // Store for text-to-speech
            this.currentExplanation = data.voice_explanation || data.explanation;
            
        } else if (data.type === 'redirect') {
            explanationText.innerHTML = data.explanation;
            if (data.suggestions) {
                explanationText.innerHTML += '<br><br><strong>Try asking:</strong><ul>';
                data.suggestions.forEach(suggestion => {
                    explanationText.innerHTML += `<li>${suggestion}</li>`;
                });
                explanationText.innerHTML += '</ul>';
            }
            explanationDiv.style.display = 'block';
            this.updateStatus('Ready for legal questions', 'ready');
        } else {
            this.showError(data.explanation || 'Sorry, something went wrong.');
        }
    }
    
    speakExplanation() {
        if (!this.currentExplanation) {
            return;
        }
        
        // Stop any current speech
        if (this.currentAudio) {
            speechSynthesis.cancel();
        }
        
        // Use browser's text-to-speech
        const utterance = new SpeechSynthesisUtterance(this.currentExplanation);
        utterance.rate = 0.9;
        utterance.pitch = 1;
        utterance.volume = 0.8;
        
        utterance.onstart = () => {
            const speakBtn = document.getElementById('speakExplanationBtn');
            if (speakBtn) {
                speakBtn.innerHTML = '<i class="fas fa-pause"></i> Speaking...';
                speakBtn.disabled = true;
            }
        };
        
        utterance.onend = () => {
            const speakBtn = document.getElementById('speakExplanationBtn');
            if (speakBtn) {
                speakBtn.innerHTML = '<i class="fas fa-volume-up"></i> Listen to Explanation';
                speakBtn.disabled = false;
            }
        };
        
        speechSynthesis.speak(utterance);
    }
    
    resetForNewQuery() {
        // Hide explanation and transcript
        const explanationDiv = document.getElementById('voiceExplanation');
        const transcriptDiv = document.getElementById('voiceTranscript');
        
        if (explanationDiv) explanationDiv.style.display = 'none';
        if (transcriptDiv) transcriptDiv.style.display = 'none';
        
        this.currentExplanation = null;
        this.updateStatus('Ready to listen for legal questions', 'ready');
    }
    
    showTranscript(text, isFinal) {
        const transcriptDiv = document.getElementById('voiceTranscript');
        const transcriptText = document.getElementById('transcriptText');
        
        if (transcriptText) {
            transcriptText.textContent = text;
            transcriptDiv.style.display = 'block';
            
            if (isFinal) {
                transcriptDiv.classList.add('final-transcript');
            }
        }
    }
    
    updateStatus(message, type = 'default') {
        const statusElement = document.getElementById('voiceStatus');
        if (!statusElement) return;
        
        let iconClass = 'fas fa-info-circle';
        let textClass = 'text-muted';
        
        switch (type) {
            case 'listening':
                iconClass = 'fas fa-microphone text-danger';
                textClass = 'text-danger';
                break;
            case 'processing':
                iconClass = 'fas fa-spinner fa-spin';
                textClass = 'text-primary';
                break;
            case 'ready':
                iconClass = 'fas fa-check-circle';
                textClass = 'text-success';
                break;
            case 'error':
                iconClass = 'fas fa-exclamation-triangle';
                textClass = 'text-warning';
                break;
        }
        
        statusElement.innerHTML = `<span class="${textClass}"><i class="${iconClass} me-1"></i>${message}</span>`;
    }
    
    updateUI() {
        const startBtn = document.getElementById('startVoiceBtn');
        const stopBtn = document.getElementById('stopVoiceBtn');
        
        if (startBtn && stopBtn) {
            startBtn.disabled = this.isListening || !this.isSupported;
            stopBtn.disabled = !this.isListening;
        }
    }
    
    handleError(error) {
        console.error('Voice recognition error:', error);
        this.updateStatus(`Error: ${error}`, 'error');
        this.isListening = false;
        this.updateUI();
    }
    
    showError(message) {
        this.updateStatus(message, 'error');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on the main page (not in an iframe, etc.)
    if (window.self === window.top) {
        window.voiceLegalExplainer = new VoiceLegalExplainer();
        console.log('Voice Legal Explainer initialized');
    }
});