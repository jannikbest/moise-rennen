const MOISE_CONFIG = {
    websocket: {
        // Stats service (local / Pi). Hardware ESP is upstream of the service.
        url: 'ws://localhost:8770/',
        reconnectInterval: 2000,
        maxReconnectAttempts: -1
    },
    staleTimeoutMs: 3000,
    maxPoints: 15,
    mausIcon: 'maus.png',
    laneLabels: {
        1: 'Speedy',
        2: 'Pilzy',
        3: 'Emdy',
        4: 'Kety',
        5: 'Koky'
    },
    statsRotateMs: 8000,
    statsDetailIdleMs: 60000,
    // Show "Start race" when stats reports testMode (mock ESP)
    testMode: true
};
