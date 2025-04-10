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
    predictedPriceElement.textContent = `$${data.predictedPrice.toFixed(2)}`;
    confidenceScoreElement.textContent = `${(data.confidenceScore * 100).toFixed(1)}%`;
    marketTrendElement.textContent = data.marketTrend;
    supplyLevelElement.textContent = data.supplyLevel;
    priceTrendElement.textContent = data.priceTrend;

    // Update recent sales table
    updateTable(recentSalesTable, data.recentSales);

    // Update active listings table
    updateTable(activeListingsTable, data.activeListings);
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