const statusEl = document.getElementById('status');
const connectBtn = document.getElementById('connectBtn');
const calibrateBtn = document.getElementById('calibrateBtn');

const valAlpha = document.getElementById('valAlpha');
const valBeta = document.getElementById('valBeta');
const valGamma = document.getElementById('valGamma');
const valRate = document.getElementById('valRate');

let socket = null;
let isConnected = false;
let isReading = false;

// Calibration offsets
let calAlpha = 0;
let calBeta = 0;
let calGamma = 0;

// Rate calculation
let updatesThisSecond = 0;
setInterval(() => {
    valRate.textContent = `${updatesThisSecond} Hz`;
    updatesThisSecond = 0;
}, 1000);

connectBtn.addEventListener('click', async () => {
    if (isConnected) {
        disconnect();
    } else {
        await connect();
    }
});

calibrateBtn.addEventListener('click', () => {
    // Flag to trigger calibration on next reading
    calAlpha = currentRawAlpha;
    calBeta = currentRawBeta;
    calGamma = currentRawGamma;
});

let currentRawAlpha = 0;
let currentRawBeta = 0;
let currentRawGamma = 0;

async function requestOrientationPermission() {
    // Request permission for iOS 13+ devices
    if (typeof DeviceOrientationEvent !== 'undefined' && typeof DeviceOrientationEvent.requestPermission === 'function') {
        try {
            const permissionState = await DeviceOrientationEvent.requestPermission();
            if (permissionState !== 'granted') {
                alert('Permission to access device orientation was denied');
                return false;
            }
        } catch (error) {
            console.error(error);
            alert('Error requesting orientation permission');
            return false;
        }
    }
    return true;
}

async function connect() {
    const hasPermission = await requestOrientationPermission();
    if (!hasPermission) return;

    // Connect to WebSocket server running on the same IP but port 8001
    const wsUrl = `wss://${window.location.hostname}:8001`;
    statusEl.textContent = 'Connecting...';
    
    try {
        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            isConnected = true;
            statusEl.textContent = 'Connected';
            statusEl.className = 'status connected';
            connectBtn.textContent = 'Disconnect';
            connectBtn.classList.replace('primary', 'secondary');
            calibrateBtn.disabled = false;
            
            // Start listening to gyro
            startReading();
        };

        socket.onclose = () => {
            disconnect();
        };

        socket.onerror = (error) => {
            console.error('WebSocket Error:', error);
            statusEl.textContent = 'Connection Error';
            disconnect();
        };
    } catch (e) {
        console.error(e);
        statusEl.textContent = 'Error connecting';
    }
}

function disconnect() {
    if (socket) {
        socket.close();
        socket = null;
    }
    isConnected = false;
    statusEl.textContent = 'Disconnected';
    statusEl.className = 'status disconnected';
    connectBtn.textContent = 'Connect & Start Gyro';
    connectBtn.classList.replace('secondary', 'primary');
    calibrateBtn.disabled = true;
    stopReading();
}

function startReading() {
    if (!isReading) {
        window.addEventListener('deviceorientation', handleOrientation);
        isReading = true;
    }
}

function stopReading() {
    if (isReading) {
        window.removeEventListener('deviceorientation', handleOrientation);
        isReading = false;
    }
}

function handleOrientation(event) {
    if (!isConnected || socket.readyState !== WebSocket.OPEN) return;

    // The event properties alpha, beta, gamma are in degrees
    let alpha = event.alpha || 0; // Z-axis (0 to 360)
    let beta = event.beta || 0;   // X-axis (-180 to 180)
    let gamma = event.gamma || 0; // Y-axis (-90 to 90)

    currentRawAlpha = alpha;
    currentRawBeta = beta;
    currentRawGamma = gamma;

    // Apply calibration
    let outAlpha = alpha - calAlpha;
    let outBeta = beta - calBeta;
    let outGamma = gamma - calGamma;

    // Update UI
    valAlpha.textContent = outAlpha.toFixed(2);
    valBeta.textContent = outBeta.toFixed(2);
    valGamma.textContent = outGamma.toFixed(2);
    updatesThisSecond++;

    // Send binary payload for much faster processing and lower GC overhead
    // 3 floats * 4 bytes = 12 bytes
    const buffer = new Float32Array([outAlpha, outBeta, outGamma]);
    socket.send(buffer);
}
