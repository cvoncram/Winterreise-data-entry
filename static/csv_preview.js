function initCsvPreview(config) {
    const input = document.getElementById(config.inputId);
    const previewContainer = document.getElementById(config.previewContainerId);

    input.addEventListener("change", async function (e) {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch(config.previewEndpoint, {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        previewContainer.innerHTML = data.html;

        if (config.onTokenReady) {
            config.onTokenReady(data.token);
        }
    });
}
