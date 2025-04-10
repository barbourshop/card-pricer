// DOM Elements
const loginSection = document.getElementById('login-section');
const userInfo = document.getElementById('user-info');
const logoutBtn = document.getElementById('logout-btn');
const cardForm = document.getElementById('pricing-form');
const resultsSection = document.getElementById('results');

// Form Elements
const brandInput = document.getElementById('brand');
const setNameInput = document.getElementById('set_name');
const yearInput = document.getElementById('year');
const conditionInput = document.getElementById('condition');
const playerNameInput = document.getElementById('player_name');
const cardNumberInput = document.getElementById('card_number');
const cardVariationInput = document.getElementById('card_variation');

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
    
    // Get form values
    const brand = document.getElementById('brand').value;
    const set_name = document.getElementById('set_name').value;
    const year = document.getElementById('year').value;
    const player_name = document.getElementById('player_name').value;
    const card_number = document.getElementById('card_number').value;
    const card_variation = document.getElementById('card_variation').value;
    const condition = document.getElementById('condition').value;
    
    // Get auth token
    const authToken = localStorage.getItem('auth_token');
    
    if (!authToken) {
        alert('Please sign in to get card prices');
        return;
    }
    
    // Show loading state
    document.getElementById('pricing-results').innerHTML = '<div class="loading">Loading...</div>';
    document.querySelector('.results-section').style.display = 'block';
    
    // Make API request
    fetch('/api/price', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
            brand: brand,
            set_name: set_name,
            year: year,
            player_name: player_name,
            card_number: card_number,
            card_variation: card_variation,
            condition: condition
        })
    })
    .then(response => {
        if (response.status === 401) {
            // Token expired or invalid
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user');
            window.location.reload();
            return;
        }
        return response.json();
    })
    .then(data => {
        console.log('API Response:', data);
        console.log('Recent Sales:', data.recent_sales);
        console.log('Active Listings:', data.active_listings);
        console.log('Market Analysis:', data.market_analysis);
        
        // Restore the original structure if it was replaced
        if (!document.getElementById('predicted-price')) {
            document.getElementById('pricing-results').innerHTML = `
                <div class="price-summary">
                    <div class="price-highlights">
                        <div class="price-item">
                            <h3>Predicted Price: <span id="predicted-price">$0.00</span></h3>
                            <p>Confidence Score: <span id="confidence-score">0%</span></p>
                            <p>Market Trend: <span id="market-trend">-</span></p>
                        </div>
                        <div class="price-item">
                            <h3>Average Sale Price: <span id="avg-sale-price">$0.00</span></h3>
                            <p>Price Trend: <span id="price-trend">-</span></p>
                            <p>Recent Sales: <span id="recent-sales-count">0</span></p>
                        </div>
                        <div class="price-item">
                            <h3>Average Active Price: <span id="avg-active-price">$0.00</span></h3>
                            <p>Supply Level: <span id="supply-level">-</span></p>
                            <p>Active Listings: <span id="active-listings-count">0</span></p>
                        </div>
                    </div>
                </div>
                
                <div class="sales-data">
                    <div id="recent-sales-section" class="collapsible-section">
                        <button class="collapsible-btn">
                            Recent Sales <span class="count">(0)</span>
                            <span class="arrow">▶</span>
                        </button>
                        <div class="collapsible-content">
                            <div class="section-description">
                                <p>Items that have been sold in the last 90 days</p>
                            </div>
                            <table class="data-table">
                                <thead>
                                    <tr>
                                        <th>Title</th>
                                        <th>Price</th>
                                        <th>Condition</th>
                                        <th>Date</th>
                                    </tr>
                                </thead>
                                <tbody id="recent-sales-list">
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <div id="active-listings-section" class="collapsible-section">
                        <button class="collapsible-btn">
                            Active Listings <span class="count">(0)</span>
                            <span class="arrow">▶</span>
                        </button>
                        <div class="collapsible-content">
                            <div class="section-description">
                                <p>Items currently available for purchase</p>
                            </div>
                            <table class="data-table">
                                <thead>
                                    <tr>
                                        <th>Title</th>
                                        <th>Price</th>
                                        <th>Condition</th>
                                        <th>Type</th>
                                    </tr>
                                </thead>
                                <tbody id="active-listings-list">
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            `;
            
            // Reinitialize collapsible sections
            initializeCollapsibleSections();
        }
        
        // Update basic information
        const predictedPriceElement = document.getElementById('predicted-price');
        const confidenceScoreElement = document.getElementById('confidence-score');
        
        if (predictedPriceElement) {
            predictedPriceElement.textContent = `$${data.predicted_price.toFixed(2)}`;
        }
        if (confidenceScoreElement) {
            confidenceScoreElement.textContent = `${(data.confidence_score * 100).toFixed(1)}%`;
        }
        
        // Update market analysis
        const marketTrendElement = document.getElementById('market-trend');
        const supplyLevelElement = document.getElementById('supply-level');
        const priceTrendElement = document.getElementById('price-trend');
        const avgSalePriceElement = document.getElementById('avg-sale-price');
        const avgActivePriceElement = document.getElementById('avg-active-price');
        
        if (marketTrendElement && data.market_analysis) {
            // Set the text content
            marketTrendElement.textContent = data.market_analysis.market_trend || '-';
        }
        
        if (supplyLevelElement && data.market_analysis) {
            // Set the text content
            supplyLevelElement.textContent = data.market_analysis.supply_level || '-';
        }
        
        if (priceTrendElement && data.market_analysis) {
            // Set the text content
            priceTrendElement.textContent = data.market_analysis.price_trend || '-';
        }
        
        if (avgSalePriceElement && data.market_analysis) {
            avgSalePriceElement.textContent = data.market_analysis.avg_sale_price ? 
                `$${data.market_analysis.avg_sale_price.toFixed(2)}` : '-';
        }
        
        if (avgActivePriceElement && data.market_analysis) {
            avgActivePriceElement.textContent = data.market_analysis.avg_active_price ? 
                `$${data.market_analysis.avg_active_price.toFixed(2)}` : '-';
        }
        
        // Update counts in the price cards
        const recentSalesCountElement = document.getElementById('recent-sales-count');
        const activeListingsCountElement = document.getElementById('active-listings-count');
        
        if (recentSalesCountElement) {
            const recentSalesCount = data.recent_sales ? data.recent_sales.length : 0;
            recentSalesCountElement.textContent = recentSalesCount;
            console.log('Setting recent sales count to:', recentSalesCount);
        }
        
        if (activeListingsCountElement) {
            const activeListingsCount = data.active_listings ? data.active_listings.length : 0;
            activeListingsCountElement.textContent = activeListingsCount;
            console.log('Setting active listings count to:', activeListingsCount);
        }
        
        // Update recent sales
        const recentSalesList = document.getElementById('recent-sales-list');
        if (recentSalesList) {
            recentSalesList.innerHTML = '';
            console.log('Recent Sales Data:', data.recent_sales);
            if (data.recent_sales && data.recent_sales.length > 0) {
                data.recent_sales.forEach(sale => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${sale.title || 'N/A'}</td>
                        <td>$${sale.price.toFixed(2)}</td>
                        <td>${sale.condition || 'Unknown'}</td>
                        <td>${new Date(sale.date).toLocaleDateString()}</td>
                    `;
                    row.classList.add('recent-sale-row');
                    recentSalesList.appendChild(row);
                });
            } else {
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="4" style="text-align: center;">No recent sales found</td>';
                recentSalesList.appendChild(row);
            }
        }
        
        // Update recent sales count in the collapsible section
        const recentSalesCount = document.querySelector('#recent-sales-section .count');
        if (recentSalesCount) {
            const count = data.recent_sales ? data.recent_sales.length : 0;
            recentSalesCount.textContent = `(${count})`;
            console.log('Setting recent sales section count to:', count);
        }
        
        // Update active listings
        const activeListingsList = document.getElementById('active-listings-list');
        if (activeListingsList) {
            activeListingsList.innerHTML = '';
            console.log('Active Listings Data:', data.active_listings);
            console.log('Active Listings Length:', data.active_listings ? data.active_listings.length : 0);
            
            if (data.active_listings && data.active_listings.length > 0) {
                data.active_listings.forEach(listing => {
                    console.log('Processing active listing:', listing);
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${listing.title || 'N/A'}</td>
                        <td>$${listing.price.toFixed(2)}</td>
                        <td>${listing.condition || 'Unknown'}</td>
                        <td>${listing.listing_type || 'N/A'}</td>
                    `;
                    row.classList.add('active-listing-row');
                    activeListingsList.appendChild(row);
                });
            } else {
                console.log('No active listings found in the response');
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="4" style="text-align: center;">No active listings found</td>';
                activeListingsList.appendChild(row);
            }
        } else {
            console.error('Active listings list element not found in the DOM');
        }
        
        // Update active listings count in the collapsible section
        const activeListingsCount = document.querySelector('#active-listings-section .count');
        if (activeListingsCount) {
            const count = data.active_listings ? data.active_listings.length : 0;
            activeListingsCount.textContent = `(${count})`;
            console.log('Setting active listings section count to:', count);
        }
        
        // Make sure the results section is visible
        const resultsSection = document.querySelector('.results-section');
        if (resultsSection) {
            resultsSection.style.display = 'block';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('pricing-results').innerHTML = '<div class="error">An error occurred while fetching the price. Please try again.</div>';
        // Show the results section even if there's an error
        document.querySelector('.results-section').style.display = 'block';
    });
});

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

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Initialize DOM elements
    loginSection = document.getElementById('login-section');
    userInfo = document.getElementById('user-info');
    logoutBtn = document.getElementById('logout-btn');
    cardForm = document.getElementById('pricing-form');
    resultsSection = document.querySelector('.results-section');
    
    // Initialize form elements
    brandInput = document.getElementById('brand');
    setNameInput = document.getElementById('set_name');
    yearInput = document.getElementById('year');
    conditionInput = document.getElementById('condition');
    playerNameInput = document.getElementById('player_name');
    cardNumberInput = document.getElementById('card_number');
    cardVariationInput = document.getElementById('card_variation');
    
    // Initialize results elements
    predictedPriceElement = document.getElementById('predicted-price');
    confidenceScoreElement = document.getElementById('confidence-score');
    marketTrendElement = document.getElementById('market-trend');
    supplyLevelElement = document.getElementById('supply-level');
    priceTrendElement = document.getElementById('price-trend');
    avgSalePriceElement = document.getElementById('avg-sale-price');
    avgActivePriceElement = document.getElementById('avg-active-price');
    
    // Make sure results section is visible by default
    if (resultsSection) {
        resultsSection.style.display = 'block';
    }
    
    // Check if user is already logged in
    const user = localStorage.getItem('user');
    if (user) {
        const userData = JSON.parse(user);
        loginSection.style.display = 'none';
        document.getElementById('main-content').style.display = 'block';
        userInfo.textContent = `Logged in as: ${userData.email}`;
    }
    
    // Add event listeners
    if (logoutBtn) {
        logoutBtn.addEventListener('click', signOut);
    }
    
    if (cardForm) {
        cardForm.addEventListener('submit', handleFormSubmit);
    }
    
    // Initialize collapsible sections
    initializeCollapsibleSections();
}); 