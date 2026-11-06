(() => {
  "use strict";

  const form = document.querySelector("[data-compra-form]");

  if (!form) {
    return;
  }

  const lines = form.querySelector("[data-compra-lines]");
  const totalForms = form.querySelector('input[name$="-TOTAL_FORMS"]');
  const template = document.getElementById("compra-line-template");
  const addButton = form.querySelector("[data-compra-add]");
  const taxInput = form.querySelector("[data-compra-tax]");
  const subtotalOutput = form.querySelector("[data-compra-subtotal]");
  const taxPreview = form.querySelector("[data-compra-tax-preview]");
  const totalOutput = form.querySelector("[data-compra-total]");

  const money = (value) => Number(value || 0).toFixed(2);

  const number = (value) => {
    const parsed = Number.parseFloat(value || "0");
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const isDeleted = (row) => {
    const deleteInput = row.querySelector("[data-compra-delete]");
    return Boolean(deleteInput?.checked) || row.classList.contains("is-removed");
  };

  const updateLine = (row) => {
    const quantity = row.querySelector("[data-compra-quantity]");
    const cost = row.querySelector("[data-compra-cost]");
    const subtotal = row.querySelector("[data-compra-line-subtotal]");
    const quantityValue = Math.max(
      0,
      Number.parseInt(quantity?.value || "0", 10) || 0
    );
    const costValue = Math.max(0, number(cost?.value));
    const value = quantityValue * costValue;

    if (subtotal) {
      subtotal.textContent = money(value);
    }
    return value;
  };

  const updateSummary = () => {
    let subtotal = 0;
    lines?.querySelectorAll("[data-compra-line]").forEach((row) => {
      if (!isDeleted(row)) {
        subtotal += updateLine(row);
      }
    });

    const tax = Math.max(0, number(taxInput?.value));
    const total = subtotal + tax;

    if (subtotalOutput) {
      subtotalOutput.textContent = money(subtotal);
    }
    if (taxPreview) {
      taxPreview.textContent = money(tax);
    }
    if (totalOutput) {
      totalOutput.textContent = money(total);
    }
  };

  const bindRow = (row) => {
    row
      .querySelector("[data-compra-quantity]")
      ?.addEventListener("input", updateSummary);
    row
      .querySelector("[data-compra-cost]")
      ?.addEventListener("input", updateSummary);
    row.querySelector("[data-compra-remove]")?.addEventListener("click", () => {
      const deleteInput = row.querySelector("[data-compra-delete]");
      if (deleteInput) {
        deleteInput.checked = true;
      }
      row.classList.add("is-removed");
      updateSummary();
    });
  };

  const addRow = () => {
    if (!lines || !totalForms || !template) {
      return;
    }

    const index = Number.parseInt(totalForms.value || "0", 10);
    const wrapper = document.createElement("tbody");
    wrapper.innerHTML = template.innerHTML.replace(/__prefix__/g, index);
    const row = wrapper.querySelector("[data-compra-line]");

    if (!row) {
      return;
    }

    lines.appendChild(row);
    totalForms.value = String(index + 1);
    bindRow(row);
    updateSummary();
    row.querySelector("[data-compra-product]")?.focus();
  };

  lines?.querySelectorAll("[data-compra-line]").forEach(bindRow);
  addButton?.addEventListener("click", addRow);
  taxInput?.addEventListener("input", updateSummary);
  updateSummary();
})();
