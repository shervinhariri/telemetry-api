// Simple test script to verify JavaScript is working
console.log('🔧 Test script loaded successfully');

// Test function to update dashboard
function testUpdateDashboard() {
    console.log('🧪 Testing dashboard update...');
    
    // Test if we can find the elements
    const elements = ['queue-lag', 'avg-risk', 'threat-matches', 'error-rate'];
    let foundCount = 0;
    
    elements.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            console.log(`✅ Found element: ${id}`);
            foundCount++;
        } else {
            console.log(`❌ Missing element: ${id}`);
        }
    });
    
    console.log(`📊 Found ${foundCount}/${elements.length} elements`);
    
    // Test API call
    fetch('http://localhost:8080/v1/metrics', {
        headers: { 'Authorization': 'Bearer TEST_KEY' }
    })
    .then(response => response.json())
    .then(data => {
        console.log('✅ API call successful:', data);
        
        // Update elements if found
        elements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                switch(id) {
                    case 'queue-lag':
                        element.textContent = data.queue_depth || '0';
                        break;
                    case 'avg-risk':
                        const riskCount = data.totals?.risk_count || 0;
                        const riskSum = data.totals?.risk_sum || 0;
                        element.textContent = riskCount > 0 ? (riskSum / riskCount).toFixed(1) : '0.0';
                        break;
                    case 'threat-matches':
                        element.textContent = data.totals?.threat_matches || '0';
                        break;
                    case 'error-rate':
                        element.textContent = '0.0%';
                        break;
                }
                console.log(`✅ Updated ${id}: ${element.textContent}`);
            }
        });
    })
    .catch(error => {
        console.error('❌ API call failed:', error);
    });
}

// Make test function available globally
window.testUpdateDashboard = testUpdateDashboard;

// Auto-run test after page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 DOM loaded, running test...');
    setTimeout(testUpdateDashboard, 1000);
});
