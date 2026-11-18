content = open('C:/SurakshaEdge/surakshaedge/dashboard/index.html', encoding='utf-8').read()

checks = {
    'Audio badge hardcoded MFCC-CNN ACTIVE': 'MFCC-CNN ACTIVE' in content and 'stat-audio-badge' in content,
    'FPS stat-val hardcoded 18.0': '>18.0<' in content,
    'Latency stat-val hardcoded 55ms': '>55ms<' in content,
    'demo-token hardcoded in JS': 'demo-token' in content,
    'Has WS reconnect (setTimeout)': 'reconnect' in content.lower(),
    'fetchHealth / pollHealth function': 'fetchHealth' in content or 'pollHealth' in content,
    'DOMContentLoaded init': 'DOMContentLoaded' in content,
    'Fetches /cameras on load': "fetch('/cameras')" in content or 'fetch(`/cameras`)' in content,
    'Updates badge-cams from server': 'badge-cams' in content and 'cameras' in content,
    'Settings thresholds read-only note': 'read-only' in content,
    'Has /api/health poll in JS (checkHealth)': 'checkHealth' in content,
    'Service worker registered': 'serviceWorker' in content,
    'manifest.json linked': 'manifest.json' in content,
    'Has Error handling for WS fail': 'onerror' in content.lower() or 'ws.onerror' in content,
    'CSP meta tag present': 'Content-Security-Policy' in content,
}

for label, result in checks.items():
    status = '✅' if result else '❌'
    print(f'{status} {label}')

# Count lines
print(f'\nTotal HTML lines: {len(content.splitlines())}')

# Find all fetch() calls
import re
fetches = re.findall(r"fetch\(['\"`]([^'\"`]+)['\"`]", content)
print(f'\nFetch calls found: {fetches}')
