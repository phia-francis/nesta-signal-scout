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
    radar: { label: "RUN MINI RADAR", color: "bg-nesta-blue" },
    research: { label: "RUN DEEP RESEARCH", color: "bg-nesta-purple" },
    governance: { label: "RUN GOVERNANCE RADAR", color: "bg-nesta-green" },
};

const MODE_COLORS = ["bg-nesta-blue", "bg-nesta-purple", "bg-nesta-green"];

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
    state.currentMode = mode;
    document.querySelectorAll(".mode-toggle").forEach((button) => {
        const isActive = button.dataset.mode === mode;
        button.classList.toggle("active", isActive);
        button.classList.toggle("bg-nesta-navy", isActive);
        button.classList.toggle("text-white", isActive);
        button.classList.toggle("bg-slate-100", !isActive);
        button.classList.toggle("text-slate-600", !isActive);
    });

    const desc = document.getElementById("mode-description");
    const scanBtn = document.getElementById("scan-btn");
    const feed = document.getElementById("radar-feed");
    const modeSettings = MODE_CONFIG[mode] ?? MODE_CONFIG.radar;

    if (scanBtn) {
        scanBtn.textContent = modeSettings.label;
        // Wipe all dynamic mode classes before applying the active mode color.
        scanBtn.classList.remove(...MODE_COLORS);
        scanBtn.classList.add(modeSettings.color);
    }

    state.radarSignals = [];
    if (feed) {
        feed.innerHTML = "";
    }

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

    ["btn-view-grid", "btn-view-network"].forEach((id) => {
        const button = document.getElementById(id);
        if (!button) return;
        // Wipe dynamic color utilities so active/inactive states never stack.
        button.classList.remove("bg-nesta-navy", "text-white", "bg-slate-200", "text-slate-800");
        const isActive = (id === "btn-view-grid" && mode === "grid") || (id === "btn-view-network" && mode === "network");
        button.classList.add(...(isActive ? ["bg-nesta-navy", "text-white"] : ["bg-slate-200", "text-slate-800"]));
    });
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
            const response = await fetch(`${state.apiBaseUrl}/trends`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    generated_at: new Date().toISOString(),
                    themes: narratives.themes.map((theme) => ({
                        ...theme,
                        analysis_text: theme.analysis_text || theme.description || "",
                    })),
                    full_analysis_text: narratives.full_analysis_text || narratives.analysis || "",
                }),
            });

            if (!response.ok) {
                throw new Error(`Trend save failed with ${response.status}`);
            }
        } catch (error) {
            console.warn("Failed to save trends:", error);
            showToast("Trend analysis generated, but saving trends failed.", "error");
        }
    }
}

async function fetchAndShowTrends() {
    const modal = document.getElementById("trends-modal");
    const content = document.getElementById("trends-modal-content");
    if (!modal || !content) return;

    content.innerHTML = '<p class="text-slate-500">Loading trends…</p>';
    modal.classList.remove("hidden");

    try {
        const response = await fetch(`${state.apiBaseUrl}/trends`);
        if (!response.ok) {
            throw new Error(`Failed to fetch trends: ${response.status}`);
        }

        const trends = await response.json();
        content.innerHTML = "";

        if (!Array.isArray(trends) || trends.length === 0) {
            content.innerHTML = '<p class="text-slate-500">No historical trends available yet.</p>';
            return;
        }

        trends.forEach((trend) => {
            const article = document.createElement("article");
            article.className = "border border-slate-200 rounded-lg p-4 bg-slate-50";

            const date = document.createElement("p");
            date.className = "text-xs font-bold uppercase tracking-wide text-slate-500";
            date.textContent = trend.date_generated || "Unknown date";

            const themeName = document.createElement("h3");
            themeName.className = "text-lg font-bold text-nesta-navy mt-1";
            themeName.textContent = trend.trend_theme || "Untitled Theme";

            const analysis = document.createElement("p");
            analysis.className = "text-sm text-slate-700 mt-2 whitespace-pre-wrap";
            analysis.textContent = trend.analysis_text || "No analysis text available.";

            article.append(date, themeName, analysis);
            content.appendChild(article);
        });
    } catch (error) {
        console.error(error);
        content.innerHTML = '<p class="text-red-600">Unable to load trends right now.</p>';
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
    document.getElementById("btn-show-trends")?.addEventListener("click", fetchAndShowTrends);
    document.getElementById("btn-close-trends")?.addEventListener("click", () => {
        document.getElementById("trends-modal")?.classList.add("hidden");
    });
    document.getElementById("trends-modal-overlay")?.addEventListener("click", () => {
        document.getElementById("trends-modal")?.classList.add("hidden");
    });
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
