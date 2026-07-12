let currentStep = 1;
let onboardingSessionId = null;
let clientData = {};

function getHeaders() {
    const token = sessionStorage.getItem('token');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

function goToStep(stepNumber) {
    // Hide all steps
    document.querySelectorAll('.wizard-step').forEach(step => {
        step.classList.remove('active');
    });

    // Show the target step
    const targetStep = document.getElementById(`step-${stepNumber}`);
    if (targetStep) {
        targetStep.classList.add('active');
    }

    // Update indicators
    document.querySelectorAll('.step-indicator').forEach(indicator => {
        indicator.classList.remove('active', 'completed');
    });

    for (let i = 1; i <= 4; i++) {
        const indicator = document.getElementById(`step-${i}-indicator`);
        if (i < stepNumber) {
            indicator.classList.add('completed');
        } else if (i === stepNumber) {
            indicator.classList.add('active');
        }
    }

    currentStep = stepNumber;
}

async function saveStepData(step, data) {
    if (!onboardingSessionId) return;
    try {
        await fetch('/api/onboarding/save', {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({
                session_id: onboardingSessionId,
                step: step,
                data: data
            })
        });
    } catch (error) {
        console.error('Failed to save step data:', error);
    }
}

async function handleClientProfileSubmit(event) {
    event.preventDefault();
    const clientName = document.getElementById('clientName').value;
    const websiteUrl = document.getElementById('websiteUrl').value;
    const industry = document.getElementById('industry').value;
    const defaultBudget = document.getElementById('defaultBudget').value;

    clientData = {
        name: clientName,
        website: websiteUrl,
        industry: industry,
        default_budget: defaultBudget
    };

    await saveStepData(1, clientData);
    goToStep(2);
}

function connectGoogle() {
    // Placeholder for OAuth flow
    alert('Connecting to Google... (OAuth flow to be implemented)');
    // On success:
    document.getElementById('google-status').textContent = 'Connected';
    document.getElementById('google-connect-btn').textContent = 'Connected';
    document.getElementById('google-connect-btn').disabled = true;
    clientData.google_connected = true;
    saveStepData(2, { google_connected: true });
}

function connectMeta() {
    // Placeholder for OAuth flow
    alert('Connecting to Meta... (OAuth flow to be implemented)');
    // On success:
    document.getElementById('meta-status').textContent = 'Connected';
    document.getElementById('meta-connect-btn').textContent = 'Connected';
    document.getElementById('meta-connect-btn').disabled = true;
    clientData.meta_connected = true;
    saveStepData(2, { meta_connected: true });
}

async function handleCampaignLaunchSubmit(event) {
    event.preventDefault();
    const objective = document.getElementById('objective').value;
    const language = document.getElementById('language').value;
    const productKeywords = document.getElementById('productKeywords').value;
    const targetGeo = document.getElementById('targetGeo').value;
    const toneOfVoice = document.getElementById('toneOfVoice').value;

    const campaignDetails = {
        campaign_objective: objective,
        campaign_language: language,
        product_keywords: productKeywords,
        target_geo: targetGeo,
        tone_of_voice: toneOfVoice,
        launch_campaign: true
    };

    // Merge all data for final submission
    const finalPayload = { ...clientData, ...campaignDetails, session_id: onboardingSessionId };

    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Launching...';

    try {
        const res = await fetch('/api/onboarding/submit', {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(finalPayload)
        });

        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || 'Failed to launch campaign');
        }

        const result = await res.json();
        console.log('Campaign launched:', result);
        goToStep(4);

    } catch (error) {
        alert(`Error: ${error.message}`);
        submitButton.disabled = false;
        submitButton.innerHTML = '<i class="fa-solid fa-rocket mr-2"></i> Launch Orchestration';
    }
}

async function initializeWizard() {
    try {
        const res = await fetch('/api/onboarding/resume', { headers: getHeaders() });
        let session;
        if (res.ok) {
            session = await res.json();
        }

        if (session && session.session_id) {
            onboardingSessionId = session.session_id;
            clientData = session.data || {};
            // Restore form fields from clientData if needed
            // goToStep(session.step || 1);
        } else {
            const startRes = await fetch('/api/onboarding/start', { method: 'POST', headers: getHeaders() });
            const startData = await startRes.json();
            onboardingSessionId = startData.session_id;
        }
    } catch (error) {
        console.error('Failed to initialize onboarding wizard:', error);
        alert('Could not start or resume onboarding session. Please try again.');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initializeWizard();
    document.getElementById('clientProfileForm').addEventListener('submit', handleClientProfileSubmit);
    document.getElementById('campaignLaunchForm').addEventListener('submit', handleCampaignLaunchSubmit);
});