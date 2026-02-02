function escapeHtml(text) {
            if (!text) return "";
            return String(text)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        function formatAnalysis(text) {
            if (!text) return '';
            return String(text)
                .split('\n')
                .map(line => line.trim())
                .filter(Boolean)
                .map(line => `<p>${escapeHtml(line)}</p>`)
                .join('');
        }
        
        const API_BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
            ? 'http://127.0.0.1:8000' 
            : 'https://nesta-signal-backend.onrender.com';

        // --- GLOBAL STATE ---
        const AppState = {
            currentSignals: [], // Displayed signals (Scan or DB View)
            lastScanResults: [], // Cache for "Current Scan" view
            currentSaved: [], // Full DB cache
            activeFilter: 'scan', // Track current filter
            radarChart: null,
            isProcessing: false,
            scanController: null,
            loadIntervals: [],
            liveTerminalInterval: null,
            liveTerminalIndex: 0,
            networkChart: null,
            currentSynth: null
        };

        const MISSION_EMOJIS = { 'A Fairer Start': '📚', 'A Healthy Life': '❤️‍🩹', 'A Sustainable Future': '🌳' };
        const LENS_EMOJIS = { 'Social': '👥', 'Tech': '🤖', 'Media': '🎙️', 'Powerhouse': '⚡' };
        
        // Nesta Mission Colors for Radar
        const MISSION_COLORS = {
            'A Fairer Start': '#FDB633', // Yellow
            'A Healthy Life': '#F6A4B7', // Pink
            'A Sustainable Future': '#18A48C', // Green
            'Default': '#646363' // Dark Grey for Mission Adjacent/Others
        };

        // --- IMPROVED BACKEND WARMUP LOGIC FOR RENDER COLD STARTS ---
        async function warmBackend() {
            // Helper function for a single check
            const check = async () => {
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(), 3000); // 3s timeout for each ping
                try {
                    const res = await fetch(`${API_BASE_URL}/`, { method: 'GET', cache: 'no-store', signal: controller.signal });
                    return res.ok;
                } catch (e) {
                    console.error('Backend check failed:', e);
                    return false;
                } finally {
                    clearTimeout(timeout);
                }
            };

            // 1. Try once immediately. If it's already warm, we are done.
            if (await check()) return true;

            // 2. If first check fails, backend is sleeping. Start Polling Loop.
            // Render free tier can take 30-90 seconds to wake up.
            showToast('Waking up Scout Agent... (This may take 60s)', 'normal');
            
            const start = Date.now();
            const MAX_WAIT_MS = 90000; // 90 seconds max wait
            let attempt = 0;

            while (Date.now() - start < MAX_WAIT_MS) {
                attempt++;
                await new Promise(r => setTimeout(r, 4000)); // Wait 4s between checks
                
                if (await check()) {
                    showToast('Agent Online!', 'success');
                    return true;
                }

                // Update user every 3rd failed attempt (approx 12s) to keep them engaged
                if (attempt % 3 === 0) {
                     showToast('Still waking up... please wait', 'normal');
                }
            }
            
            showToast('Connection failed. Please refresh.', 'error');
            return false;
        }

        async function initDashboard() {
            // Load the UI skeleton first so the page isn't blank
            toggleButtonState(); 
            switchFilter('scan');

            // Now perform the robust connection check
            const ready = await warmBackend();
            
            if (!ready) {
                document.getElementById('preview-grid').innerHTML = '<div class="text-center py-10 text-nesta-red font-bold">Backend Offline. Retrying preview load...</div>';
            }
            
            // Backend may still be waking up, attempt to fetch data regardless
            loadPreview();
        }

        function toggleButtonState() {
            if (AppState.isProcessing) return;
            const input = document.getElementById('topic-input');
            const broadBtn = document.getElementById('broad-btn');
            const searchBtn = document.getElementById('search-btn');
            const hasText = input.value.trim().length > 0;

            if (hasText) {
                broadBtn.classList.add('hidden');
                searchBtn.classList.remove('hidden');
            } else {
                broadBtn.classList.remove('hidden');
                searchBtn.classList.add('hidden');
            }
        }

        function generateFrictionQuery() {
            const topics = [
                // --- A SUSTAINABLE FUTURE ---
                "biomass boiler", "decarbonised housing", "low carbon built environment", "carbon capture storage",
                "climate tech", "green tech", "net zero material", "district heating", "heat network",
                "energy efficiency retrofit", "building insulation", "smart meter", "smart thermostat",
                "demand response", "electricity grid flexibility", "energy storage batteries", "geothermal heat",
                "green skills", "heat pumps", "heat batteries", "thermal energy storage", "blue hydrogen",
                "green hydrogen", "hydrogen boiler", "micro-chp", "photovoltaic", "solar thermal",
                "wind turbine", "community energy", "retrofitting",

                // --- A FAIRER START ---
                "school readiness", "executive function", "speech therapy", "childcare affordability",
                "nursery shortage", "early years curriculum", "montessori", "forest schools",
                "cognitive development", "language acquisition", "phonics", "numeracy", "gamified learning",
                "learning through play", "edtech", "parental leave", "work-life balance", "peer support groups",
                "classroom technology", "early years analytics", "motor skills development", "adhd diagnosis",
                "autism support", "dyslexia tools", "special educational needs", "infant sleep patterns",
                "maternal health", "fetal development", "family income support", "financial inclusion for parents",

                // --- A HEALTHY LIFE ---
                "ultra processed food", "precision fermentation", "glp-1", "semaglutide", "ozempic",
                "digital therapeutics", "gut microbiome", "personalized nutrition", "nutrigenomics",
                "sugar reduction", "salt reduction", "fat replacers", "plant-based protein", "lab-grown meat",
                "cellular agriculture", "mycoprotein", "insect protein", "vertical farming", "food environment",
                "dark kitchens", "ultra fast delivery", "robot chefs", "kitchen automation", "smart appliances",
                "food waste reduction", "upcycled food", "reformulation", "clean label", "functional food",
                "medical foods", "lifestyle medicine", "social prescribing", "mental health apps",
                "wearable health trackers", "remote patient monitoring", "telehealth", "online pharmacy",
                "metabolic health", "type 2 diabetes prevention", "obesity stigma", "food marketing regulation",
                "active travel", "micromobility", "e-bikes", "e-scooters", "walkable cities",

                // --- CROSS-CUTTING & TECH ---
                "generative ai", "synthetic biology", "quantum sensing", "privacy enhancing tech",
                "autonomous robotics", "computer vision", "natural language processing", "deepfakes",
                "algorithmic bias", "digital literacy", "online safety", "screen time impact",
                "virtual reality", "augmented reality", "immersive education", "social media influence",
                "data privacy", "cybersecurity", "blockchain", "web3", "metaverse", "5g connectivity",
                "internet of things", "smart cities", "digital inclusion", "tech ethics"
            ];
            const modifiers = window.FRICTION_MODIFIERS || [];
            if (!topics.length || !modifiers.length) {
                console.warn("Friction query lists are missing.");
                return;
            }
            const topic = topics[Math.floor(Math.random() * topics.length)];
            const modifier = modifiers[Math.floor(Math.random() * modifiers.length)];
            const input = document.getElementById('topic-input');
            input.value = `${topic} + "${modifier}"`;
            toggleButtonState();
        }

        // --- LOADING ANIMATION LOGIC ---
        function startLoadingSimulation(requestedCount) {
            const statuses = [
                "Initialising Scout Agent...", "Scanning Global Sources...", "Filtering Mainstream Noise...",
                "Applying Friction Method...", "Scoring Novelty & Evidence...", "Synthesising Intelligence..."
            ];
            let statusIndex = 0;
            stopLoadingSimulation(); 

            // Base duration roughly 25s for 1 signal, scaling up non-linearly
            // e.g., 5 signals might take 45s, 10 signals ~70s
            // This is just a simulation, but gives feedback based on request size.
            const SIMULATION_BASE_FACTOR = 250;
            const DEFAULT_REQUEST_COUNT = 5;
            const COUNT_MULTIPLIER = 40;

            const baseFactor = SIMULATION_BASE_FACTOR;
            const countFactor = (requestedCount || DEFAULT_REQUEST_COUNT) * COUNT_MULTIPLIER;
            const speed = baseFactor + countFactor;

            const statInt = setInterval(() => {
                statusIndex = (statusIndex + 1) % statuses.length;
                const el = document.getElementById('loading-status-text');
                if(el) {
                    el.style.opacity = '0';
                    setTimeout(() => { el.innerText = statuses[statusIndex]; el.style.opacity = '1'; }, 200);
                }
            }, 3500);
            AppState.loadIntervals.push(statInt);

            let progress = 0;
            const progInt = setInterval(() => {
                if(progress < 99) {
                    let increment = (100 - progress) / speed;
                    if(increment < 0.05) increment = 0.05; 
                    progress += increment;
                    const textEl = document.getElementById('loading-percent-text');
                    const barEl = document.getElementById('loading-bar-inner');
                    if(textEl) textEl.innerText = Math.floor(progress) + '%';
                    if(barEl) barEl.style.width = progress + '%';
                }
            }, 100);
            AppState.loadIntervals.push(progInt);
        }

        function stopLoadingSimulation() {
            AppState.loadIntervals.forEach(clearInterval);
            AppState.loadIntervals = [];
        }

        function addTerminalLine(text) {
            const terminal = document.getElementById('live-terminal');
            if (!terminal) return;
            const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const line = document.createElement('div');
            line.textContent = `> [${time}] ${text}`;
            terminal.appendChild(line);
            terminal.scrollTop = terminal.scrollHeight;
        }

        function startLiveTerminal() {
            const terminal = document.getElementById('live-terminal');
            if (terminal) {
                terminal.innerHTML = '<div class="opacity-70">&gt; Waiting for scan...</div>';
            }
            const messages = [
                'Initialising scout agent...',
                'Searching for relevant sources...',
                'Verifying deep links...',
                'Scraping signal context...',
                'Scoring novelty and evidence...',
                'Synthesising candidate signals...'
            ];
            AppState.liveTerminalIndex = 0;
            addTerminalLine(messages[AppState.liveTerminalIndex]);
            if (AppState.liveTerminalInterval) {
                clearInterval(AppState.liveTerminalInterval);
            }
            AppState.liveTerminalInterval = setInterval(() => {
                AppState.liveTerminalIndex = (AppState.liveTerminalIndex + 1) % messages.length;
                addTerminalLine(messages[AppState.liveTerminalIndex]);
            }, 4000);
        }

        function stopLiveTerminal() {
            if (AppState.liveTerminalInterval) {
                clearInterval(AppState.liveTerminalInterval);
                AppState.liveTerminalInterval = null;
            }
            addTerminalLine('Scan complete.');
        }

        function downloadSignalsAsCSV() {
            const signals = AppState.currentSignals.length > 0 ? AppState.currentSignals : AppState.lastScanResults;
            if (!signals || signals.length === 0) {
                showToast('No signals to download', 'error');
                return;
            }
            const headers = ['Title', 'URL', 'Hook', 'Novelty Score', 'Evidence Score', 'Mission'];
            const escapeCSV = (value) => {
                if (value === null || value === undefined) return '';
                const stringValue = String(value).replace(/"/g, '""');
                return `"${stringValue}"`;
            };
            const rows = signals.map((signal) => [
                escapeCSV(signal.title),
                escapeCSV(signal.final_url || signal.url),
                escapeCSV(signal.hook),
                escapeCSV(signal.score_novelty),
                escapeCSV(signal.score_evidence),
                escapeCSV(signal.mission)
            ]);
            const csv = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
            const mode = getSelectedScanMode();
            const modeLabel = mode ? mode.charAt(0).toUpperCase() + mode.slice(1) : 'General';
            const dateString = new Date().toISOString().split('T')[0];
            const filename = `SignalScout_${modeLabel}_${dateString}.csv`;
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);
            showToast('CSV downloaded', 'success');
        }

        function getMissionEmoji(mission) {
            for (const [key, emoji] of Object.entries(MISSION_EMOJIS)) { if (mission.includes(key)) return emoji; }
            return ''; 
        }

        function getMissionColor(mission) {
            if (!mission) return MISSION_COLORS['Default'];
            for (const [key, color] of Object.entries(MISSION_COLORS)) {
                if (mission.includes(key)) return color;
            }
            return MISSION_COLORS['Default'];
        }

        const getDomain = (url) => {
            try {
                return new URL(url).hostname.replace('www.', '').toUpperCase();
            } catch {
                return 'SOURCE';
            }
        };

        function formatSource(url) {
            try {
                const hostname = new URL(url).hostname.replace('www.', '');
                const name = hostname.split('.')[0];
                return name.length <= 3 ? name.toUpperCase() : name.charAt(0).toUpperCase() + name.slice(1);
            } catch { return 'Source'; }
        }

        function renderCard(data) {
            // 1. Theme Mapping (Solid Colors & Contrast Rules)
            const themes = {
                'A Healthy Life': {
                    bg: 'bg-nesta-pink',
                    text: 'text-nesta-navy',
                    border: 'border-nesta-pink',
                    badge: 'bg-white text-nesta-pink',
                    icon: 'text-nesta-navy',
                    link: 'text-nesta-navy hover:text-white',
                    innerBox: 'bg-white/90 text-nesta-navy'
                },
                'A Fairer Start': {
                    bg: 'bg-nesta-purple',
                    text: 'text-white',
                    border: 'border-nesta-purple',
                    badge: 'bg-white text-nesta-purple',
                    icon: 'text-white',
                    link: 'text-white/80 hover:text-white',
                    innerBox: 'bg-white/95 text-nesta-navy'
                },
                'A Sustainable Future': {
                    bg: 'bg-nesta-green',
                    text: 'text-white',
                    border: 'border-nesta-green',
                    badge: 'bg-white text-nesta-green',
                    icon: 'text-white',
                    link: 'text-white/80 hover:text-white',
                    innerBox: 'bg-white/95 text-nesta-navy'
                },
                'default': {
                    bg: 'bg-nesta-blue',
                    text: 'text-white',
                    border: 'border-nesta-blue',
                    badge: 'bg-white text-nesta-blue',
                    icon: 'text-white',
                    link: 'text-white/80 hover:text-white',
                    innerBox: 'bg-white/95 text-nesta-navy'
                }
            };

            // 2. Normalize Mission
            const normalize = (m) => {
                if (!m) return { key: 'default', label: '⚡ Mission Adjacent' };
                const lower = m.toLowerCase();
                if (lower.includes('health')) return { key: 'A Healthy Life', label: '❤️‍🩹 A Healthy Life' };
                if (lower.includes('fairer') || lower.includes('start')) return { key: 'A Fairer Start', label: '📚 A Fairer Start' };
                if (lower.includes('sustain') || lower.includes('green')) return { key: 'A Sustainable Future', label: '🌳 A Sustainable Future' };
                return { key: 'default', label: m.includes('Adjacent') ? m : `⚡ ${m}` };
            };

            const missionInfo = normalize(data.mission);
            const style = themes[missionInfo.key] || themes['default'];
            
            // 3. Fix Source Link (Must be absolute)
            let safeUrl = '';
            if (data.url && typeof data.url === 'string') {
                // FIX: Remove citations like [1], [2], quotes " ' and surrounding spaces
                let cleaned = data.url.replace(/\[\d+\]/g, '').replace(/["']/g, '').trim();
                
                // Auto-fix missing 'https://'
                if (!/^https?:\/\//i.test(cleaned) && cleaned.length > 0) {
                    cleaned = 'https://' + cleaned.replace(/^\/+/, '');
                }
            
                try {
                    // Validate it is a real URL structure
                    safeUrl = new URL(cleaned).toString();
                } catch (e) {
                    console.warn("Invalid URL found:", data.url);
                    safeUrl = '';
                }
            }

            const getDomain = (u) => {
                try { return new URL(u).hostname.replace('www.', '').toUpperCase(); } 
                catch { return "SOURCE"; }
            };
            const domainLabel = safeUrl ? getDomain(safeUrl) : "SOURCE";
            const getCountryDisplay = (c) => {
                    if (!c || c.toLowerCase() === 'global') return '🌍 Global';
                    // Basic mapping for common flags, fallback to Pin
                    const map = { 'uk': '🇬🇧', 'usa': '🇺🇸', 'us': '🇺🇸', 'eu': '🇪🇺', 'china': '🇨🇳' };
                    const flag = map[c.toLowerCase()] || '📍';
                    // Title Case: "united kingdom" -> "United Kingdom"
                    const name = c.toLowerCase().split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                    return `${flag} ${name}`;
                };
                const countryTag = getCountryDisplay(data.origin_country);

            const tooltips = {
                nov: "How new or surprising is this signal?",
                ev: "Strength of evidence backing this claim.",
                imp: "Potential scale of systemic impact."
            };

            // 4. Content Blocks
            const hasDeepDive = (data.analysis && data.analysis.length > 10);

            const analysisBlock = hasDeepDive
                ? `<div class="${style.innerBox} rounded-lg p-4 shadow-sm">
                     <h4 class="font-display font-bold text-nesta-navy/50 text-[10px] uppercase tracking-widest mb-2">The Shift</h4>
                     <div class="prose prose-sm max-w-none font-body leading-relaxed text-sm editable-analysis max-h-40 overflow-y-auto custom-scrollbar">
                        ${formatAnalysis(data.analysis)}
                     </div>
                   </div>`
                : `<div id="enrich-container-${data.id}" class="py-4 flex justify-center">
                     <button type="button" onclick="triggerEnrichment('${safeUrl}', '${data.id}')" 
                        class="px-4 py-2 bg-white rounded-full text-xs font-bold uppercase tracking-widest text-nesta-navy shadow-lg hover:scale-105 transition-transform">
                        🪄 Generate Deep Dive
                     </button>
                   </div>`;

            const implicationBlock = hasDeepDive
                ? `<div class="mt-4 border-l-2 border-white/40 pl-4">
                     <h4 class="${style.text} opacity-80 font-display font-bold text-xs uppercase tracking-widest mb-1">🚀 Why It Matters</h4>
                     <p class="${style.text} text-sm italic font-body leading-relaxed editable-implication">"${escapeHtml(data.implication)}"</p>
                   </div>`
                : ``;

            const titleMarkup = safeUrl
                ? `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer" class="hover:underline decoration-2 underline-offset-4">
                        ${escapeHtml(data.title)}
                    </a>`
                : `<span class="opacity-70 cursor-not-allowed">${escapeHtml(data.title)}</span>`;

            const sourceMarkup = safeUrl
                ? `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer" 
                       class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider ${style.link}">
                       <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                       ${domainLabel}
                    </a>`
                : `<span class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider ${style.text} opacity-60 cursor-not-allowed">
                       <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                       SOURCE
                    </span>`;

            // 5. Render Card (Solid Background)
            return `
            <div id="card-${data.id}" class="signal-card ${style.bg} rounded-xl shadow-lg border-0 p-6 flex flex-col gap-5 relative group transition-transform hover:-translate-y-1 hover:shadow-xl" 
                 data-mission="${missionInfo.label}" data-url="${safeUrl}">
                
                <div class="flex justify-between items-center">
                    <span class="px-3 py-1 text-[11px] font-bold uppercase tracking-wider rounded-md shadow-sm ${style.badge}">
                        ${missionInfo.label}
                    </span>
                    
                    <div class="flex items-center gap-2">
                         <button type="button" onclick="toggleEdit('${data.id}', this)" class="${style.text} opacity-60 hover:opacity-100 transition-opacity">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
                        </button>
                        <div class="absolute top-4 right-4 z-30 group/score">
                            <div class="bg-nesta-blue text-white font-bold rounded-full w-12 h-12 flex items-center justify-center shadow-md cursor-help transition-transform group-hover/score:scale-105 border-2 border-white">
                                ${data.score || '-'}
                            </div>
                            <div class="absolute right-0 top-full mt-2 w-64 bg-white p-4 rounded-xl shadow-2xl border border-gray-100 opacity-0 invisible group-hover/score:opacity-100 group-hover/score:visible transition-all duration-200 z-50 text-left pointer-events-none transform origin-top-right">
                                <div class="text-[10px] font-bold text-nesta-navy uppercase tracking-widest mb-3 border-b border-gray-100 pb-2">Score Breakdown</div>
                                <div class="grid grid-cols-3 gap-2 mb-3">
                                     <div class="bg-gray-50 rounded p-1.5 text-center">
                                        <div class="text-[9px] text-gray-500 uppercase mb-0.5">Nov</div>
                                        <div class="font-bold text-nesta-blue text-sm">${data.score_novelty || '-'}</div>
                                     </div>
                                     <div class="bg-gray-50 rounded p-1.5 text-center">
                                        <div class="text-[9px] text-gray-500 uppercase mb-0.5">Imp</div>
                                        <div class="font-bold text-nesta-blue text-sm">${data.score_impact || '-'}</div>
                                     </div>
                                     <div class="bg-gray-50 rounded p-1.5 text-center">
                                        <div class="text-[9px] text-gray-500 uppercase mb-0.5">Evi</div>
                                        <div class="font-bold text-nesta-blue text-sm">${data.score_evidence || '-'}</div>
                                     </div>
                                </div>
                                <div class="space-y-2 text-[10px] text-nesta-darkgrey leading-tight">
                                     ${tooltips.nov ? `<div><span class="font-bold text-nesta-blue">Novelty:</span> ${tooltips.nov}</div>` : ''}
                                     ${tooltips.imp ? `<div><span class="font-bold text-nesta-blue">Impact:</span> ${tooltips.imp}</div>` : ''}
                                     ${tooltips.ev ? `<div><span class="font-bold text-nesta-blue">Evidence:</span> ${tooltips.ev}</div>` : ''}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div>
                    <h3 class="font-display font-bold text-xl mb-3 leading-snug ${style.text}">
                        ${titleMarkup}
                    </h3>
                    <p class="${style.text} text-base leading-relaxed font-body editable-hook">
                        ${escapeHtml(data.hook)}
                    </p>
                </div>

                ${analysisBlock}

                ${implicationBlock}

                <div class="mt-auto pt-4 border-t border-white/20 flex flex-wrap justify-between items-center gap-4">
                    <div class="flex items-center gap-2">
                        ${sourceMarkup}
                        <span class="text-[10px] font-bold uppercase tracking-wider ${style.text} opacity-80">[${countryTag}]</span>
                    </div>

                    <div class="flex gap-2 items-center">
                        <span class="w-2 h-2 rounded-full bg-nesta-aqua" title="Novelty Scored"></span>
                        <span class="w-2 h-2 rounded-full bg-nesta-blue" title="Impact Scored"></span>
                        <span class="w-2 h-2 rounded-full bg-nesta-purple" title="Evidence Scored"></span>
                    </div>
                </div>
            </div>
            `;
        }

        function buildActionBar(cardData, cardId, cardElementId) {
            const actionBar = document.createElement('div');
            actionBar.className = "flex items-center justify-between gap-3 mt-auto pt-4 border-t border-black/10";
            actionBar.innerHTML = `
                <button id="reject-btn-${cardId}" class="px-3 py-1.5 rounded-full border border-black/20 bg-white/20 hover:bg-white hover:text-red-600 text-[10px] font-bold uppercase transition">👎 Reject</button>
                <button id="copy-shortlist-${cardId}" class="px-3 py-1.5 rounded-full border border-black/20 bg-white/20 hover:bg-white hover:text-nesta-navy text-[10px] font-bold uppercase transition">📋 Copy</button>
                <button id="keep-btn-${cardId}" class="px-3 py-1.5 rounded-full border border-black/20 bg-white/20 hover:bg-white hover:text-yellow-500 text-[10px] font-bold uppercase transition">⭐ Star</button>
            `;

            const rejectButton = actionBar.querySelector(`#reject-btn-${cardId}`);
            if (rejectButton) {
                rejectButton.addEventListener('click', () => rejectSignal(cardData.url, cardElementId));
            }

            const shortlistButton = actionBar.querySelector(`#copy-shortlist-${cardId}`);
            if (shortlistButton) {
                shortlistButton.addEventListener('click', () => shortlistSignal({ ...cardData, url: cardData.url, id: `copy-shortlist-${cardId}` }));
            }

            const keepButton = actionBar.querySelector(`#keep-btn-${cardId}`);
            if (keepButton) {
                keepButton.addEventListener('click', () => keepSignal(cardData.url, `keep-btn-${cardId}`));
            }

            return actionBar;
        }

        function attachCardListeners(cardElement, cardId) {
            const editButton = cardElement.querySelector('[data-action="toggle-edit"]');
            if (editButton) {
                editButton.addEventListener('click', () => toggleEdit(cardId, editButton));
            }

            const enrichButton = cardElement.querySelector('[data-action="enrich"]');
            if (enrichButton) {
                enrichButton.addEventListener('click', () => triggerEnrichment(enrichButton.dataset.url, cardId, enrichButton));
            }
        }

        function updateCardMarkup(cardId) {
            const cardData = AppState.cardDataById?.[cardId];
            if (!cardData) return;
            const existingCard = document.querySelector(`[data-card-id="${cardId}"]`);
            if (!existingCard) return;
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = renderCard(cardData).trim();
            const newCard = tempDiv.firstChild;
            const showActions = existingCard.dataset.showActions === 'true';
            if (showActions) {
                newCard.appendChild(buildActionBar(cardData, cardId, newCard.id));
            }
            newCard.dataset.cardId = cardId;
            newCard.dataset.showActions = existingCard.dataset.showActions;
            if (existingCard.dataset.index) {
                newCard.dataset.index = existingCard.dataset.index;
            }
            existingCard.replaceWith(newCard);
        }

        async function triggerEnrichment(url, cardId, buttonEl) {
            if (!url) return;
            const cardData = AppState.cardDataById?.[cardId];
            if (!cardData) return;
            if (buttonEl) {
                buttonEl.disabled = true;
                buttonEl.classList.add('opacity-60', 'cursor-wait');
                buttonEl.innerHTML = '<span>🪄 Generating...</span>';
            }
            try {
                const response = await fetch(`${API_BASE_URL}/api/enrich_signal`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });
                const result = await response.json();
                if (result.status === 'success') {
                    cardData.analysis = result.analysis;
                    cardData.implication = result.implication;
                    AppState.cardDataById[cardId] = cardData;
                    updateCardMarkup(cardId);
                } else {
                    showToast(result.message || 'Enrichment failed', 'error');
                    updateCardMarkup(cardId);
                }
            } catch (e) {
                showToast('Connection Failed', 'error');
                updateCardMarkup(cardId);
            }
        }

        async function toggleEdit(cardId, buttonEl) {
            const cardData = AppState.cardDataById?.[cardId];
            const card = document.getElementById(`card-${cardId}`);
            if (!card || !cardData) return;
            const isEditing = card.dataset.editing === 'true';
            const hookEl = card.querySelector('.editable-hook');
            const analysisEl = card.querySelector('.editable-analysis');
            const implicationEl = card.querySelector('.editable-implication');
            const editableElements = [hookEl, analysisEl, implicationEl].filter(Boolean);

            if (!isEditing) {
                card.dataset.editing = 'true';
                editableElements.forEach(el => {
                    el.contentEditable = 'true';
                    el.classList.add('ring-2', 'ring-nesta-yellow', 'rounded-md', 'p-2', 'bg-white');
                });
                if (buttonEl) {
                    buttonEl.classList.add('text-nesta-blue');
                    buttonEl.setAttribute('aria-label', 'Save edits');
                }
                return;
            }

            const hookValue = hookEl ? hookEl.innerText.trim() : cardData.hook || '';
            const analysisValue = analysisEl ? analysisEl.innerText.trim() : cardData.analysis || '';
            const implicationValue = implicationEl ? implicationEl.innerText.trim().replace(/^"+|"+$/g, '') : cardData.implication || '';

            try {
                const response = await fetch(`${API_BASE_URL}/api/update_signal`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        url: cardData.url,
                        hook: hookValue,
                        analysis: analysisValue,
                        implication: implicationValue
                    })
                });
                if (!response.ok) throw new Error();
                cardData.hook = hookValue;
                cardData.analysis = analysisValue;
                cardData.implication = implicationValue;
                AppState.cardDataById[cardId] = cardData;
                showToast('Saved changes', 'success');
            } catch (e) {
                showToast('Failed to save', 'error');
            }

            updateCardMarkup(cardId);
        }

        function getLensBadges(lensesStr, styleClass) {
            if (!lensesStr) return '';
            const style = styleClass || "bg-gray-50 text-nesta-darkgrey border-gray-200"; 
            const tags = lensesStr.split(',').map(t => t.trim());
            let html = '<div class="flex flex-wrap gap-2 mb-4">';
            tags.forEach(tag => {
                let emoji = '';
                for (const [key, icon] of Object.entries(LENS_EMOJIS)) {
                    if (tag.toLowerCase().includes(key.toLowerCase())) emoji = icon;
                }
                if (emoji) {
                    html += `<span class="px-2 py-1 border rounded text-[10px] font-bold ${style}" title="${tag}">${emoji} ${tag}</span>`;
                }
            });
            html += '</div>';
            return html;
        }

        // --- DATA MANAGEMENT ---
        async function ensureDatabaseLoaded() {
            if (AppState.currentSaved.length === 0) {
                try {
                    const res = await fetch(`${API_BASE_URL}/api/saved`);
                    if (!res.ok) throw new Error();
                    AppState.currentSaved = (await res.json()).reverse(); // Newest first
                    return true;
                } catch (e) {
                    console.error("DB Load Error", e);
                    return false;
                }
            }
            return true;
        }

        async function loadPreview() {
            const grid = document.getElementById('preview-grid');
            try {
                const loaded = await ensureDatabaseLoaded();
                if (!loaded) {
                    grid.innerHTML = `
                        <div class="col-span-3 text-center text-xs text-red-400 py-10 space-y-3">
                            <div>Database Offline</div>
                            <button type="button" class="btn-interactive px-4 py-2 text-xs font-bold bg-nesta-blue text-white rounded">Retry</button>
                        </div>
                    `;
                    const retryButton = grid.querySelector('button');
                    if (retryButton) {
                        retryButton.addEventListener('click', () => loadPreview());
                    }
                    return;
                }
                const data = AppState.currentSaved;
                if(!data || data.length === 0) { grid.innerHTML = '<div class="col-span-3 text-center py-12 text-gray-400">Database empty.</div>'; return; }
                
                const recent = data.slice(0, 3);
                
                grid.innerHTML = ''; 
                recent.forEach((sig, i) => {
                    const normalized = normalizeSignal(sig);
                    createSignalCard(normalized, i, false, 'preview-grid');
                });
            } catch(e) { grid.innerHTML = '<div class="col-span-3 text-center text-xs text-red-400 py-10">Database Offline</div>'; }
        }

        function normalizeSignal(sig) {
            return {
                title: sig.Title || sig.title, 
                score: sig.Score || sig.score, 
                hook: sig.Hook || sig.hook, 
                analysis: sig.Analysis || sig.analysis,
                implication: sig.Implication || sig.implication,
                final_url: sig.URL || sig.final_url || sig.url,
                mission: sig.Mission || sig.mission, 
                origin_country: sig.Origin_Country || sig.origin_country,
                lenses: sig.Lenses || sig.lenses, 
                score_novelty: sig.Score_Novelty || sig.score_novelty, 
                score_evidence: sig.Score_Evidence || sig.score_evidence, 
                score_impact: sig.Score_Impact || sig.Score_Evocativeness || sig.score_impact || sig.score_evocativeness,
                score_evocativeness: sig.score_evocativeness,
                shareable: sig.Shareable || sig.shareable, 
                feedback: sig.Feedback || sig.User_Comment || sig.feedback,
                _row: sig._row, 
                source_date: sig.Source_Date || sig.source_date
            };
        }

        function renderDatabase() {
            const list = document.getElementById('saved-list');
            if (!list || !AppState.currentSaved) return;
            list.innerHTML = '';
            if (AppState.currentSaved.length === 0) {
                list.innerHTML = '<div class="col-span-full text-center py-20 text-gray-400">Database is empty.</div>';
                return;
            }

            AppState.currentSaved.forEach((signal, index) => {
                // PREFIX IDs with 'saved-' to prevent collision with main scan
                const savedId = `saved-card-${index}`;
                const normalized = normalizeSignal(signal);
                const linkUrl = normalized.final_url || normalized.url;
                const cardData = { ...normalized, id: savedId, url: linkUrl };

                if (!AppState.cardDataById) {
                    AppState.cardDataById = {};
                }
                AppState.cardDataById[savedId] = cardData;

                // Render the card HTML using the shared renderCard function
                // But override the ID in the data object passed to it
                const cardHTML = renderCard(cardData);

                const wrapper = document.createElement('div');
                wrapper.innerHTML = cardHTML.trim();
                const cardEl = wrapper.firstChild;
                cardEl.dataset.cardId = savedId;
                cardEl.dataset.showActions = 'true';
                cardEl.dataset.index = String(index);

                // Re-attach listeners specifically for the Saved View
                cardEl.appendChild(buildActionBar(cardData, savedId, cardEl.id));

                list.appendChild(cardEl);
            });
        }

        // --- UNIFIED FILTER LOGIC ---
        async function switchFilter(type) {
            AppState.activeFilter = type;
            
            // UI Toggle
            document.querySelectorAll('.filter-view-btn').forEach(b => {
                b.classList.remove('active', 'bg-nesta-navy', 'text-white', 'border-nesta-navy');
                b.classList.add('text-gray-500', 'border-transparent');
            });
            const btn = document.getElementById(`filter-btn-${type}`);
            if(btn) {
                btn.classList.add('active', 'bg-nesta-navy', 'text-white', 'border-nesta-navy');
                btn.classList.remove('text-gray-500', 'border-transparent');
            }

            // Data Logic
            const listContainer = document.getElementById('result-container');
            
            if (type === 'scan') {
                if (AppState.lastScanResults.length === 0) {
                    AppState.currentSignals = [];
                    listContainer.innerHTML = `<div class="col-span-full py-16 text-center border-2 border-dashed border-gray-200 rounded-xl"><p class="text-nesta-darkgrey font-bold">No active scan results.</p><p class="text-xs text-gray-400 mt-1">Enter a topic above to initiate a scan.</p></div>`;
                    renderRadar(); // Clears radar
                    updateDownloadButton();
                    return;
                }
                AppState.currentSignals = AppState.lastScanResults;
            } else {
                await ensureDatabaseLoaded();
                if (AppState.currentSaved.length === 0) {
                    listContainer.innerHTML = `<div class="text-center py-10">Database offline or empty.</div>`;
                    return;
                }
                
                let filtered = [];
                if (type === 'recent') {
                    filtered = AppState.currentSaved.slice(0, 10);
                } else if (type === 'funding') {
                    const keywords = ['fund', 'invest', 'venture', 'capital', 'raise', 'grant', 'million', 'billion', 'round'];
                    filtered = AppState.currentSaved.filter(s => {
                        const txt = ((s.Title||'') + (s.Hook||'') + (s.User_Comment||'')).toLowerCase();
                        return keywords.some(k => txt.includes(k));
                    });
                } else if (type === 'tech') {
                    filtered = AppState.currentSaved.filter(s => {
                        const lenses = (s.Lenses || '').toLowerCase();
                        const hook = (s.Hook || '').toLowerCase();
                        return lenses.includes('tech') || hook.includes('ai') || hook.includes('quantum') || hook.includes('novel');
                    });
                }
                AppState.currentSignals = filtered.map(normalizeSignal);
            }
            
            // Re-render both views
            renderList(); 
            renderRadar();
        }

        function renderList() {
            const container = document.getElementById('result-container');
            container.innerHTML = '';
            AppState.currentSignals.forEach((sig, i) => createSignalCard(sig, i));
            updateDownloadButton();
        }

        function filterFeed() {
            const missionSelect = document.getElementById('missionFilter') || document.getElementById('mission-select');
            if (!missionSelect) {
                return;
            }
            const selectedValue = missionSelect.value || 'all';
            const mission = selectedValue.toLowerCase().includes('all') ? 'all' : selectedValue;
            const cards = document.querySelectorAll('.signal-card');

            cards.forEach(card => {
                const cardMission = card.dataset.mission || '';
                if (mission === 'all') {
                    card.classList.remove('hidden');
                } else if (mission === 'adjacent') {
                    card.classList.toggle('hidden', !cardMission.includes('Adjacent'));
                } else {
                    const normalizedSelectedMission = mission.replace(/^[^A-Za-z]+\\s*/, '').trim();
                    card.classList.toggle('hidden', cardMission !== normalizedSelectedMission);
                }
            });
        }

        function createEditableTextarea(value, field, ariaLabel) {
            const textarea = document.createElement('textarea');
            textarea.value = value;
            textarea.dataset.field = field;
            textarea.setAttribute('aria-label', ariaLabel);
            textarea.className = 'w-full border-2 border-nesta-black bg-white text-nesta-black text-sm p-3 font-body focus:outline-none focus:ring-4 focus:ring-nesta-yellow';
            return textarea;
        }

        

        function showToast(msg, type='success') {
            const el = document.getElementById('toast');
            document.getElementById('toast-msg').innerText = msg;
            const dot = el.querySelector('div');
            
            // Allow 'normal' type for neutral/blue notifications that aren't errors
            let colorClass, borderClass;
            switch (type) {
                case 'error':
                    colorClass = 'bg-nesta-red';
                    borderClass = 'border-nesta-red';
                    break;
                case 'success':
                    colorClass = 'bg-nesta-green';
                    borderClass = 'border-nesta-green';
                    break;
                default: // 'normal' and other types
                    colorClass = 'bg-nesta-aqua';
                    borderClass = 'border-nesta-aqua';
            }
            
            dot.className = `w-2 h-2 rounded-full ${colorClass}`;
            el.className = `fixed bottom-8 right-8 bg-nesta-navy text-white px-6 py-4 shadow-2xl transform transition-all duration-500 z-[120] font-bold text-sm flex items-center gap-4 rounded-lg border-l-4 ${borderClass}`;
            el.classList.remove('translate-y-24', 'opacity-0');
            setTimeout(() => el.classList.add('translate-y-24', 'opacity-0'), 3000);
        }

        function handleEnter(e) { if(e.key === 'Enter') generateSignal(false); }
        function getCheckedSources() { return Array.from(document.querySelectorAll('#source-bias-container input:checked')).map(cb => cb.value); }
        function getSelectedScanMode() {
            const selected = document.querySelector('input[name="scan_mode"]:checked');
            return selected ? selected.value : 'general';
        }
        function updateDownloadButton() {
            const button = document.getElementById('download-signals-btn');
            if (!button) return;
            if (AppState.lastScanResults.length > 0) {
                button.classList.remove('hidden');
            } else {
                button.classList.add('hidden');
            }
        }

        function switchView(view) {
            const list = document.getElementById('result-container');
            const radar = document.getElementById('radar-container');
            const network = document.getElementById('network-container');
            const btnList = document.getElementById('btn-list');
            const btnRadar = document.getElementById('btn-radar');
            const btnNetwork = document.getElementById('btn-network');
            
            if(view === 'list') {
                list.classList.remove('hidden');
                radar.classList.add('hidden');
                network.classList.add('hidden');
                btnList.className = "px-5 py-2 text-xs font-bold transition shadow-sm bg-nesta-navy text-white rounded-md";
                btnRadar.className = "px-5 py-2 text-xs font-bold transition text-nesta-darkgrey hover:text-nesta-navy rounded-md";
                btnNetwork.className = "px-5 py-2 text-xs font-bold transition text-nesta-darkgrey hover:text-nesta-navy rounded-md";
            } else if (view === 'radar') {
                list.classList.add('hidden');
                radar.classList.remove('hidden');
                network.classList.add('hidden');
                btnRadar.className = "px-5 py-2 text-xs font-bold transition shadow-sm bg-nesta-navy text-white rounded-md";
                btnList.className = "px-5 py-2 text-xs font-bold transition text-nesta-darkgrey hover:text-nesta-navy rounded-md";
                btnNetwork.className = "px-5 py-2 text-xs font-bold transition text-nesta-darkgrey hover:text-nesta-navy rounded-md";
                renderRadar();
            } else {
                list.classList.add('hidden');
                radar.classList.add('hidden');
                network.classList.remove('hidden');
                btnNetwork.className = "px-5 py-2 text-xs font-bold transition shadow-sm bg-nesta-navy text-white rounded-md";
                btnList.className = "px-5 py-2 text-xs font-bold transition text-nesta-darkgrey hover:text-nesta-navy rounded-md";
                btnRadar.className = "px-5 py-2 text-xs font-bold transition text-nesta-darkgrey hover:text-nesta-navy rounded-md";
                renderNetwork();
            }
        }

        function renderNetwork() {
            const container = document.getElementById('signalNetwork');
            if (!container) return;
            if (!AppState.currentSignals.length) {
                container.innerHTML = '<div class="text-center text-gray-400 font-bold py-10">No signals to visualise.</div>';
                return;
            }

            const nodes = new vis.DataSet(
                AppState.currentSignals.map((signal, index) => ({
                    id: index,
                    label: signal.title || `Signal ${index + 1}`,
                    title: signal.hook || '',
                }))
            );

            const edges = [];
            const sanitize = (text) =>
                (text || '')
                    .toLowerCase()
                    .replace(/[^a-z0-9\s]/g, ' ')
                    .split(/\s+/) 

            for (let i = 0; i < AppState.currentSignals.length; i++) {
                const signalA = AppState.currentSignals[i];
                const wordsA = new Set(sanitize(signalA.title));
                for (let j = i + 1; j < AppState.currentSignals.length; j++) {
                    const signalB = AppState.currentSignals[j];
                    const wordsB = sanitize(signalB.title);
                    const sharedWord = wordsB.find((word) => wordsA.has(word));
                    const shareMission = signalA.mission && signalB.mission && signalA.mission === signalB.mission;
                    if (shareMission || sharedWord) {
                        edges.push({ from: i, to: j });
                    }
                }
            }

            const data = { nodes, edges };
            const options = {
                nodes: {
                    shape: 'dot',
                    size: 14,
                    color: {
                        background: '#0F294A',
                        border: '#0F294A',
                        highlight: {
                            background: '#F6A4B7',
                            border: '#F6A4B7',
                        },
                    },
                    font: { color: '#0F294A', size: 12 },
                },
                edges: {
                    color: { color: '#D1D5DB' },
                    width: 1,
                    smooth: true,
                },
                interaction: {
                    hover: true,
                },
                physics: {
                    stabilization: true,
                },
            };

            if (AppState.networkChart) {
                AppState.networkChart.destroy();
            }
            AppState.networkChart = new vis.Network(container, data, options);
        }

        async function synthesizeTrend() {
            if (!AppState.currentSignals.length) {
                showToast('No signals to synthesise.', 'error');
                return;
            }
            try {
                const res = await fetch(`${API_BASE_URL}/api/synthesize`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ signals: AppState.currentSignals }),
                });
                if (!res.ok) throw new Error();
                const data = await res.json();
                AppState.currentSynth = data;

                const container = document.getElementById('result-container');
                if (!container) return;
                const existing = document.getElementById('synth-card');
                if (existing) existing.remove();

                const card = document.createElement('div');
                card.id = 'synth-card';
                card.className = 'bg-gradient-to-r from-nesta-purple to-nesta-blue text-white rounded-xl p-8 shadow-soft';
                card.innerHTML = `
                    <div class="text-xs uppercase tracking-widest text-white/70 mb-3">Meta-Analysis</div>
                    <h3 class="text-3xl font-bold brand-font mb-3">${escapeHtml(data.trend_name || 'Emerging Trend')}</h3>
                    <p class="text-sm leading-relaxed mb-4">${escapeHtml(data.analysis || '')}</p>
                    <div class="text-sm font-semibold">Implication: <span class="font-normal">${escapeHtml(data.implication || '')}</span></div>
                `;
                container.prepend(card);
            } catch (error) {
                showToast('Synthesis failed. Please retry.', 'error');
            }
        }

        function generateBriefing() {
            if (!AppState.currentSignals.length) {
                showToast('No signals to export.', 'error');
                return;
            }
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            const now = new Date();
            const dateLabel = now.toLocaleDateString('en-GB');
            const filenameDate = now.toISOString().split('T')[0];

            let y = 16;
            doc.setFontSize(14);
            doc.text('Nesta Signal Scout // Intelligence Briefing', 14, y);
            y += 8;
            doc.setFontSize(10);
            doc.text(`Date: ${dateLabel}`, 14, y);
            y += 10;

            if (AppState.currentSynth) {
                doc.setFontSize(12);
                doc.text('Executive Summary', 14, y);
                y += 6;
                doc.setFontSize(10);
                const summary = `${AppState.currentSynth.trend_name || ''} — ${AppState.currentSynth.analysis || ''} ${AppState.currentSynth.implication || ''}`.trim();
                const summaryLines = doc.splitTextToSize(summary, 180);
                doc.text(summaryLines, 14, y);
                y += summaryLines.length * 5 + 4;
            }

            doc.setFontSize(12);
            doc.text('Signals', 14, y);
            y += 6;
            doc.setFontSize(10);

            AppState.currentSignals.slice(0, 6).forEach((signal) => {
                const block = `${signal.title || 'Untitled'} (Score: ${signal.score || '-'})\n${signal.hook || ''}`;
                const lines = doc.splitTextToSize(block, 180);
                if (y + lines.length * 5 > 280) {
                    doc.addPage();
                    y = 16;
                }
                doc.text(lines, 14, y);
                y += lines.length * 5 + 6;
            });

            doc.save(`Nesta_Briefing_${filenameDate}.pdf`);
        }

        function setScanningState(isScanning) {
            const startBtn = document.getElementById('search-btn');
            const broadBtn = document.getElementById('broad-btn');
            const stopBtn = document.getElementById('stop-btn');

            if (isScanning) {
                startBtn.classList.add('hidden');
                broadBtn.classList.add('hidden');
                stopBtn.classList.remove('hidden');
            } else {
                stopBtn.classList.add('hidden');
                toggleButtonState();
            }
        }

        function toggleTerminal() {
            const terminal = document.getElementById('live-terminal');
            const indicator = document.getElementById('terminal-toggle-indicator');
            if (!terminal || !indicator) return;
            terminal.classList.toggle('hidden');
            indicator.textContent = terminal.classList.contains('hidden') ? '[+]' : '[-]';
        }

        function stopScan() {
            if (AppState.scanController) {
                AppState.scanController.abort();
                AppState.scanController = null;
                showToast('Scan Cancelled', 'error');
            }
        }

        async function generateSignal(isBroad) {
            if (AppState.isProcessing) return;
            const topic = document.getElementById('topic-input').value;
            const container = document.getElementById('result-container');
            const signalCount = parseInt(document.getElementById('signal-count').value) || 5;
            const requestTimeoutMs = 900000;
            
            if (!topic && !isBroad) return showToast("Please enter a topic", "error");

            AppState.isProcessing = true;
            setScanningState(true); 
            switchView('list');
            // Force filter to 'scan' mode
            switchFilter('scan'); 
            updateDownloadButton();
            startLiveTerminal();
            
            container.innerHTML = `
                <div class="col-span-full py-24 flex flex-col items-center justify-center space-y-8 animate-fade-in-up">
                    <div class="radar-loader w-16 h-16 border-4 border-t-nesta-blue"></div>
                    <div class="w-full max-w-md space-y-2">
                        <div class="flex justify-between items-end px-1">
                            <p id="loading-status-text" class="font-display text-xl text-nesta-navy transition-opacity duration-200">Initialising Scout Agent...</p>
                            <p id="loading-percent-text" class="font-bold text-nesta-blue text-xl">0%</p>
                        </div>
                        <div class="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                            <div id="loading-bar-inner" class="h-full bg-gradient-to-r from-nesta-blue to-nesta-aqua w-0 transition-all duration-100 ease-out"></div>
                        </div>
                        <p class="text-[10px] font-bold text-nesta-darkgrey uppercase tracking-widest text-center pt-2">AI Analysis in Progress</p>
                    </div>
                </div>`;
            
            startLoadingSimulation(signalCount);

            const missionSelectValue = document.getElementById('mission-select').value;

            const payload = {
                message: isBroad 
                    ? `Find ${signalCount} high-novelty novel signals related to ${missionSelectValue}. Context: ${topic}` 
                    : `Find ${signalCount} signals about ${topic} for ${missionSelectValue}`,
                time_filter: document.getElementById('time-filter').value,
                source_types: getCheckedSources(),
                tech_mode: document.getElementById('tech-mode').checked,
                mission: missionSelectValue,
                signal_count: signalCount,
                scan_mode: getSelectedScanMode()
            };

            AppState.scanController = new AbortController();
            const signal = AppState.scanController.signal;

            let timeoutId;
            try {
                // We reuse the robust check here too, in case user went idle
                const backendReady = await warmBackend();
                if (!backendReady) {
                    stopLoadingSimulation();
                    container.innerHTML = `<div class="p-8 bg-white border-l-4 border-nesta-red shadow-sm text-center"><p class="font-bold text-nesta-red">Backend Offline</p><p class="text-sm text-gray-500">Could not reach the scanning service. Trying again in a moment...</p></div>`;
                    showToast('Could not reach backend. Please retry.', 'error');
                    return;
                }

                timeoutId = setTimeout(() => {
                    if (AppState.scanController) {
                        AppState.scanController.abort();
                    }
                }, requestTimeoutMs);

                const res = await fetch(`${API_BASE_URL}/api/chat`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload),
                    signal: signal 
                });

                if(!res.ok) throw new Error();

                AppState.currentSignals = [];
                AppState.lastScanResults = [];

                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop();
                    
                    for (const line of lines) {
                        if (!line.trim()) continue;
                        try {
                            const msg = JSON.parse(line);
                            if (msg.type === 'progress') {
                                document.getElementById('loading-status-text').innerText = msg.message;
                            } else if (msg.type === 'signal') {
                                const norm = normalizeSignal(msg.data);
                                AppState.currentSignals.push(norm);
                                createSignalCard(norm, AppState.currentSignals.length - 1);
                                autosaveSignal(norm);
                                AppState.lastScanResults = AppState.currentSignals;
                                updateDownloadButton();
                            } else if (msg.type === 'error') {
                                showToast(msg.message, 'error');
                            }
                        } catch (e) { console.error('Stream parse error', e); }
                    }
                }
                stopLoadingSimulation();
                const loader = document.querySelector('.radar-loader');
                if (loader) loader.parentElement.remove();
                // Signals already streamed in; avoid clearing the container.
            } catch (error) {
                stopLoadingSimulation();
                if (error.name === 'AbortError') {
                    container.innerHTML = `<div class="p-10 text-center text-gray-400">Scan cancelled.</div>`;
                } else {
                    container.innerHTML = `<div class="p-8 bg-white border-l-4 border-nesta-red shadow-sm text-center"><p class="font-bold text-nesta-red">Connection Failed</p><p class="text-sm text-gray-500">Please check your internet or try again later.</p></div>`;
                }
            } finally {
                if (timeoutId) {
                    clearTimeout(timeoutId);
                }
                AppState.isProcessing = false;
                AppState.scanController = null;
                setScanningState(false);
                stopLiveTerminal();
            }
        }

        function createSignalCard(signal, index, showActions = true, containerId = 'result-container') {
            const container = document.getElementById(containerId);
            if (!container) return;

            const cardId = signal.id || `card-${index}`;
            const linkUrl = signal.final_url || signal.url;
            const cardData = { ...signal, id: cardId, url: linkUrl };
            signal.id = cardId;

            if (!AppState.cardDataById) {
                AppState.cardDataById = {};
            }
            AppState.cardDataById[cardId] = cardData;

            const cardHTML = renderCard(cardData);
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = cardHTML.trim();
            const cardElement = tempDiv.firstChild;
            cardElement.dataset.cardId = cardId;
            cardElement.dataset.showActions = showActions ? 'true' : 'false';
            cardElement.dataset.index = String(index);

            if (showActions) {
                cardElement.appendChild(buildActionBar(cardData, cardId, cardElement.id));
            }
            
            const existing = container.querySelector(`[data-card-id="${cardId}"]`);
            if (existing) {
                existing.replaceWith(cardElement);
            } else {
                container.appendChild(cardElement);
            }
        }

        async function updateSignalStatus(url, status) {
            if (!url) return;
            try {
                await fetch(`${API_BASE_URL}/api/update`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ url, user_status: status })
                });
            } catch (e) {
                console.error('Status update failed', e);
            }
        }

        async function autosaveSignal(signal) {
            const url = signal?.final_url || signal?.url;
            if (!url) return;
            const basePayload = {
                url,
                title: signal?.title,
                hook: signal?.hook ?? '',
                analysis: signal?.analysis ?? '',
                implication: signal?.implication ?? '',
                score: signal?.score,
                score_novelty: signal?.score_novelty,
                score_evidence: signal?.score_evidence,
                score_evocativeness: signal?.score_evocativeness,
                mission: signal?.mission,
                lenses: signal?.lenses,
                source_date: signal?.source_date
            };
            const requiredFields = new Set(['url', 'hook', 'analysis', 'implication']);
            const payload = Object.fromEntries(
                Object.entries(basePayload).filter(([key, value]) => requiredFields.has(key) || (value != null && value !== ''))
            );
            try {
                const res = await fetch(`${API_BASE_URL}/api/update_signal`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                if (!res.ok) {
                    console.error('Autosave failed', await res.text());
                }
            } catch (e) {
                console.error('Autosave failed', e);
            }
        }

        async function rejectSignal(url, cardId) {
            await updateSignalStatus(url, 'Rejected');
            const card = document.getElementById(cardId);
            if (card) {
                card.remove();
            }
            AppState.currentSignals = AppState.currentSignals.filter(signal => (signal.final_url || signal.url) !== url);
            AppState.lastScanResults = AppState.lastScanResults.filter(signal => (signal.final_url || signal.url) !== url);
            const normalizeUrl = (value) => {
                if (!value) return '';
                try {
                    return decodeURIComponent(String(value)).trim().toLowerCase();
                } catch (e) {
                    return String(value).trim().toLowerCase();
                }
            };
            const targetUrl = normalizeUrl(url);
            AppState.currentSaved = AppState.currentSaved.filter(signal => normalizeUrl(signal.URL || signal.url) !== targetUrl); // Ensure case-insensitive comparison for consistency.
            updateDownloadButton();
            showToast('Signal rejected', 'normal');
        }

        async function shortlistSignal(cardData) {
            await copyFormattedCard(cardData);
            await updateSignalStatus(cardData?.url, 'Shortlisted');
        }

        async function keepSignal(url, buttonId) {
            await updateSignalStatus(url, 'Saved');
            const button = document.getElementById(buttonId);
            if (button) {
                button.textContent = '⭐ Starred';
                button.classList.add('bg-nesta-sand');
            }
            showToast('Signal starred', 'success');
        }

        async function checkLinkHealth(url, indicatorId) {
            const indicator = document.getElementById(indicatorId);
            if (!indicator) return;
            indicator.className = 'w-2 h-2 rounded-full bg-nesta-sand';
            indicator.title = 'Checking link...';
            try {
                await fetch(url, { method: 'HEAD', mode: 'no-cors' });
                indicator.className = 'w-2 h-2 rounded-full bg-nesta-green';
                indicator.title = 'Server responded (link validity not checked)';
            } catch (e) {
                indicator.className = 'w-2 h-2 rounded-full bg-nesta-red';
                indicator.title = 'Server unreachable (link may be broken)';
            }
        }

        async function copyFormattedCard(signalData) {
            const missionEmojis = {
                'A Sustainable Future': '🌳',
                'A Fairer Start': '📚',
                'A Healthy Life': '❤️‍🩹',
                'Creative Industries': '🎨',
                'default': '🔮'
            };
            const emoji = missionEmojis[signalData?.mission] || missionEmojis['default'];
            const title = signalData?.title || 'Untitled Signal';
            const hook = signalData?.hook || 'No hook provided.';
            const url = signalData?.url || '';
            const analysis = signalData?.analysis;
            const implication = signalData?.implication;
            const scoreNovelty = signalData?.score_novelty ?? 'N/A';
            const scoreEvidence = signalData?.score_evidence ?? 'N/A';
            const scoreImpact = signalData?.score_impact ?? signalData?.score_evocativeness ?? 'N/A';

            let text = `${emoji} ${signalData?.mission || 'Signal Scout'}\n`;
            text += `*${title}*\n\n`;
            text += `🤖 *Signal*\n`;
            text += `${hook}\n\n`;
            if (analysis) {
                text += `🔍 *The Analysis*\n`;
                text += `${analysis}\n\n`;
            }
            if (implication) {
                text += `🚀 *Why it matters*\n`;
                text += `${implication}\n\n`;
            }
            text += `*Score:* Novelty: ${scoreNovelty}/10 | Evidence: ${scoreEvidence}/10 | Impact: ${scoreImpact}/10\n`;
            text += `${url}`;
            try {
                await navigator.clipboard.writeText(text);
                const btn = document.getElementById(signalData?.id || '');
                if (btn) {
                    const originalIcon = btn.textContent;
                    btn.textContent = '✅ Copied!';
                    setTimeout(() => {
                        btn.textContent = originalIcon;
                    }, 2000);
                }
                showToast('Copied!', 'success');
            } catch (e) {
                console.error('Failed to copy!', e);
                showToast('Clipboard unavailable', 'error');
            }
        }

        async function openSavedSignals() {
            document.getElementById('saved-modal').classList.remove('hidden');
            const list = document.getElementById('saved-list');
            list.innerHTML = '<div class="col-span-full py-24 text-center flex flex-col items-center"><div class="radar-loader mb-4 border-2 border-gray-200 border-t-nesta-blue w-10 h-10"></div><p class="font-bold text-nesta-navy">Retrieving Intelligence...</p></div>';
            
            try {
                const res = await fetch(`${API_BASE_URL}/api/saved`);
                const data = await res.json();
                list.innerHTML = '';
                // NEWEST FIRST for full database view as well
                AppState.currentSaved = data.reverse(); 
                renderDatabase();
            } catch(e) { list.innerHTML = '<div class="col-span-full text-center text-nesta-red py-10 font-bold">Failed to load database.</div>'; }
        }

        function closeSavedSignals() { document.getElementById('saved-modal').classList.add('hidden'); }

        function openUserGuide() { document.getElementById('user-guide-modal').classList.remove('hidden'); }
        function closeUserGuide() { document.getElementById('user-guide-modal').classList.add('hidden'); }

        async function updateSavedSignal(url, title, domIndex) {
            const shareVal = document.getElementById(`saved-shareable-${domIndex}`).value;
            const commentVal = document.getElementById(`saved-comment-${domIndex}`)?.value || '';
            const statusMap = { Yes: 'Shortlisted', Maybe: 'Saved', No: 'Rejected' };
            const userStatus = statusMap[shareVal] || 'Saved';
            try {
                const res = await fetch(`${API_BASE_URL}/api/update`, {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ url, title, shareable: shareVal, user_status: userStatus, user_comment: commentVal, feedback: commentVal })
                });
                if(res.ok) { showToast('Database updated'); AppState.currentSaved = []; loadPreview(); }
                else throw new Error();
            } catch(e) { showToast('Update failed', 'error'); }
        }

        function downloadCSV() {
            if(!AppState.currentSaved || AppState.currentSaved.length === 0) return showToast('No data to export', 'error');
            let csv = "Title,URL,Score,Mission,Hook,Date,Status,Notes\n";
            AppState.currentSaved.forEach(r => { csv += `"${r.Title}","${r.URL}",${r.Score},"${r.Mission}","${(r.Hook||"").replace(/"/g, '""')}",${r.Source_Date},${r.Shareable},"${r.User_Comment||""}"\n`; });
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = `Signal_Export_${new Date().toISOString().split('T')[0]}.csv`;
            a.click();
        }

        // --- INTERACTIVE RADAR ---
        function scrollToCard(index) {
            switchView('list'); 
            const card = document.querySelector(`[data-index="${index}"]`);
            if (card) {
                card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                card.classList.add('card-highlight');
                setTimeout(() => card.classList.remove('card-highlight'), 2000);
            }
        }

        function renderRadar() {
            const canvas = document.getElementById('signalRadar');
            if (AppState.radarChart) AppState.radarChart.destroy();

            // 1. Prepare Data
            const dataPoints = AppState.currentSignals.map((s, i) => ({
                x: s.score_novelty || Math.random() * 10,
                y: s.score_evidence || Math.random() * 10,
                r: (s.score / 6) + 5,
                title: s.title,
                mission: s.mission,
                hook: s.hook,
                index: i
            }));

            // 2. Define Quadrant Background Plugin
            const quadrantPlugin = {
                id: 'quadrants',
                beforeDraw(chart) {
                    const { ctx, chartArea: { left, top, right, bottom }, scales: { x, y } } = chart;
                    const midX = x.getPixelForValue(5);
                    const midY = y.getPixelForValue(5);

                    const drawZone = (x1, y1, x2, y2, color, label) => {
                        ctx.fillStyle = color;
                        ctx.fillRect(x1, y1, x2 - x1, y2 - y1);
                        ctx.fillStyle = 'rgba(15, 41, 74, 0.1)';
                        ctx.font = 'bold 12px "Zosia Display"';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        const labelX = x1 + (x2 - x1) / 2;
                        const labelY = y1 + (y2 - y1) / 2;
                        ctx.fillText(label, labelX, labelY);
                    };

                    drawZone(left, top, midX, midY, 'rgba(240, 240, 240, 0.3)', 'ESTABLISHED TRENDS');
                    drawZone(midX, top, right, midY, 'rgba(151, 217, 227, 0.1)', 'GOLDEN SIGNALS (Act Now)');
                    drawZone(left, midY, midX, bottom, 'rgba(235, 0, 59, 0.03)', 'EARLY NOISE');
                    drawZone(midX, midY, right, bottom, 'rgba(253, 182, 51, 0.1)', 'WILDCARDS (Watch)');

                    ctx.strokeStyle = '#0F294A';
                    ctx.lineWidth = 1;
                    ctx.setLineDash([5, 5]);
                    ctx.beginPath();
                    ctx.moveTo(midX, top); ctx.lineTo(midX, bottom);
                    ctx.moveTo(left, midY); ctx.lineTo(right, midY);
                    ctx.stroke();
                    ctx.setLineDash([]);
                }
            };

            // 3. Render Chart
            AppState.radarChart = new Chart(canvas, {
                type: 'bubble',
                data: {
                    datasets: [{
                        label: 'Signals',
                        data: dataPoints,
                        backgroundColor: dataPoints.map(p => getMissionColor(p.mission)),
                        borderColor: '#fff',
                        borderWidth: 2,
                        hoverBackgroundColor: '#0F294A',
                        hoverBorderColor: '#0F294A',
                        hoverRadius: 10
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    layout: { padding: 20 },
                    scales: {
                        x: {
                            type: 'linear',
                            min: 0, max: 10,
                            title: { display: true, text: 'NOVELTY (How new is it?)', color: '#0F294A', font: { weight: 'bold' } },
                            grid: { display: false }
                        },
                        y: {
                            type: 'linear',
                            min: 0, max: 10,
                            title: { display: true, text: 'EVIDENCE (How real is it?)', color: '#0F294A', font: { weight: 'bold' } },
                            grid: { display: false }
                        }
                    },
                    plugins: {
                        tooltip: {
                            backgroundColor: 'rgba(15, 41, 74, 0.95)',
                            titleFont: { family: 'Zosia Display', size: 14 },
                            bodyFont: { family: 'Averta', size: 12 },
                            padding: 12,
                            cornerRadius: 4,
                            callbacks: {
                                label: (ctx) => {
                                    const p = ctx.raw;
                                    return [p.title, `Novelty: ${p.x.toFixed(1)} | Evidence: ${p.y.toFixed(1)}`];
                                }
                            }
                        },
                        legend: { display: false }
                    },
                    onClick: (evt, activeElements) => {
                        if (activeElements.length > 0) {
                            const idx = activeElements[0].index;
                            const point = dataPoints[idx];
                            scrollToCard(point.index);
                        }
                    }
                },
                plugins: [quadrantPlugin]
            });
        }

        Object.assign(window, {
            openUserGuide,
            closeUserGuide,
            openSavedSignals,
            closeSavedSignals,
            downloadCSV,
            generateBriefing,
            handleEnter,
            toggleButtonState,
            generateFrictionQuery,
            initDashboard,
            switchView,
            filterFeed,
            generateSignal,
            stopScan,
            downloadSignalsAsCSV,
            toggleTerminal,
            synthesizeTrend,
            switchFilter,
            toggleEdit,
            triggerEnrichment,
            createSignalCard,
            renderDatabase,
        });
        console.log("System Status: Global functions attached successfully.");
