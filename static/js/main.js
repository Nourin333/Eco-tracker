// API Utility Functions
async function postData(url = '', data = {}) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    });
    return response.json();
}

// Display alert messages
function showAlert(message, type = 'error', elementId = 'alert-box') {
    const box = document.getElementById(elementId);
    if (!box) return;
    box.className = `alert alert-${type}`;
    box.innerText = message;
    box.style.display = 'block';
    setTimeout(() => {
        box.style.display = 'none';
    }, 5000);
}

// Check for missing data reminder
function showMonthlyReminder() {
    const banner = document.getElementById('monthly-reminder');
    if (!banner) return;
    
    // Check local storage so we don't spam the user every reload
    const lastNotified = localStorage.getItem('eco_last_notified');
    const currentMonth = new Date().toISOString().slice(0, 7); // YYYY-MM
    
    if (lastNotified !== currentMonth) {
        banner.style.display = 'block';
        banner.innerText = "🍃 Reminder: Don't forget to enter your emissions data for this month!";
        // We will set this in localStorage when they actually submit the data
    }
}

// Form Submission Handlers
document.addEventListener('DOMContentLoaded', () => {
    
    // Monthly Reminder on Dashboard
    if (window.location.pathname === '/dashboard') {
        showMonthlyReminder();
    }
    
    // Login Form
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            try {
                const result = await postData('/api/login', { email, password });
                if (result.error) {
                    showAlert(result.error, 'error');
                } else {
                    window.location.href = '/dashboard';
                }
            } catch (error) {
                showAlert('An error occurred. Please try again.', 'error');
            }
        });
    }

    // Register Form
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('name').value;
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            try {
                const result = await postData('/api/register', { name, email, password });
                if (result.error) {
                    showAlert(result.error, 'error');
                } else {
                    showAlert('Registration successful! Redirecting...', 'success');
                    setTimeout(() => window.location.href = '/login', 1500);
                }
            } catch (error) {
                showAlert('An error occurred. Please try again.', 'error');
            }
        });
    }

    // Input Data Form
    const inputForm = document.getElementById('input-form');
    if (inputForm) {
        inputForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const elec = document.getElementById('electricity_units').value;
            const petrol = document.getElementById('petrol_litres').value;
            const month = document.getElementById('month').value;
            
            try {
                const result = await postData('/api/submit-data', { 
                    electricity_units: elec, 
                    petrol_litres: petrol,
                    month: month || undefined
                });
                
                if (result.error) {
                    showAlert(result.error, 'error');
                } else {
                    showAlert('Data submitted successfully! Carbon logic computed.', 'success');
                    // Mark as notified for this month
                    const currentMonth = new Date().toISOString().slice(0, 7);
                    localStorage.setItem('eco_last_notified', currentMonth);
                    
                    setTimeout(() => window.location.href = '/dashboard', 1500);
                }
            } catch (error) {
                showAlert('An error occurred. Please try again.', 'error');
            }
        });
    }

    // Logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            await postData('/api/logout');
            window.location.href = '/login';
        });
    }
    
    // Dashboard Data Fetch
    if (window.location.pathname === '/dashboard') {
        fetch('/api/get-dashboard')
            .then(res => res.json())
            .then(data => {
                const v = obj => document.getElementById(obj.id);
                if (data.user_name) v({id: 'user-name'}).innerText = data.user_name;
                
                if (data.lifetime) {
                    if(v({id: 'total-co2'})) v({id: 'total-co2'}).innerText = data.lifetime.total_co2 + ' kg';
                    if(v({id: 'carbon-saved'})) v({id: 'carbon-saved'}).innerText = data.lifetime.carbon_saved + ' kg';
                    if(v({id: 'total-credits'})) v({id: 'total-credits'}).innerText = data.lifetime.credits;
                    if(v({id: 'wallet-value'})) v({id: 'wallet-value'}).innerText = '₹ ' + data.lifetime.wallet_value;
                }
                
                if (data.latest_month) {
                    const lm = document.getElementById('latest-month-info');
                    if (lm) {
                        lm.innerHTML = `In ${data.latest_month.month}, you emitted ${data.latest_month.total_co2}kg CO2 and saved ${data.latest_month.carbon_saved}kg CO2.`;
                    }
                }
            })
            .catch(err => console.error("Error fetching dashboard data:", err));
    }
});
