// ================================
// File input name update
// ================================
document.addEventListener("change", (event) => {
    if (event.target.matches(".file-input-hidden")) {
        const input = event.target;
        const nameSpan = document.getElementById(input.id + "-name");
        const wrapper = input.closest(".file-wrapper");

        if (nameSpan) {
            nameSpan.textContent = input.files[0]?.name || "No file chosen";
        }

        if (wrapper) {
            if (input.files.length > 0) {
                wrapper.classList.add("file-selected");
            } else {
                wrapper.classList.remove("file-selected");
            }
        }
    }
});

// ================================
// Custom dropdown menus
// ================================
document.addEventListener("click", (event) => {
    document.querySelectorAll(".custom-select-options").forEach((menu) => {
        const wrapper = menu.closest(".custom-select-wrapper");
        if (!wrapper.contains(event.target)) {
            menu.style.display = "none";
        }
    });
});

function toggleSelect(id) {
    const menu = document.getElementById(id);
    document.querySelectorAll(".custom-select-options").forEach((m) => {
        if (m !== menu) m.style.display = "none";
    });
    menu.style.display = menu.style.display === "block" ? "none" : "block";
}

function chooseOption(wrapperId, value, text) {
    const wrapper = document.getElementById(wrapperId);
    wrapper.querySelector("input").value = value;
    wrapper.querySelector(".custom-select-display").textContent = text;
    wrapper.querySelector(".custom-select-options").style.display = "none";
}

// ================================
// Helper: Apply Form Action
// ================================
async function applyFormAction(
    formDataPairs,
    actionEndpoint,
    previewEndpoint,
    previewContainerId,
    tokenInputId = null,
    downloadPrefix = null,
    downloadFilename = null
) {
    const form = new FormData();
    for (const [key, value] of Object.entries(formDataPairs)) {
        form.append(key, value);
    }

    try {
        const r = await fetch(actionEndpoint, { method: "POST", body: form });
        const data = await r.json();

        if (!data.error) {

            if (tokenInputId) document.getElementById(tokenInputId).value = data.token;

            if (previewEndpoint && previewContainerId) {
                const previewForm = new FormData();
                previewForm.append("token", data.token);

                try {
                    const previewResp = await fetch(previewEndpoint, { method: "POST", body: previewForm });
                    const previewData = await previewResp.json();

                    if (previewData.measures && previewData.measures.length > 0) {
                        renderMEIPreview(previewData.measures);
                    } else {
                        const container = document.getElementById(previewContainerId);
                        container.innerHTML = "<p>No MEI preview available yet. Please process the SV file first.</p>";
                        container.style.display = "block";
                    }

                    if (previewData.warnings && previewData.warnings.length > 0) {
                        const warningsContainer = document.getElementById("warnings");
                        warningsContainer.innerHTML = "<ul>" + previewData.warnings.map(w => `<li>${w}</li>`).join("") + "</ul>";
                        warningsContainer.style.display = "block";
                    }
                } catch (err) {
                    console.error("Error fetching MEI preview:", err);
                }
            }

            if (downloadPrefix && downloadFilename) {
                document.getElementById("download-container").innerHTML =
                    `<a href="${downloadPrefix}/${data.token}" download="${downloadFilename}">
                        <button type="button">Download file</button>
                    </a>`;
            }
        }
    } catch (err) {
        console.error("applyFormAction error:", err);
        alert("An error occurred while processing the request.");
    }
}