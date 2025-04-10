// DOM Elements
const loginSection = document.getElementById('login-section');
const userInfo = document.getElementById('user-info');
const logoutBtn = document.getElementById('logout-btn');
const cardForm = document.getElementById('card-form');
const resultsSection = document.getElementById('results');

// Form Elements
const brandInput = document.getElementById('brand');
const setNameInput = document.getElementById('set-name');
const yearInput = document.getElementById('year');
const conditionInput = document.getElementById('condition');
const playerNameInput = document.getElementById('player-name');
const cardNumberInput = document.getElementById('card-number');
const cardVariationInput = document.getElementById('card-variation');

// Results Elements
const predictedPriceElement = document.getElementById('predicted-price');
const confidenceScoreElement = document.getElementById('confidence-score');
const marketTrendElement = document.getElementById('market-trend');
const supplyLevelElement = document.getElementById('supply-level');
const priceTrendElement = document.getElementById('price-trend');
const recentSalesTable = document.getElementById('recent-sales');
const activeListingsTable = document.getElementById('active-listings');

// Initialize Firebase Authentication
firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
const provider = new firebase.auth.GoogleAuthProvider();

// Handle Authentication State Changes
auth.onAuthStateChanged((user) => {
    if (user) {
        // User is signed in
        loginSection.classList.add('hidden');
        userInfo.classList.remove('hidden');
        document.getElementById('user-name').textContent = user.displayName;
        document.getElementById('user-email').textContent = user.email;
    } else {
        // User is signed out
        loginSection.classList.remove('hidden');
        userInfo.classList.add('hidden');
        resultsSection.classList.add('hidden');
    }
});

// Google Sign In
document.getElementById('google-login').addEventListener('click', () => {
    auth.signInWithPopup(provider)
        .catch((error) => {
            console.error('Error during sign in:', error);
            alert('Error signing in with Google. Please try again.');
        });
});

// Sign Out
logoutBtn.addEventListener('click', () => {
    auth.signOut()
        .catch((error) => {
            console.error('Error signing out:', error);
            alert('Error signing out. Please try again.');
        });
});

// Handle collapsible sections
document.querySelectorAll('.collapsible-btn').forEach(button => {
    button.addEventListener('click', () => {
        const content = button.nextElementSibling;
        content.classList.toggle('active');
        button.setAttribute('aria-expanded', content.classList.contains('active'));
    });
});

// Handle Form Submission
cardForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        brand: brandInput.value,
        set_name: setNameInput.value,
        year: parseInt(yearInput.value),
        condition: conditionInput.value,
        player_name: playerNameInput.value,
        card_number: cardNumberInput.value,
        card_variation: cardVariationInput.value
    };

    try {
        console.log('Sending form data:', formData);
        const response = await fetch('/api/price', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json();
        console.log('API Response:', data);
        console.log('Recent Sales:', data.recent_sales);
        console.log('Active Listings:', data.active_listings);
        displayResults(data);
    } catch (error) {
        console.error('Error:', error);
        alert('Error getting price prediction. Please try again.');
    }
});

// Display Results
function displayResults(data) {
    console.log('Displaying results:', data);
    
    // Update predicted price and confidence score
    if (predictedPriceElement) {
        predictedPriceElement.textContent = `$${data.predicted_price.toFixed(2)}`;
    }
    if (confidenceScoreElement) {
        confidenceScoreElement.textContent = `${(data.confidence_score * 100).toFixed(0)}%`;
    }
    
    // Update market analysis
    if (marketTrendElement) {
        marketTrendElement.textContent = data.market_trend || '-';
    }
    if (supplyLevelElement) {
        supplyLevelElement.textContent = data.supply_level || '-';
    }
    if (priceTrendElement) {
        priceTrendElement.textContent = data.price_trend || '-';
    }
    if (avgSalePriceElement) {
        avgSalePriceElement.textContent = data.average_sale_price ? `$${data.average_sale_price.toFixed(2)}` : '-';
    }
    if (avgActivePriceElement) {
        avgActivePriceElement.textContent = data.average_active_price ? `$${data.average_active_price.toFixed(2)}` : '-';
    }
    
    // Update recent sales
    const recentSalesList = document.getElementById('recent-sales-list');
    if (recentSalesList) {
        recentSalesList.innerHTML = '';  // Clear existing content
        
        if (data.recent_sales && data.recent_sales.length > 0) {
            data.recent_sales.forEach(sale => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${sale.title || 'N/A'}</td>
                    <td>$${sale.price.toFixed(2)}</td>
                    <td>${sale.condition || 'Unknown'}</td>
                    <td>${new Date(sale.date).toLocaleDateString()}</td>
                `;
                recentSalesList.appendChild(row);
            });
        } else {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="4">No recent sales found</td>';
            recentSalesList.appendChild(row);
        }
    }
    
    // Update active listings
    const activeListingsList = document.getElementById('active-listings-list');
    if (activeListingsList) {
        activeListingsList.innerHTML = '';  // Clear existing content
        
        if (data.active_listings && data.active_listings.length > 0) {
            data.active_listings.forEach(listing => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${listing.title || 'N/A'}</td>
                    <td>$${listing.price.toFixed(2)}</td>
                    <td>${listing.condition || 'Unknown'}</td>
                    <td>${listing.listing_type || 'N/A'}</td>
                `;
                activeListingsList.appendChild(row);
            });
        } else {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="4">No active listings found</td>';
            activeListingsList.appendChild(row);
        }
    }
    
    // Update counts
    const recentSalesCount = document.querySelector('#recent-sales-section .count');
    const activeListingsCount = document.querySelector('#active-listings-section .count');
    
    if (recentSalesCount) {
        recentSalesCount.textContent = `(${data.recent_sales ? data.recent_sales.length : 0})`;
    }
    if (activeListingsCount) {
        activeListingsCount.textContent = `(${data.active_listings ? data.active_listings.length : 0})`;
    }
    
    // Show results section
    const resultsSection = document.querySelector('.results-section');
    if (resultsSection) {
        resultsSection.style.display = 'block';
    }
    
    // Initialize collapsible sections
    initializeCollapsibleSections();
}

// Initialize collapsible sections
function initializeCollapsibleSections() {
    console.log('Initializing collapsible sections');
    
    // Initialize recent sales section
    const recentSalesSection = document.getElementById('recent-sales-section');
    if (recentSalesSection) {
        const recentSalesBtn = recentSalesSection.querySelector('.collapsible-btn');
        const recentSalesContent = recentSalesSection.querySelector('.collapsible-content');
        const recentSalesArrow = recentSalesSection.querySelector('.arrow');
        
        if (recentSalesBtn && recentSalesContent && recentSalesArrow) {
            // Set initial state
            recentSalesContent.style.display = 'none';
            recentSalesBtn.classList.remove('active');
            recentSalesArrow.textContent = '▶';
            
            // Remove existing event listeners by cloning
            const newRecentSalesBtn = recentSalesBtn.cloneNode(true);
            recentSalesBtn.parentNode.replaceChild(newRecentSalesBtn, recentSalesBtn);
            
            // Add new event listener
            newRecentSalesBtn.addEventListener('click', () => {
                const isActive = newRecentSalesBtn.classList.contains('active');
                newRecentSalesBtn.classList.toggle('active');
                recentSalesContent.style.display = isActive ? 'none' : 'block';
                recentSalesArrow.textContent = isActive ? '▶' : '▼';
            });
        }
    }
    
    // Initialize active listings section
    const activeListingsSection = document.getElementById('active-listings-section');
    if (activeListingsSection) {
        const activeListingsBtn = activeListingsSection.querySelector('.collapsible-btn');
        const activeListingsContent = activeListingsSection.querySelector('.collapsible-content');
        const activeListingsArrow = activeListingsSection.querySelector('.arrow');
        
        if (activeListingsBtn && activeListingsContent && activeListingsArrow) {
            // Set initial state
            activeListingsContent.style.display = 'none';
            activeListingsBtn.classList.remove('active');
            activeListingsArrow.textContent = '▶';
            
            // Remove existing event listeners by cloning
            const newActiveListingsBtn = activeListingsBtn.cloneNode(true);
            activeListingsBtn.parentNode.replaceChild(newActiveListingsBtn, activeListingsBtn);
            
            // Add new event listener
            newActiveListingsBtn.addEventListener('click', () => {
                const isActive = newActiveListingsBtn.classList.contains('active');
                newActiveListingsBtn.classList.toggle('active');
                activeListingsContent.style.display = isActive ? 'none' : 'block';
                activeListingsArrow.textContent = isActive ? '▶' : '▼';
            });
        }
    }
}

// Helper function to update tables
function updateTable(tableElement, data) {
    const tbody = tableElement.querySelector('tbody');
    tbody.innerHTML = '';

    data.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>$${item.price.toFixed(2)}</td>
            <td>${item.date}</td>
            <td>${item.condition}</td>
            <td><a href="${item.url}" target="_blank">View</a></td>
        `;
        tbody.appendChild(row);
    });
} 