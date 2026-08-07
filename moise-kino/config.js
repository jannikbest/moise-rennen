const MOISE_CONFIG = {
    websocket: {
        // Same host as the page → works for localhost and hostname.local over LAN.
        url: `ws://${typeof location !== 'undefined' ? location.hostname : 'localhost'}:8770/`,
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
    statsDetailIdleMs: 60000
};
