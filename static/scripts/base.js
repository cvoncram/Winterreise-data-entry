    document.addEventListener("change", function (event) {
        if (event.target.matches(".file-input-hidden")) {
            const input = event.target;
            const nameSpan = document.getElementById(input.id + "-name");
            if (nameSpan) {
                nameSpan.textContent = input.files[0]
                    ? input.files[0].name
                    : "No file chosen";
            }
        }
    });

document.addEventListener("click", function (event) {
const menus = document.querySelectorAll(".custom-select-options");
menus.forEach(menu => {
    const wrapper = menu.closest(".custom-select-wrapper");
    if (!wrapper.contains(event.target)) {
        menu.style.display = "none";
    }
});
});

function toggleSelect(id) {
const menu = document.getElementById(id);
document.querySelectorAll(".custom-select-options").forEach(m => {
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