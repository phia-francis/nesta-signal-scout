import {
    clusterSignals,
    fetchSavedSignals,
    triggerScan,
    updateSignalStatus,
    wakeServer,
} from "./api.js";
import { state } from "./state.js";
import { initialiseTriage } from "./triage.js";
import {
    appendConsoleLog,
    clearConsole,
    finishScan,
    renderClusterInsights,
    renderSignals,
    showToast,
    startScan,
} from "./ui.js";
import { renderNetworkGraph } from "./vis.js";

let triageController;

// --- Modal system ---

function toggleDatabaseModal(show) {
    // 'open' matches styles.css (.modal-content.open)
    document.getElementById("db-modal")?.classList.toggle("open", show);
    document.getElementById("db-overlay")?.classList.toggle("open", show);
    if (show) refreshDatabase();
}

function toggleHelpModal(show) {
    document.getElementById("help-modal")?.classList.toggle("open", show);
    document.getElementById("help-overlay")?.classList.toggle("open", show);
}

// --- Database ---

async function refreshDatabase() {
    try {
        const databaseGrid = document.getElementById("database-grid");
        const groupByValue = document.getElementById("database-group")?.value || "none";
        const groupBy = groupByValue === "none" ? null : groupByValue;

        if (databaseGrid && !databaseGrid.innerHTML.trim()) {
            databaseGrid.innerHTML = '<p class="text-slate-400 p-4">Loading vault...</p>';
        }

        state.databaseItems = await fetchSavedSignals();
        renderSignals(state.databaseItems, databaseGrid, "database", groupBy);
    } catch (error) {
        console.error("Failed to refresh database:", error);
        showToast("Could not load database.", "error");
    }
}

// --- Triage & scanning ---

function updateTriageBadge() {
    const count = document.getElementById("new-signal-count");
    const triageButton = document.getElementById("btn-triage");
    if (count) count.textContent = String(state.triageQueue.length);
    if (triageButton) triageButton.classList.toggle("hidden", state.triageQueue.length === 0);
}

async function runScan() {
    const mission = document.getElementById("mission-select")?.value || "A Sustainable Future";
    const topic = (document.getElementById("query-input")?.value || "").trim();
    const feed = document.getElementById("radar-feed");

    state.radarSignals = [];
    state.triageQueue = [];
    updateTriageBadge();
    if (feed) feed.innerHTML = "";
    clearConsole();
    startScan();

    try {
        const data = await triggerScan(topic, mission, state.currentMode);

        if (data?.signals) {
            state.radarSignals = data.signals;
            state.triageQueue = data.signals.slice();
            updateTriageBadge();

            if (feed) {
                feed.innerHTML = "";
                if (data.signals.length === 0) {
                    feed.innerHTML = `
                        <div class="flex flex-col items-center justify-center p-12 text-center bg-nesta-sand/10 rounded-lg border border-nesta-sand border-dashed">
                            <h3 class="text-xl font-bold text-nesta-navy mb-2">No Novel Trends Found</h3>
                            <p class="text-nesta-navy/70 max-w-md">The agent filtered out results that were too old, irrelevant, or lacked strong evidence.</p>
                        </div>`;
                } else {
                    if (data.cluster_insights) renderClusterInsights(data.cluster_insights, feed);
                    renderSignals(state.radarSignals, feed, topic);
                }
            }
        }

        showToast("Scan complete", "success");
    } catch (error) {
        console.error(error);
        showToast("Connection failed. Check backend.", "error");
    } finally {
        finishScan();
    }
}

// --- View & mode ---

function switchMode(mode) {
    state.currentMode = mode;
    document.querySelectorAll(".mode-toggle").forEach((button) => {
        button.classList.toggle("active", button.dataset.mode === mode);
    });

    const desc = document.getElementById("mode-description");
    if (desc) {
        const descriptions = {
            radar: "<strong>Mini Radar:</strong> Fast web &amp; social trends.",
            research: "<strong>Deep Research:</strong> AI-powered deep dive analysis.",
            governance: "<strong>Governance:</strong> Policy &amp; regulatory intelligence.",
        };
        desc.innerHTML = descriptions[mode] ?? "";
    }
}

function switchVisualMode(mode) {
    const networkContainer =
        document.getElementById("view-network-container") ??
        document.getElementById("cluster-map-wrapper");
    if (!networkContainer) return;

    if (mode === "network") {
        networkContainer.classList.remove("hidden");
        renderNetworkGraph(state.radarSignals);
    } else {
        networkContainer.classList.add("hidden");
    }

    document.getElementById("btn-view-grid")?.classList.toggle("bg-white", mode === "grid");
    document.getElementById("btn-view-network")?.classList.toggle("bg-white", mode === "network");
}

async function runAutoCluster() {
    if (!state.radarSignals.length) {
        showToast("No signals available to cluster yet.", "info");
        return;
    }
    showToast("Clustering in progress...", "info");
    const narratives = await clusterSignals(state.radarSignals);
    const drawer = document.getElementById('narrative-drawer');
    const container = document.getElementById('narrative-container');
    if (!drawer || !container) return;

    drawer.classList.remove('hidden');
    container.innerHTML = narratives
        .map(
            (narrative) =>
                `<article class="bg-white border border-slate-200 p-4"><h4 class="font-bold text-sm text-nesta-navy">${narrative.title}</h4><p class="text-xs text-slate-600 mt-2">${narrative.count} signals</p></article>`
        )
        .join('');
}

// --- Initialisation ---

document.addEventListener("DOMContentLoaded", () => {

    // Attach all listeners synchronously — nothing awaited here
    triageController = initialiseTriage({
        getQueue: () => state.triageQueue,
        onArchive: async (signal) => updateSignalStatus(signal.url, "Archived"),
        onKeep: async (signal) => updateSignalStatus(signal.url, "New"),
        onStar: async (signal) => updateSignalStatus(signal.url, "Starred"),
    });

    document.querySelectorAll(".mode-toggle").forEach((button) => {
        button.addEventListener("click", () => switchMode(button.dataset.mode));
    });

    document.getElementById("open-db-btn")?.addEventListener("click", () => toggleDatabaseModal(true));
    document.getElementById("close-db-btn")?.addEventListener("click", () => toggleDatabaseModal(false));
    document.getElementById("db-overlay")?.addEventListener("click", () => toggleDatabaseModal(false));
    document.getElementById("refresh-db-btn")?.addEventListener("click", refreshDatabase);

    document.getElementById("help-btn")?.addEventListener("click", () => toggleHelpModal(true));
    document.getElementById("close-help-btn")?.addEventListener("click", () => toggleHelpModal(false));
    document.getElementById("close-help-btn-top")?.addEventListener("click", () => toggleHelpModal(false));
    document.getElementById("help-overlay")?.addEventListener("click", () => toggleHelpModal(false));

    document.getElementById("scan-btn")?.addEventListener("click", runScan);
    document.getElementById("btn-view-grid")?.addEventListener("click", () => switchVisualMode("grid"));
    document.getElementById("btn-view-network")?.addEventListener("click", () => switchVisualMode("network"));
    document.getElementById("btn-generate-analysis")?.addEventListener("click", runAutoCluster);
    document.getElementById("btn-regroup-clusters")?.addEventListener("click", runAutoCluster);
    document.getElementById("btn-triage")?.addEventListener("click", () => triageController?.open());

    switchMode("radar");
    switchVisualMode("grid");
    updateTriageBadge();

    // Non-blocking background initialisation
    (async () => {
        try {
            await wakeServer();
            await refreshDatabase();
        } catch (err) {
            console.warn("Background initialisation warning:", err);
        }
    })();
});
