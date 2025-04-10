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
        setName: setNameInput.value,
        year: parseInt(yearInput.value),
        condition: conditionInput.value,
        playerName: playerNameInput.value,
        cardNumber: cardNumberInput.value,
        cardVariation: cardVariationInput.value
    };

    try {
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
        displayResults(data);
    } catch (error) {
        console.error('Error:', error);
        alert('Error getting price prediction. Please try again.');
    }
});

// Display Results
function displayResults(data) {
    resultsSection.classList.remove('hidden');
    
    // Update basic information
    document.getElementById('predicted-price').textContent = `$${data.predictedPrice.toFixed(2)}`;
    document.getElementById('confidence-score').textContent = `${(data.confidenceScore * 100).toFixed(1)}%`;
    
    // Update market analysis
    document.getElementById('market-trend').textContent = data.marketAnalysis.marketTrend;
    document.getElementById('supply-level').textContent = data.marketAnalysis.supplyLevel;
    document.getElementById('price-trend').textContent = data.marketAnalysis.priceTrend;
    document.getElementById('avg-sale-price').textContent = `$${data.marketAnalysis.avgSalePrice.toFixed(2)}`;
    document.getElementById('avg-active-price').textContent = `$${data.marketAnalysis.avgActivePrice.toFixed(2)}`;

    // Update recent sales
    const recentSalesList = document.getElementById('recent-sales-list');
    recentSalesList.innerHTML = '';
    data.recentSales.forEach(sale => {
        const li = document.createElement('li');
        li.innerHTML = `
            <div class="title">${sale.title}</div>
            <div class="details">
                $${sale.price.toFixed(2)} - ${sale.condition}
                <br>
                Sold: ${new Date(sale.saleDate).toLocaleDateString()}
            </div>
        `;
        recentSalesList.appendChild(li);
    });
    document.querySelector('.collapsible-section:nth-child(1) .count').textContent = `(${data.recentSales.length})`;

    // Update active listings
    const activeListingsList = document.getElementById('active-listings-list');
    activeListingsList.innerHTML = '';
    data.activeListings.forEach(listing => {
        const li = document.createElement('li');
        li.innerHTML = `
            <div class="title">${listing.title}</div>
            <div class="details">
                $${listing.price.toFixed(2)} - ${listing.condition}
                <br>
                Type: ${listing.listingType}
            </div>
        `;
        activeListingsList.appendChild(li);
    });
    document.querySelector('.collapsible-section:nth-child(2) .count').textContent = `(${data.activeListings.length})`;

    // Show results section
    document.querySelector('.results-section').style.display = 'block';
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