// ===============================
//      Correct Beats JS
// ===============================

let CURRENT_TOKEN = null;

// -------------------------------
// CSV Preview Initialization
// -------------------------------
initCsvPreview({
    inputId: "upload_csv",
    previewContainerId: "csv-preview",
    previewEndpoint: "/correct/preview",
    onTokenReady: (token) => CURRENT_TOKEN = token
});

// -------------------------------
// Tool Panel Controller
// -------------------------------
document.addEventListener("DOMContentLoaded", () => {
    const panel = document.getElementById("tool-panel");
    const buttons = document.querySelectorAll("#tool-buttons button");
    let activeTool = null;

    function closePanel() {
        panel.innerHTML = "";
        panel.style.display = "none";
        activeTool = null;
    }

    function openPanel(templateId) {
        const tpl = document.getElementById(templateId);
        panel.innerHTML = tpl.innerHTML;
        panel.style.display = "block";

        // Restore anacrusis toggle handler
        const checkbox = panel.querySelector("#beats_has_ana");
        const anaPanel = panel.querySelector("#beats_ana_panel");
        if (checkbox && anaPanel) {
            checkbox.addEventListener("change", () => {
                anaPanel.classList.toggle("hidden", !checkbox.checked);
            });
        }
    }

    buttons.forEach(btn => {
        btn.addEventListener("click", () => {
            const tool = btn.dataset.tool;

            if (activeTool === tool) {
                closePanel();
                return;
            }

            activeTool = tool;

            if (tool === "rename") openPanel("tpl-rename-tool");
            if (tool === "beats") openPanel("tpl-beats-tool");
            if (tool === "tempo") openPanel("tpl-tempo-tool");
        });
    });
});

// -------------------------------
// Apply Actions (Rename / Beats / Tempo)
// -------------------------------
document.addEventListener("click", (e) => {
    // ----- Rename -----
    if (e.target.matches("#apply_rename")) {
        const oldName = document.getElementById("rename_old").value.trim();
        const newName = document.getElementById("rename_new").value.trim();
        const moveLeft = document.getElementById("rename_move_left").checked;

        applyFormAction(
            { token: CURRENT_TOKEN, old: oldName, new: newName, move_left: moveLeft ? "1" : "0" },
            "/correct/rename",
            "/correct/preview_temp_csv",
            "csv-preview",
            null,
            "/correct/download",
            "corrected.csv"
        );
    }

    // ----- Beats -----
    if (e.target.matches("#apply_beats")) {
        const bpm = document.querySelector("#beats_bpm-wrapper input").value;
        const hasAna = document.getElementById("beats_has_ana").checked;
        const anaVal = hasAna ? document.querySelector("#beats_ana-wrapper input").value : 0;

        applyFormAction(
            { token: CURRENT_TOKEN, bpm, has_anacrusis: hasAna ? "1" : "0", anacrusis: anaVal },
            "/correct/beats",
            "/correct/preview_temp_csv",
            "csv-preview",
            null,
            "/correct/download",
            "corrected.csv"

        );
    }

    // ----- Tempo -----
    if (e.target.matches("#apply_tempo")) {
        applyFormAction(
            { token: CURRENT_TOKEN },
            "/correct/tempo",
            "/correct/preview_temp_csv",
            "csv-preview",
            null,
            "/correct/download",
            "corrected.csv"
        );
    }
});
