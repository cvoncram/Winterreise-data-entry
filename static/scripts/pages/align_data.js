// ===============================
//          Align Data JS
// ===============================

let CURRENT_TOKEN = null;

// -------------------------------
// CSV Previews
// -------------------------------
initCsvPreview({
    inputId: "base-upload",
    previewContainerId: "base-preview",
    previewEndpoint: "/align/preview_csv",
    onTokenReady: token => document.getElementById("base-token").value = token
});

initCsvPreview({
    inputId: "sc-upload",
    previewContainerId: "sc-preview",
    previewEndpoint: "/align/preview_csv",
    onTokenReady: token => document.getElementById("sc-token").value = token,
    hasHeaderId: "sc-has-header"
});

initCsvPreview({
    inputId: "power-upload",
    previewContainerId: "power-preview",
    previewEndpoint: "/align/preview_csv",
    onTokenReady: token => document.getElementById("power-token").value = token,
    hasHeaderId: "power-has-header"
});

// -------------------------------
// Collapsible Tool Panels
// -------------------------------
document.addEventListener("DOMContentLoaded", () => {
    const panelButtons = document.querySelectorAll("#tool-buttons button");
    let activeTool = null;

    panelButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const toolId = btn.dataset.tool;
            const panel = document.getElementById(toolId);

            if (activeTool === toolId) {
                panel.classList.remove("visible");
                activeTool = null;
                return;
            }

            document.querySelectorAll(".tool-panel").forEach(p => p.classList.remove("visible"));
            panel.classList.add("visible");
            activeTool = toolId;
        });
    });
});

// -------------------------------
// Apply Functions
// -------------------------------
document.getElementById("apply_centroid").addEventListener("click", () => {
    const baseToken = document.getElementById("base-token").value;
    const scToken = document.getElementById("sc-token").value;
    if (!baseToken || !scToken) return alert("Please upload both CSVs");

    applyFormAction(
        { base_token: baseToken, sc_token: scToken },
        "/align/apply_spectral_centroid",
        "/align/preview_temp_csv",
        "base-preview",
        "base-token",
        "/align/download",
        "aligned.csv"
    );
});

document.getElementById("apply_powercurve").addEventListener("click", () => {
    const baseToken = document.getElementById("base-token").value;
    const powerToken = document.getElementById("power-token").value;
    if (!baseToken || !powerToken) return alert("Please upload both CSVs");

    applyFormAction(
        { base_token: baseToken, power_token: powerToken, mf_ref: document.getElementById("mf_ref").value },
        "/align/apply_powercurve",
        "/align/preview_temp_csv",
        "base-preview",
        "base-token",
        "/align/download",
        "aligned.csv"
    );
});
