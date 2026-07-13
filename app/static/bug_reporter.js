// bug_reporter.js
document.addEventListener('DOMContentLoaded', () => {
    // Inject the CSS for the bug reporter
    const style = document.createElement('style');
    style.textContent = `
        #bug-reporter-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: #ef4444;
            color: white;
            padding: 10px 15px;
            border-radius: 9999px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            cursor: pointer;
            z-index: 9999;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: background-color 0.2s;
        }
        #bug-reporter-btn:hover {
            background-color: #dc2626;
        }
        #bug-reporter-modal {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: rgba(0,0,0,0.5);
            z-index: 10000;
            justify-content: center;
            align-items: center;
        }
        #bug-reporter-content {
            background: white;
            padding: 24px;
            border-radius: 8px;
            width: 90%;
            max-width: 500px;
            box-shadow: 0 10px 15px rgba(0,0,0,0.1);
        }
        #bug-reporter-content h2 {
            margin-top: 0;
            margin-bottom: 16px;
            font-size: 1.5rem;
            color: #111827;
        }
        #bug-reporter-content textarea {
            width: 100%;
            height: 120px;
            padding: 8px;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            margin-bottom: 16px;
            font-family: inherit;
        }
        .bug-reporter-actions {
            display: flex;
            justify-content: flex-end;
            gap: 12px;
        }
        .bug-reporter-btn-cancel {
            background: white;
            border: 1px solid #d1d5db;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
        }
        .bug-reporter-btn-submit {
            background: #ef4444;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        .bug-reporter-btn-submit:hover {
            background: #dc2626;
        }
    `;
    document.head.appendChild(style);

    // Inject the Button
    const btn = document.createElement('div');
    btn.id = 'bug-reporter-btn';
    btn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m8 2 1.88 1.88"/><path d="M14.12 3.88 16 2"/><path d="M9 7.13v-1a3.003 3.003 0 1 1 6 0v1"/><path d="M12 20c-3.3 0-6-2.7-6-6v-3a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v3c0 3.3-2.7 6-6 6"/><path d="M12 20v-9"/><path d="M6.53 9C4.6 8.8 3 7.1 3 5"/><path d="M6 13H2"/><path d="M3 21c0-2.1 1.7-3.9 3.8-4"/><path d="M20.97 5c0 2.1-1.6 3.8-3.5 4"/><path d="M22 13h-4"/><path d="M17.2 17c2.1.1 3.8 1.9 3.8 4"/></svg>
        Report Bug
    `;
    document.body.appendChild(btn);

    // Inject the Modal
    const modal = document.createElement('div');
    modal.id = 'bug-reporter-modal';
    modal.innerHTML = `
        <div id="bug-reporter-content">
            <h2>Report a Bug</h2>
            <textarea id="bug-reporter-desc" placeholder="Please describe the issue you encountered..."></textarea>
            <div class="bug-reporter-actions">
                <button class="bug-reporter-btn-cancel" id="bug-cancel">Cancel</button>
                <button class="bug-reporter-btn-submit" id="bug-submit">Submit Report</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    // Event Listeners
    btn.addEventListener('click', () => {
        modal.style.display = 'flex';
        document.getElementById('bug-reporter-desc').focus();
    });

    document.getElementById('bug-cancel').addEventListener('click', () => {
        modal.style.display = 'none';
        document.getElementById('bug-reporter-desc').value = '';
    });

    document.getElementById('bug-submit').addEventListener('click', async () => {
        const description = document.getElementById('bug-reporter-desc').value;
        if (!description.trim()) {
            alert('Please enter a description.');
            return;
        }

        const submitBtn = document.getElementById('bug-submit');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting...';

        const bugData = {
            description: description,
            url: window.location.href,
            userAgent: navigator.userAgent,
            timestamp: new Date().toISOString(),
            screenResolution: \`\${window.innerWidth}x\${window.innerHeight}\`
        };

        try {
            const token = localStorage.getItem('token');
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = 'Bearer ' + token;

            const res = await fetch('/api/bug-report', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(bugData)
            });

            if (res.ok) {
                alert('Bug report submitted successfully! Thank you.');
                modal.style.display = 'none';
                document.getElementById('bug-reporter-desc').value = '';
            } else {
                alert('Failed to submit bug report. Please try again later.');
            }
        } catch (e) {
            console.error(e);
            alert('An error occurred while submitting the report.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Report';
        }
    });
});
