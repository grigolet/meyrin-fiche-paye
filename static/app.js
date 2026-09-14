const number = (value) => {
  const parsed = Number(String(value || "0").replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
};
const chf = (value) => `${value.toFixed(2)} CHF`;

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

