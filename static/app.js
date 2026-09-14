const number = (value) => {
  const parsed = Number(String(value || "0").replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
};
const chf = (value) => `${value.toFixed(2)} CHF`;
const PROFILE_KEY = "meyrinCTT.trainerProfiles.v1";

const profileSelect = document.getElementById("trainer-profile");
const profileStatus = document.getElementById("profile-status");
const deleteProfileButton = document.getElementById("delete-profile");

function loadProfiles() {
  try {
    const value = JSON.parse(localStorage.getItem(PROFILE_KEY) || "[]");
    return Array.isArray(value) ? value : [];
  } catch (_) {
    profileStatus.textContent = "Impossible de lire les profils enregistrés dans ce navigateur.";
    return [];
  }
}

function storeProfiles(profiles) {
  try {
    localStorage.setItem(PROFILE_KEY, JSON.stringify(profiles));
    return true;
  } catch (_) {
    profileStatus.textContent = "Le navigateur n'autorise pas l'enregistrement local.";
    return false;
  }
}

let profiles = loadProfiles();

function renderProfiles(selectedId = "") {
  profileSelect.replaceChildren(new Option("Nouvel entraîneur", ""));
  [...profiles]
    .sort((a, b) => a.name.localeCompare(b.name, "fr"))
    .forEach((profile) => profileSelect.add(new Option(profile.name, profile.id)));
  profileSelect.value = selectedId;
  deleteProfileButton.disabled = !selectedId;
}

function activeDocumentType() {
  return document.getElementById("invoice").classList.contains("active") ? "invoice" : "salary";
}

function currentProfile(existing = {}) {
  const invoiceActive = activeDocumentType() === "invoice";
  const sharedName = invoiceActive ? invoiceForm.invoice_trainer_name.value : salaryForm.trainer_name.value;
  const sharedAddress = invoiceActive ? invoiceForm.invoice_trainer_address.value : salaryForm.trainer_address.value;
  return {
    ...existing,
    name: sharedName.trim(),
    address: sharedAddress.trim(),
    avsNumber: salaryForm.avs_number.value.trim(),
    birthDate: salaryForm.birth_date.value,
    role: salaryForm.role.value.trim(),
    iban: invoiceForm.iban.value.trim(),
  };
}

function applyProfile(profile) {
  salaryForm.trainer_name.value = profile.name || "";
  salaryForm.trainer_address.value = profile.address || "";
  salaryForm.avs_number.value = profile.avsNumber || "";
  salaryForm.birth_date.value = profile.birthDate || "";
  salaryForm.role.value = profile.role || "Moniteur de tennis de table";
  invoiceForm.invoice_trainer_name.value = profile.name || "";
  invoiceForm.invoice_trainer_address.value = profile.address || "";
  invoiceForm.iban.value = profile.iban || "";
}

function clearProfileFields() {
  applyProfile({ role: "Moniteur de tennis de table" });
  profileSelect.value = "";
  deleteProfileButton.disabled = true;
  profileStatus.textContent = "Nouveau profil prêt à être saisi.";
}

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab, .panel").forEach((node) => node.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.tab).classList.add("active");
  });
});

const salaryForm = document.querySelector('[data-calculator="salary"]');
function updateSalary() {
  const gross = number(salaryForm.hours.value) * number(salaryForm.hourly_rate.value)
    + number(salaryForm.days.value) * number(salaryForm.daily_rate.value)
    + number(salaryForm.other_amount.value);
  const rates = ["avs_rate", "unemployment_rate", "accident_rate", "lpp_rate", "withholding_rate", "extra_deduction_rate"];
  const deductions = rates.reduce((total, name) => total + Math.round(gross * number(salaryForm[name].value) / 100), 0);
  salaryForm.querySelector('[data-total="gross"]').textContent = chf(gross);
  salaryForm.querySelector('[data-total="deductions"]').textContent = chf(deductions);
  salaryForm.querySelector('[data-total="net"]').textContent = chf(gross - deductions);
}
salaryForm.addEventListener("input", updateSalary);

const invoiceForm = document.querySelector('[data-calculator="invoice"]');
function updateInvoice() {
  let subtotal = 0;
  invoiceForm.querySelectorAll(".invoice-line").forEach((line) => {
    subtotal += number(line.querySelector('[name="item_quantity[]"]').value) * number(line.querySelector('[name="item_rate[]"]').value);
  });
  const vat = subtotal * number(invoiceForm.vat_rate.value) / 100;
  invoiceForm.querySelector('[data-total="subtotal"]').textContent = chf(subtotal);
  invoiceForm.querySelector('[data-total="vat"]').textContent = chf(vat);
  invoiceForm.querySelector('[data-total="invoice-total"]').textContent = chf(subtotal + vat);
}
invoiceForm.addEventListener("input", updateInvoice);

profileSelect.addEventListener("change", () => {
  const profile = profiles.find((item) => item.id === profileSelect.value);
  if (!profile) {
    clearProfileFields();
    return;
  }
  applyProfile(profile);
  deleteProfileButton.disabled = false;
  profileStatus.textContent = `Profil « ${profile.name} » chargé.`;
});

document.getElementById("new-profile").addEventListener("click", clearProfileFields);

document.getElementById("save-profile").addEventListener("click", () => {
  const selected = profiles.find((item) => item.id === profileSelect.value);
  const profile = currentProfile(selected || {});
  if (!profile.name) {
    profileStatus.textContent = "Saisissez le nom de l'entraîneur avant d'enregistrer.";
    const nameField = activeDocumentType() === "invoice" ? invoiceForm.invoice_trainer_name : salaryForm.trainer_name;
    nameField.focus();
    return;
  }
  if (selected) {
    Object.assign(selected, profile);
  } else {
    profile.id = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    profiles.push(profile);
  }
  if (!storeProfiles(profiles)) return;
  applyProfile(profile);
  renderProfiles(profile.id);
  profileStatus.textContent = `Profil « ${profile.name} » enregistré.`;
});

deleteProfileButton.addEventListener("click", () => {
  const profile = profiles.find((item) => item.id === profileSelect.value);
  if (!profile || !window.confirm(`Supprimer le profil « ${profile.name} » de ce navigateur ?`)) return;
  profiles = profiles.filter((item) => item.id !== profile.id);
  if (!storeProfiles(profiles)) return;
  renderProfiles();
  clearProfileFields();
  profileStatus.textContent = `Profil « ${profile.name} » supprimé.`;
});

document.getElementById("add-line").addEventListener("click", () => {
  const source = document.querySelector(".invoice-line");
  const clone = source.cloneNode(true);
  clone.querySelectorAll("input").forEach((input) => {
    input.value = input.name === "item_quantity[]" ? "1" : input.name === "item_unit[]" ? "heure" : "";
    input.required = false;
  });
  document.getElementById("invoice-lines").appendChild(clone);
  updateInvoice();
});

document.getElementById("invoice-lines").addEventListener("click", (event) => {
  if (!event.target.classList.contains("remove-line")) return;
  const lines = document.querySelectorAll(".invoice-line");
  if (lines.length === 1) {
    lines[0].querySelectorAll("input").forEach((input) => input.value = "");
  } else {
    event.target.closest(".invoice-line").remove();
  }
  updateInvoice();
});

updateSalary();
updateInvoice();
renderProfiles();
