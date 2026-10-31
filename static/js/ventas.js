(() => {
  "use strict";

  const form = document.querySelector("[data-sale-form]");

  if (form) {
    const lines = form.querySelector("[data-sale-lines]");
    const totalForms = form.querySelector('input[name$="-TOTAL_FORMS"]');
    const template = document.getElementById("sale-line-template");
    const addButton = form.querySelector("[data-sale-add]");
    const totalOutput = form.querySelector("[data-sale-total]");
    const receivedInput = form.querySelector("[data-sale-received]");
    const receivedPreview = form.querySelector(
      "[data-sale-received-preview]"
    );
    const changeOutput = form.querySelector("[data-sale-change]");
    const changeRow = form.querySelector("[data-sale-change-row]");

    const money = (value) => Number(value || 0).toFixed(2);

    const isDeleted = (row) => {
      const deleteInput = row.querySelector("[data-line-delete]");
      return Boolean(deleteInput?.checked) || row.classList.contains("is-removed");
    };

    const updateLine = (row) => {
      const product = row.querySelector("[data-line-product]");
      const quantity = row.querySelector("[data-line-quantity]");
      const priceOutput = row.querySelector("[data-line-price]");
      const subtotalOutput = row.querySelector("[data-line-subtotal]");
      const selected = product?.selectedOptions?.[0];
      const price = Number(selected?.dataset.precio || 0);
      const quantityValue = Math.max(
        0,
        Number.parseInt(quantity?.value || "0", 10) || 0
      );
      const subtotal = price * quantityValue;

      if (priceOutput) {
        priceOutput.textContent = money(price);
      }
      if (subtotalOutput) {
        subtotalOutput.textContent = money(subtotal);
      }

      return subtotal;
    };

    const updateSummary = () => {
      let total = 0;
      lines?.querySelectorAll("[data-sale-line]").forEach((row) => {
        if (!isDeleted(row)) {
          total += updateLine(row);
        }
      });

      const received = Number.parseFloat(receivedInput?.value || "0") || 0;
      const change = received - total;

      if (totalOutput) {
        totalOutput.textContent = money(total);
      }
      if (receivedPreview) {
        receivedPreview.textContent = money(received);
      }
      if (changeOutput) {
        changeOutput.textContent = money(change);
      }
      changeRow?.classList.toggle("is-negative", change < 0);
    };

    const bindRow = (row) => {
      row
        .querySelector("[data-line-product]")
        ?.addEventListener("change", updateSummary);
      row
        .querySelector("[data-line-quantity]")
        ?.addEventListener("input", updateSummary);
      row.querySelector("[data-sale-remove]")?.addEventListener("click", () => {
        const deleteInput = row.querySelector("[data-line-delete]");
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
      const row = wrapper.querySelector("[data-sale-line]");

      if (!row) {
        return;
      }

      lines.appendChild(row);
      totalForms.value = String(index + 1);
      bindRow(row);
      updateSummary();
      row.querySelector("[data-line-product]")?.focus();
    };

    lines?.querySelectorAll("[data-sale-line]").forEach(bindRow);
    addButton?.addEventListener("click", addRow);
    receivedInput?.addEventListener("input", updateSummary);
    updateSummary();
  }

  document.querySelector("[data-print-ticket]")?.addEventListener("click", () => {
    window.print();
  });
})();
