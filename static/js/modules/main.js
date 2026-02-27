import {
    clusterSignals,
    fetchSavedSignals,
    triggerScan,
    updateSignalStatus,
    wakeServer,
} from "./api.js";
import { loadScan, shareCurrentScan, state } from "./state.js";
import { initialiseTriage } from "./triage.js";
import {
    clearConsole,
    finishScan,
    renderClusterInsights,
    renderSignals,
    showToast,
    startScan,
    openDetailPanel,
    closeDetailPanel,
    showEnhancedToast,
} from "./ui.js";
import { clusterAndRenderThemes, renderNetworkGraph, setupViewToggle } from "./vis.js";

let triageController;

const MODE_TITLES = {
    radar: "Mini Radar Results",
    research: "Deep Research Analysis",
    governance: "Governance & Policy Results",
};

const MODE_CONFIG = {
    radar: { label: "Run Mini Radar", buttonColor: "bg-nesta-blue" },
    research: { label: "Run Deep Research", buttonColor: "bg-nesta-purple" },
    governance: { label: "Run Governance Scan", buttonColor: "bg-nesta-green" },
};

function toggleDatabaseModal(show) {
    const modal = document.getElementById("db-modal");
    const overlay = document.getElementById("db-overlay");
    modal?.classList.toggle("open", show);
    modal?.classList.toggle("active", show);
    overlay?.classList.toggle("open", show);
    overlay?.classList.toggle("active", show);
    if (show) refreshDatabase();
}

function toggleHelpModal(show) {
    document.getElementById("help-modal")?.classList.toggle("open", show);
    document.getElementById("help-overlay")?.classList.toggle("open", show);
}

async function refreshDatabase() {
    const databaseGrid = document.getElementById("database-grid");
    const refreshBtn = document.getElementById("refresh-db-btn");
    const originalBtnText = refreshBtn?.textContent || "Refresh";

    try {
        const groupByValue = document.getElementById("database-group")?.value || "none";
        const groupBy = groupByValue === "none" ? null : groupByValue;

        if (refreshBtn) {
            refreshBtn.textContent = "Refreshing...";
            refreshBtn.setAttribute("disabled", "true");
            refreshBtn.classList.add("opacity-50", "cursor-not-allowed");
        }

        if (databaseGrid && !databaseGrid.innerHTML.trim()) {
            databaseGrid.innerHTML = '<p class="text-slate-400 p-4">Loading vault...</p>';
        }

        const latestSignals = await fetchSavedSignals();
        state.databaseItems = latestSignals;
        renderSignals(state.databaseItems, databaseGrid, "database", groupBy);
    } catch (error) {
        console.error("Failed to refresh database:", error);
        showToast("Could not load database.", "error");
    } finally {
        if (refreshBtn) {
            refreshBtn.textContent = originalBtnText;
            refreshBtn.removeAttribute("disabled");
            refreshBtn.classList.remove("opacity-50", "cursor-not-allowed");
        }
    }
}


function setupDatabaseAutoSync() {
    const dbModal = document.getElementById("db-modal");
    if (!dbModal || typeof MutationObserver === "undefined") return;

    let wasVisible = dbModal.classList.contains("open") || dbModal.classList.contains("active");
    const observer = new MutationObserver(() => {
        const isVisible = dbModal.classList.contains("open") || dbModal.classList.contains("active");
        if (!wasVisible && isVisible) {
            refreshDatabase();
        }
        wasVisible = isVisible;
    });

    observer.observe(dbModal, { attributes: true, attributeFilter: ["class"] });
}

function updateTriageBadge() {
    const count = document.getElementById("new-signal-count");
    const triageButton = document.getElementById("btn-triage");
    if (count) count.textContent = String(state.triageQueue.length);
    if (triageButton) triageButton.classList.toggle("hidden", state.triageQueue.length === 0);
}

function ensureClusterMapShell() {
    const feed = document.getElementById("radar-feed");
    if (!feed) return;

    const toggles = document.getElementById("view-toggles");
    const networkContainer = document.getElementById("view-network-container");
    if (toggles) toggles.classList.remove("hidden");
    if (networkContainer) networkContainer.classList.add("hidden");
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
            state.globalSignalsArray = data.signals;
            state.triageQueue = data.signals.slice();
            updateTriageBadge();

            if (feed) {
                feed.innerHTML = `<h2 class="font-display text-2xl font-bold text-nesta-navy mb-6 border-b border-nesta-sand pb-2">${MODE_TITLES[state.currentMode] ?? "Scan Results"}</h2>`;

                if (data.signals.length === 0) {
                    feed.innerHTML += `
                        <div class="flex flex-col items-center justify-center p-12 text-center bg-nesta-sand/10 rounded-lg border border-nesta-sand border-dashed">
                            <h3 class="text-xl font-bold text-nesta-navy mb-2">No Novel Trends Found</h3>
                            <p class="text-nesta-navy/70 max-w-md">The agent filtered out results that were too old, irrelevant, or lacked strong evidence.</p>
                        </div>`;
                } else {
                    ensureClusterMapShell();
                    const resultsContainer = document.createElement("div");
                    feed.appendChild(resultsContainer);
                    renderSignals(data.signals, resultsContainer, topic);
                    if (data.cluster_insights) renderClusterInsights(data.cluster_insights, resultsContainer);
                }
            }
        }

        showEnhancedToast("Scan complete", "success");
    } catch (error) {
        console.error(error);
        showToast("Connection failed. Check backend.", "error");
    } finally {
        finishScan();
    }
}

function switchMode(mode) {
    const selectedMode = MODE_CONFIG[mode] ? mode : "radar";
    const selectedConfig = MODE_CONFIG[selectedMode];
    state.currentMode = selectedMode;

    document.querySelectorAll(".mode-toggle").forEach((button) => {
        const isActive = button.dataset.mode === selectedMode;
        button.classList.toggle("active", isActive);

        // Remove all dynamic mode colours before applying the active state.
        button.classList.remove("bg-nesta-blue", "bg-nesta-purple", "bg-nesta-green", "bg-nesta-navy");
        if (isActive) {
            button.classList.add(selectedConfig.buttonColor, "text-white");
            button.classList.remove("bg-slate-100", "text-slate-600");
        } else {
            button.classList.add("bg-slate-100", "text-slate-600");
            button.classList.remove("text-white");
        }
    });

    const scanButton = document.getElementById("scan-btn");
    if (scanButton) {
        // Keep scan CTA aligned with active mode and ensure colour classes never stack.
        scanButton.classList.remove("bg-nesta-blue", "bg-nesta-purple", "bg-nesta-green");
        scanButton.classList.add(selectedConfig.buttonColor);
        scanButton.textContent = selectedConfig.label;
    }

    const feed = document.getElementById("radar-feed");
    if (feed) feed.innerHTML = "";
    state.radarSignals = [];

    const desc = document.getElementById("mode-description");
    if (desc) {
        const descriptions = {
            radar: "<strong>Mini Radar:</strong> Fast web &amp; social trends.",
            research: "<strong>Deep Research:</strong> AI-powered deep dive analysis.",
            governance: "<strong>Governance:</strong> Policy &amp; regulatory intelligence.",
        };
        desc.innerHTML = descriptions[selectedMode] ?? "";
    }
}

function switchVisualMode(mode) {
    const toggles = document.getElementById("view-toggles");
    const networkContainer = document.getElementById("view-network-container") ?? document.getElementById("cluster-map-wrapper");
    if (!networkContainer) return;

    if (toggles) toggles.classList.remove("hidden");

    if (mode === "network") {
        networkContainer.classList.remove("hidden");
        renderNetworkGraph(state.radarSignals);
    } else {
        networkContainer.classList.add("hidden");
    }

    const gridButton = document.getElementById("btn-view-grid");
    const networkButton = document.getElementById("btn-view-network");
    const applyViewButtonState = (button, isActive) => {
        if (!button) return;
        button.classList.remove("bg-nesta-navy", "text-white", "bg-slate-200", "text-slate-800", "bg-white");
        if (isActive) {
            button.classList.add("bg-nesta-navy", "text-white");
        } else {
            button.classList.add("bg-slate-200", "text-slate-800");
        }
    };

    applyViewButtonState(gridButton, mode === "grid");
    applyViewButtonState(networkButton, mode === "network");
}

async function runAutoCluster() {
    if (!state.radarSignals.length) {
        showToast("No signals available to cluster yet.", "info");
        return;
    }
    showToast("Clustering in progress...", "info");
    const narratives = await clusterSignals(state.radarSignals);
    const drawer = document.getElementById("narrative-drawer");
    const container = document.getElementById("narrative-container");
    if (!drawer || !container) return;

    drawer.classList.remove("hidden");
    container.innerHTML = "";
    if (narratives.themes) {
        narratives.themes.forEach((narrative) => {
            const article = document.createElement("article");
            article.className = "bg-white border border-slate-200 p-4";
            const h4 = document.createElement("h4");
            h4.className = "font-bold text-sm text-nesta-navy";
            h4.textContent = narrative.name || "Untitled Theme";
            const paragraph = document.createElement("p");
            paragraph.className = "text-xs text-slate-600 mt-2";
            paragraph.textContent = `${narrative.count || 0} signals`;
            article.append(h4, paragraph);
            container.appendChild(article);
        });

        try {
            const trendResponse = await fetch(`${state.apiBaseUrl}/api/trends`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ themes: narratives.themes }),
            });
            if (!trendResponse.ok) {
                throw new Error(`Failed to persist trends: HTTP ${trendResponse.status}`);
            }
        } catch (error) {
            console.error("Trend persistence failed:", error);
            showToast("Analysis generated, but trends could not be saved.", "error");
        }
    }
}

document.addEventListener("DOMContentLoaded", () => {
    setupViewToggle();
    setupDatabaseAutoSync();
    window.refreshDatabase = refreshDatabase;

    document.getElementById("close-detail-panel")?.addEventListener("click", () => closeDetailPanel());
    document.getElementById("detail-overlay")?.addEventListener("click", () => closeDetailPanel());

    document.getElementById("share-scan-btn")?.addEventListener("click", async () => {
        await shareCurrentScan();
    });

    document.getElementById("cluster-themes-btn")?.addEventListener("click", async () => {
        await clusterAndRenderThemes(state.globalSignalsArray.length ? state.globalSignalsArray : state.radarSignals);
    });

    const params = new URLSearchParams(window.location.search);
    const scanId = params.get("scan");
    if (scanId) loadScan(scanId);

    const handleTriage = async (signal, status) => {
        await updateSignalStatus(signal.url, status);
        state.triageQueue = state.triageQueue.filter((s) => s.url !== signal.url);
        updateTriageBadge();
    };

    triageController = initialiseTriage({
        getQueue: () => state.triageQueue,
        onArchive: async (signal) => handleTriage(signal, "Archived"),
        onKeep: async (signal) => handleTriage(signal, "Active"),
        onStar: async (signal) => handleTriage(signal, "Starred"),
    });

    document.getElementById("start-tour-btn")?.addEventListener("click", (e) => {
        e.stopPropagation();
        import("./guide.js").then((module) => module.startTour());
    });

    document.querySelectorAll(".mode-toggle").forEach((button) => {
        button.addEventListener("click", () => switchMode(button.dataset.mode));
    });

    document.getElementById("open-db-btn")?.addEventListener("click", () => toggleDatabaseModal(true));
    document.getElementById("close-db-btn")?.addEventListener("click", () => toggleDatabaseModal(false));
    document.getElementById("db-overlay")?.addEventListener("click", () => toggleDatabaseModal(false));
    document.getElementById("refresh-db-btn")?.addEventListener("click", async () => {
        await refreshDatabase();
    });
    document.getElementById("database-group")?.addEventListener("change", refreshDatabase);

    document.getElementById("help-btn")?.addEventListener("click", () => toggleHelpModal(true));
    document.getElementById("close-help-btn")?.addEventListener("click", () => toggleHelpModal(false));
    document.getElementById("close-help-btn-top")?.addEventListener("click", () => toggleHelpModal(false));
    document.getElementById("help-overlay")?.addEventListener("click", () => toggleHelpModal(false));

    document.getElementById("scan-btn")?.addEventListener("click", runScan);
    document.getElementById("radar-feed")?.addEventListener("click", (event) => {
        const card = event.target.closest(".signal-card");
        if (!card || event.target.closest("a") || event.target.closest("button")) return;
        const url = card.dataset.url || "";
        const fullSignal = (state.radarSignals ?? state.globalSignalsArray ?? []).find((s) => (s.url ?? s.URL) === url);
        if (fullSignal) openDetailPanel(fullSignal);
    });
    document.getElementById("btn-view-grid")?.addEventListener("click", () => switchVisualMode("grid"));
    document.getElementById("btn-view-network")?.addEventListener("click", () => switchVisualMode("network"));
    document.getElementById("btn-generate-analysis")?.addEventListener("click", runAutoCluster);
    document.getElementById("btn-regroup-clusters")?.addEventListener("click", runAutoCluster);
    document.getElementById("btn-triage")?.addEventListener("click", () => triageController?.open());

    switchMode("radar");
    switchVisualMode("grid");
    updateTriageBadge();

    (async () => {
        try {
            await wakeServer();
            await refreshDatabase();
        } catch (err) {
            console.warn("Background initialisation warning:", err);
        }
    })();
});
