const socket = io();
const presets = window.FILAMENT_PRESETS;
const swatchColors = [
    "#212721", "#8a8d8f", "#d0cfca", "#ffffff", "#e6322b", "#f88192",
    "#cf4f80", "#ff7338", "#695fa2", "#3e55ab", "#23a3c7", "#3db24e",
    "#75cb5d", "#fddb27", "#7c4d3a", "#d4b996"
];

const elements = {
    form: document.getElementById("spoolForm"),
    type: document.getElementById("type"),
    color: document.getElementById("colorInput"),
    swatches: document.getElementById("colorSwatches"),
    readerSelect: document.getElementById("readerSelect"),
    readerDetail: document.getElementById("readerDetail"),
    refreshReaders: document.getElementById("refreshReaders"),
    themeToggle: document.getElementById("themeToggle"),
    themeColor: document.getElementById("themeColor"),
    connectionDot: document.getElementById("connectionDot"),
    connectionState: document.getElementById("connectionState"),
    deviceVisual: document.querySelector(".device-visual"),
    deviceVisualLabel: document.getElementById("deviceVisualLabel"),
    writeButton: document.getElementById("writeButton"),
    readButton: document.getElementById("readButton"),
    dumpButton: document.getElementById("dumpButton"),
    advancedToggle: document.getElementById("advancedToggle"),
    advancedFields: document.getElementById("advancedFields"),
    modal: document.getElementById("operationModal"),
    operationEyebrow: document.getElementById("operationEyebrow"),
    operationTitle: document.getElementById("operationTitle"),
    operationMessage: document.getElementById("operationMessage"),
    operationError: document.getElementById("operationError"),
    cancelButton: document.getElementById("cancelButton"),
    toast: document.getElementById("toast")
};

let readerSignature = "";
let activeOperation = null;
let operationCancelled = false;
let toastTimer = null;
const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");

function getSavedTheme() {
    try {
        return localStorage.getItem("spooltag-theme");
    } catch (_) {
        return null;
    }
}

function applyTheme(theme, persist = false) {
    const isDark = theme === "dark";
    document.documentElement.dataset.theme = isDark ? "dark" : "light";
    elements.themeToggle.setAttribute("aria-pressed", String(isDark));
    elements.themeToggle.title = isDark ? "Use light mode" : "Use dark mode";
    elements.themeToggle.setAttribute("aria-label", elements.themeToggle.title);
    elements.themeColor.content = isDark ? "#141a1d" : "#f4f6f7";
    if (persist) {
        try {
            localStorage.setItem("spooltag-theme", isDark ? "dark" : "light");
        } catch (_) {
            // The selected theme still applies for this session.
        }
    }
}

elements.themeToggle.addEventListener("click", () => {
    applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark", true);
});
systemTheme.addEventListener("change", (event) => {
    if (!getSavedTheme()) applyTheme(event.matches ? "dark" : "light");
});
applyTheme(document.documentElement.dataset.theme);

function showToast(message) {
    elements.toast.textContent = message;
    elements.toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { elements.toast.hidden = true; }, 3500);
}

function updateSwatchSelection() {
    const value = elements.color.value.toLowerCase();
    document.querySelectorAll(".swatch").forEach((swatch) => {
        swatch.classList.toggle("selected", swatch.dataset.color === value);
    });
}

swatchColors.forEach((color) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "swatch";
    button.dataset.color = color;
    button.style.backgroundColor = color;
    button.title = color;
    button.setAttribute("aria-label", `Use color ${color}`);
    button.addEventListener("click", () => {
        elements.color.value = color;
        updateSwatchSelection();
    });
    elements.swatches.appendChild(button);
});
elements.color.addEventListener("input", updateSwatchSelection);

function getNumber(id, defaultValue = 0) {
    const value = document.getElementById(id).value;
    return value === "" ? defaultValue : Number.parseInt(value, 10);
}

function getFilamentData() {
    return {
        type: elements.type.value,
        color: elements.color.value,
        range_a: {
            speed_min: getNumber("speedMinA"), speed_max: getNumber("speedMaxA"),
            nozzle_min: getNumber("nozzleMinA"), nozzle_max: getNumber("nozzleMaxA")
        },
        range_b: {
            speed_min: getNumber("speedMinB"), speed_max: getNumber("speedMaxB"),
            nozzle_min: getNumber("nozzleMinB"), nozzle_max: getNumber("nozzleMaxB")
        },
        range_c: {
            speed_min: getNumber("speedMinC"), speed_max: getNumber("speedMaxC"),
            nozzle_min: getNumber("nozzleMinC"), nozzle_max: getNumber("nozzleMaxC")
        },
        bed_min: getNumber("bedMin"),
        bed_max: getNumber("bedMax")
    };
}

function setValue(id, value) {
    document.getElementById(id).value = value === 0 || value == null ? "" : value;
}

function loadFilamentData(data) {
    elements.type.value = data.type || "PLA";
    if (data.color) elements.color.value = data.color.slice(0, 7);
    setValue("bedMin", data.bed_min);
    setValue("bedMax", data.bed_max);
    ["a", "b", "c"].forEach((rangeName) => {
        const range = data[`range_${rangeName}`] || {};
        const suffix = rangeName.toUpperCase();
        setValue(`speedMin${suffix}`, range.speed_min);
        setValue(`speedMax${suffix}`, range.speed_max);
        setValue(`nozzleMin${suffix}`, range.nozzle_min);
        setValue(`nozzleMax${suffix}`, range.nozzle_max);
    });
    updateSwatchSelection();
}

function validateRanges() {
    const pairs = [
        ["nozzleMinA", "nozzleMaxA", "Nozzle"],
        ["bedMin", "bedMax", "Bed"],
        ["speedMinA", "speedMaxA", "Speed range 1"],
        ["speedMinB", "speedMaxB", "Speed range 2"],
        ["speedMinC", "speedMaxC", "Speed range 3"],
        ["nozzleMinB", "nozzleMaxB", "Nozzle range 2"],
        ["nozzleMinC", "nozzleMaxC", "Nozzle range 3"]
    ];
    for (const [minimumId, maximumId, label] of pairs) {
        const minimum = getNumber(minimumId);
        const maximum = getNumber(maximumId);
        if (minimum && maximum && minimum > maximum) {
            showToast(`${label}: minimum cannot exceed maximum.`);
            document.getElementById(minimumId).focus();
            return false;
        }
    }
    return true;
}

elements.type.addEventListener("change", () => loadFilamentData(presets[elements.type.value]));
loadFilamentData(presets[Object.keys(presets)[0]]);

elements.advancedToggle.addEventListener("click", () => {
    const expanded = elements.advancedToggle.getAttribute("aria-expanded") === "true";
    elements.advancedToggle.setAttribute("aria-expanded", String(!expanded));
    elements.advancedFields.hidden = expanded;
});

function readerOptionLabel(reader) {
    if (reader.kind === "chameleon") return `${reader.name} · USB`;
    return reader.supported ? reader.name : `${reader.name} (untested)`;
}

function updateReaderState(state) {
    const signature = JSON.stringify({readers: state.readers, selected: state.selected_reader});
    if (signature !== readerSignature) {
        const fragment = document.createDocumentFragment();
        const automatic = document.createElement("option");
        automatic.value = "";
        automatic.textContent = "Automatic (recommended)";
        fragment.appendChild(automatic);
        state.readers.forEach((reader) => {
            const option = document.createElement("option");
            option.value = reader.id;
            option.textContent = readerOptionLabel(reader);
            fragment.appendChild(option);
        });
        elements.readerSelect.replaceChildren(fragment);
        elements.readerSelect.value = state.selected_reader || "";
        readerSignature = signature;
    }

    const connected = Boolean(state.reader_connected);
    elements.connectionDot.classList.toggle("connected", connected);
    elements.connectionState.textContent = connected ? "Reader connected" : "No reader";
    elements.deviceVisual.classList.toggle("online", connected);
    elements.deviceVisualLabel.textContent = connected ? "Ready for tag" : "Reader offline";
    elements.readerDetail.textContent = state.active_reader
        ? `Active: ${state.active_reader}`
        : state.readers.length ? "Selected reader is unavailable" : "No PC/SC readers detected";
    [elements.writeButton, elements.readButton, elements.dumpButton].forEach((button) => {
        button.disabled = !connected || Boolean(state.busy);
    });
}

elements.readerSelect.addEventListener("change", () => {
    elements.readerSelect.disabled = true;
    socket.emit("select_reader", {reader: elements.readerSelect.value || null});
});

elements.refreshReaders.addEventListener("click", () => {
    elements.refreshReaders.classList.add("spinning");
    socket.emit("ping");
    setTimeout(() => elements.refreshReaders.classList.remove("spinning"), 650);
});

socket.on("nfc_state", updateReaderState);
socket.on("reader_selected", (result) => {
    elements.readerSelect.disabled = false;
    updateReaderState(result.state);
    if (!result.success) showToast(result.message || "Could not select that reader.");
});

function showOperation(kind) {
    const labels = {
        write: ["Write tag", "Waiting for a writable tag"],
        read: ["Read tag", "Waiting for a filament tag"],
        dump: ["Export dump", "Waiting for a tag to inspect"]
    };
    activeOperation = kind;
    operationCancelled = false;
    elements.operationEyebrow.textContent = labels[kind][0];
    elements.operationTitle.textContent = labels[kind][1];
    elements.operationMessage.textContent = "Keep the tag on the selected reader until this window closes.";
    elements.operationError.hidden = true;
    elements.cancelButton.textContent = "Cancel";
    elements.modal.hidden = false;
}

function operationFailed(message, busy = false) {
    if (busy) {
        elements.modal.hidden = true;
        showToast("Another NFC operation is already running.");
        return;
    }
    elements.operationTitle.textContent = "Operation did not complete";
    elements.operationError.textContent = message;
    elements.operationError.hidden = false;
    elements.cancelButton.textContent = "Close";
}

elements.writeButton.addEventListener("click", () => {
    if (!elements.form.reportValidity() || !validateRanges()) return;
    showOperation("write");
    socket.emit("write_tag", getFilamentData());
});
elements.readButton.addEventListener("click", () => {
    showOperation("read");
    socket.emit("read_tag");
});
elements.dumpButton.addEventListener("click", () => {
    showOperation("dump");
    socket.emit("create_dump");
});
elements.cancelButton.addEventListener("click", () => {
    operationCancelled = true;
    socket.emit("cancel_nfc");
});

socket.on("read_done", (result) => {
    if (operationCancelled || activeOperation !== "read") return;
    if (!result.success) return operationFailed(result.message || "The tag could not be read. Remove it, wait a moment, and try again.", result.busy);
    loadFilamentData(result.data);
    elements.modal.hidden = true;
    showToast("Tag profile loaded.");
});

socket.on("write_done", (result) => {
    if (operationCancelled || activeOperation !== "write") return;
    if (!result.success) return operationFailed(result.message || "The tag could not be written. Check that it is an unlocked NTAG213 and try again.", result.busy);
    elements.modal.hidden = true;
    showToast("Tag written successfully.");
});

socket.on("dump_done", (result) => {
    if (operationCancelled || activeOperation !== "dump") return;
    if (!result.success) return operationFailed(result.message || "The raw tag data could not be read.", result.busy);
    const blob = new Blob([result.data], {type: "text/plain"});
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = result.filename;
    link.click();
    URL.revokeObjectURL(link.href);
    elements.modal.hidden = true;
    showToast("Tag dump exported.");
});

socket.on("canceled", () => {
    activeOperation = null;
    elements.modal.hidden = true;
});
socket.on("disconnect", () => updateReaderState({reader_connected: false, readers: [], selected_reader: null, active_reader: null, busy: false}));

setInterval(() => socket.emit("ping"), 1200);
socket.emit("ping");
updateSwatchSelection();
lucide.createIcons({attrs: {"stroke-width": 1.8}});
