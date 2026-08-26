// app.js - All browser actions for the login and drive pages.

// Keep the token name in one place so login and logout agree.
const token_key = "simpledrive_token";
const message_element = document.getElementById("message");
const drive_message_element = document.getElementById("drive-message");

// Show a message on whichever page is currently open.
function show_message(message, message_type) {
    const element = message_element || drive_message_element;
    if (element) {
        element.textContent = message;
        element.className = "message " + message_type;
    }
}

// Send one API request, adding the login token when it exists.
async function api_call(path, request_options = {}) {
    const headers = { ...request_options.headers };
    const token = localStorage.getItem(token_key);
    const is_form_data = request_options.body instanceof FormData;
    // JSON needs this header; FormData must not get it because fetch adds its boundary.
    if (!is_form_data) headers["Content-Type"] = "application/json";
    if (token) headers.Authorization = "Bearer " + token;
    const response = await fetch(path, { ...request_options, headers: headers });
    const response_data = await response.json();
    if (!response.ok) {
        if (response.status === 401 && document.getElementById("files-body")) {
            localStorage.removeItem(token_key);
            window.location.href = "index.html";
        }
        throw new Error(response_data.detail || "Something went wrong. Please try again.");
    }
    return response_data;
}

// Create an account from the sign-up form.
async function handle_signup(event) {
    event.preventDefault();
    const email = document.getElementById("signup-email").value;
    const password = document.getElementById("signup-password").value;
    try {
        const data = await api_call("/api/auth/signup", { method: "POST", body: JSON.stringify({ email: email, password: password }) });
        show_message(data.message + " Please log in now.", "success");
        document.getElementById("signup-form").reset();
    } catch (error) { show_message(error.message, "error"); }
}

// Log in and save the returned pass-slip in browser storage.
async function handle_login(event) {
    event.preventDefault();
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;
    try {
        const data = await api_call("/api/auth/login", { method: "POST", body: JSON.stringify({ email: email, password: password }) });
        localStorage.setItem(token_key, data.token);
        window.location.href = "drive.html";
    } catch (error) { show_message(error.message, "error"); }
}

// Turn raw bytes into a size a person can read quickly.
function format_size(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

// Turn the backend date into the browser's normal local date and time.
function format_date(date_text) { return new Date(date_text).toLocaleString(); }

// Load the user details and put the storage bar on screen.
async function load_account() {
    const data = await api_call("/api/auth/me");
    const limit = 200 * 1024 * 1024;
    document.getElementById("user-email").textContent = data.email;
    document.getElementById("storage-text").textContent = format_size(data.storage_used) + " of 200 MB";
    document.getElementById("storage-bar").style.width = Math.min(data.storage_used / limit * 100, 100) + "%";
}

// Escape a file name before placing it into HTML, keeping the page safe.
function escape_html(value) {
    return value.replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#039;" })[character]);
}

// Draw one table row for every file returned by the backend.
function render_files(files) {
    const body = document.getElementById("files-body");
    const empty_message = document.getElementById("empty-message");
    empty_message.textContent = "No files yet. Upload something na.";
    empty_message.hidden = files.length !== 0;
    document.getElementById("files-table").hidden = files.length === 0;
    body.innerHTML = "";
    for (const file of files) {
        const row = document.createElement("tr");
        row.innerHTML = `<td>${escape_html(file.name)}</td><td>${format_size(file.size)}</td>`
            + `<td>${format_date(file.created_at)}</td><td class="action-cell">`
            + `<button data-action="download" data-id="${file.id}">Download</button>`
            + `<button data-action="rename" data-id="${file.id}">Rename</button>`
            + `<button data-action="delete" data-id="${file.id}">Delete</button></td>`;
        body.appendChild(row);
    }
}

// Ask the backend for this user's files and draw them.
async function load_files() { render_files((await api_call("/api/files")).files); }

// Upload the selected file using multipart/form-data made by FormData.
async function handle_upload(event) {
    event.preventDefault();
    const input = document.getElementById("file-input");
    if (!input.files[0]) return;
    const button = document.getElementById("upload-button");
    button.disabled = true;
    show_message("Uploading...", "success");
    const form_data = new FormData();
    form_data.append("file", input.files[0]);
    try {
        await api_call("/api/files/upload", { method: "POST", body: form_data });
        show_message("File uploaded successfully.", "success");
        input.value = "";
        await Promise.all([load_account(), load_files()]);
    } catch (error) { show_message(error.message, "error"); }
    finally { button.disabled = false; }
}

// Download by opening the temporary five-minute link in a new tab.
async function download_file(file_id) {
    const data = await api_call("/api/files/" + file_id + "/download");
    window.open(data.download_url, "_blank");
}

// Ask for a new name and save it through the rename endpoint.
async function rename_file(file_id) {
    const new_name = window.prompt("Enter the new file name:");
    if (!new_name) return;
    await api_call("/api/files/" + file_id, { method: "PATCH", body: JSON.stringify({ name: new_name }) });
    await load_files();
}

// Confirm before deleting, because deletion removes the file permanently.
async function delete_file(file_id) {
    if (!window.confirm("Delete this file permanently?")) return;
    await api_call("/api/files/" + file_id, { method: "DELETE" });
    show_message("File deleted successfully.", "success");
    await Promise.all([load_account(), load_files()]);
}

// Route clicks from all file action buttons to the correct operation.
async function handle_file_action(event) {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    try {
        if (button.dataset.action === "download") await download_file(button.dataset.id);
        if (button.dataset.action === "rename") await rename_file(button.dataset.id);
        if (button.dataset.action === "delete") await delete_file(button.dataset.id);
    } catch (error) { show_message(error.message, "error"); }
}

// Start the login page only when its forms are present.
if (document.getElementById("signup-form")) {
    document.getElementById("signup-form").addEventListener("submit", handle_signup);
    document.getElementById("login-form").addEventListener("submit", handle_login);
}

// Start the drive page only when its file table is present.
if (document.getElementById("files-body")) {
    if (!localStorage.getItem(token_key)) window.location.href = "index.html";
    document.getElementById("upload-form").addEventListener("submit", handle_upload);
    document.getElementById("files-body").addEventListener("click", handle_file_action);
    document.getElementById("logout-button").addEventListener("click", async () => {
        try { await api_call("/api/auth/logout", { method: "POST" }); } catch (error) { /* clear token even if server is unavailable */ }
        localStorage.removeItem(token_key);
        window.location.href = "index.html";
    });
    Promise.all([load_account(), load_files()]).catch(error => show_message(error.message, "error"));
}
